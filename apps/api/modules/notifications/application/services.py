from __future__ import annotations

import base64
import binascii
import logging
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from domain.enums import (
    NotificationChannel,
    NotificationDeliveryStatus,
    RevisionStatus,
)
from modules.identity.application.audit import record_audit_event
from modules.identity.models import User
from modules.observability.metrics import measure_job_timing

from ..models import (
    NotificationDelivery,
    NotificationEvent,
    NotificationOutbox,
    NotificationPreference,
)
from .channels import EmailAdapter, configured_email_adapter
from .templates import (
    NotificationContent,
    normalize_locale,
    render_notification,
    supported_event_types,
)

logger = logging.getLogger(__name__)


class NotificationError(RuntimeError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _encode_cursor(delivery: NotificationDelivery) -> str:
    value = f"{delivery.created_at.isoformat()}|{delivery.pk}"
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_cursor(value: str) -> tuple[datetime, UUID]:
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        created_at_value, delivery_id = decoded.split("|", 1)
        created_at = datetime.fromisoformat(created_at_value)
        if timezone.is_naive(created_at):
            created_at = timezone.make_aware(created_at)
        return created_at, UUID(delivery_id)
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise NotificationError(
            "The notification cursor is invalid.", code="notification_cursor_invalid"
        ) from exc


def _retry_at(now: datetime, attempt_count: int) -> datetime:
    seconds = min(3600, 5 * (2 ** min(attempt_count, 8)))
    return now + timedelta(seconds=seconds)


def _safe_outbox_payload(outbox: NotificationOutbox) -> dict[str, str]:
    """Keep recipient-facing templates independent from academic detail."""

    return {
        "publication_event_id": str(outbox.publication_event_id),
        "message_key": "notifications.curriculum_revision_published",
    }


def _preference(user: User, event_type: str) -> NotificationPreference:
    preference, _ = NotificationPreference.objects.get_or_create(
        user=user,
        event_type=event_type,
        defaults={"in_app_enabled": True, "email_enabled": False, "locale": "es-CO"},
    )
    return preference


def _delivery_defaults(
    *,
    event: NotificationEvent,
    recipient: User,
    channel: str,
    content: NotificationContent,
    locale: str,
    status: str,
    now: Any,
    error_code: str = "",
) -> dict[str, Any]:
    return {
        "status": status,
        "dedupe_key": f"notification:{event.pk}:{recipient.pk}:{channel.lower()}",
        "locale": locale,
        "title_key": content.title_key,
        "body_key": content.body_key,
        "link_path": content.link_path,
        "payload": {"message_key": content.body_key},
        "available_at": now,
        "delivered_at": now if status == NotificationDeliveryStatus.SENT.value else None,
        "last_error_code": error_code,
    }


def _upsert_delivery(
    *,
    event: NotificationEvent,
    recipient: User,
    channel: str,
    content: NotificationContent,
    locale: str,
    status: str,
    now: Any,
    error_code: str = "",
) -> NotificationDelivery:
    delivery, _ = NotificationDelivery.objects.get_or_create(
        event=event,
        recipient=recipient,
        channel=channel,
        defaults=_delivery_defaults(
            event=event,
            recipient=recipient,
            channel=channel,
            content=content,
            locale=locale,
            status=status,
            now=now,
            error_code=error_code,
        ),
    )
    return delivery


@transaction.atomic  # type: ignore[untyped-decorator]
def materialize_outbox(outbox_id: UUID | str) -> NotificationEvent | None:
    """Fan out one committed publication request exactly once per channel."""

    now = timezone.now()
    outbox = (
        NotificationOutbox.objects.select_for_update()
        .select_related(
            "recipient",
            "publication_event__revision__plan__program__faculty__campus",
        )
        .get(pk=outbox_id)
    )
    if (
        outbox.status
        in {
            NotificationDeliveryStatus.SENT.value,
            NotificationDeliveryStatus.SUPPRESSED.value,
        }
        and outbox.processed_at is not None
    ):
        return NotificationEvent.objects.filter(publication_event=outbox.publication_event).first()

    source = outbox.publication_event
    if source.revision.status != RevisionStatus.PUBLISHED.value:
        outbox.status = NotificationDeliveryStatus.FAILED.value
        outbox.attempt_count += 1
        outbox.last_attempt_at = now
        outbox.last_error_code = "notification_source_not_published"
        outbox.next_attempt_at = _retry_at(now, outbox.attempt_count)
        outbox.save(
            update_fields=[
                "status",
                "attempt_count",
                "last_attempt_at",
                "last_error_code",
                "next_attempt_at",
                "updated_at",
            ]
        )
        return None

    outbox.attempt_count += 1
    outbox.last_attempt_at = now
    event, _ = NotificationEvent.objects.get_or_create(
        publication_event=source,
        defaults={
            "event_key": f"notification:{source.pk}",
            "event_type": source.event_type,
            "schema_version": 1,
            "message_key": "notifications.curriculum_revision_published",
            "locale": "es-CO",
            "payload": _safe_outbox_payload(outbox),
            "occurred_at": source.created_at,
            "published_at": now,
        },
    )
    preference = _preference(outbox.recipient, event.event_type)
    locale = normalize_locale(preference.locale)
    content = render_notification(event.event_type, locale)

    if preference.in_app_enabled:
        _upsert_delivery(
            event=event,
            recipient=outbox.recipient,
            channel=NotificationChannel.IN_APP.value,
            content=content,
            locale=locale,
            status=NotificationDeliveryStatus.SENT.value,
            now=now,
        )
    else:
        _upsert_delivery(
            event=event,
            recipient=outbox.recipient,
            channel=NotificationChannel.IN_APP.value,
            content=content,
            locale=locale,
            status=NotificationDeliveryStatus.SUPPRESSED.value,
            now=now,
            error_code="notification_preference_disabled",
        )

    if preference.email_enabled and outbox.recipient.email_verified_at is not None:
        _upsert_delivery(
            event=event,
            recipient=outbox.recipient,
            channel=NotificationChannel.EMAIL.value,
            content=content,
            locale=locale,
            status=NotificationDeliveryStatus.QUEUED.value,
            now=now,
        )
    else:
        _upsert_delivery(
            event=event,
            recipient=outbox.recipient,
            channel=NotificationChannel.EMAIL.value,
            content=content,
            locale=locale,
            status=NotificationDeliveryStatus.SUPPRESSED.value,
            now=now,
            error_code=(
                "notification_preference_disabled"
                if not preference.email_enabled
                else "notification_email_unverified"
            ),
        )

    outbox.status = NotificationDeliveryStatus.SENT.value
    outbox.processed_at = now
    outbox.next_attempt_at = None
    outbox.last_error_code = ""
    outbox.save(
        update_fields=[
            "status",
            "attempt_count",
            "last_attempt_at",
            "processed_at",
            "next_attempt_at",
            "last_error_code",
            "updated_at",
        ]
    )
    record_audit_event(
        None,
        action="NOTIFICATION_EVENT_MATERIALIZED",
        object_type="NotificationEvent",
        object_id=event.pk,
        institution_id=source.revision.plan.program.faculty.campus.institution_id,
        metadata={
            "publication_event_id": str(source.pk),
            "channels": [
                NotificationChannel.IN_APP.value,
                NotificationChannel.EMAIL.value,
            ],
        },
    )
    return event


def deliver_email(
    delivery_id: UUID | str,
    *,
    adapter: EmailAdapter | None = None,
) -> NotificationDelivery:
    """Deliver one email with a stable idempotency key and safe template content."""

    now = timezone.now()
    with transaction.atomic():
        delivery = (
            NotificationDelivery.objects.select_for_update()
            .select_related("event", "recipient")
            .get(pk=delivery_id)
        )
        if delivery.channel != NotificationChannel.EMAIL.value:
            raise NotificationError(
                "Only email deliveries can use the email adapter.",
                code="notification_channel_invalid",
            )
        if delivery.status in {
            NotificationDeliveryStatus.SENT.value,
            NotificationDeliveryStatus.SUPPRESSED.value,
        }:
            return delivery
        if (
            delivery.status == NotificationDeliveryStatus.SENDING.value
            and delivery.last_attempt_at is not None
            and now - delivery.last_attempt_at < timedelta(minutes=5)
        ):
            return delivery
        if adapter is None:
            adapter = configured_email_adapter()
        if adapter is None:
            delivery.status = NotificationDeliveryStatus.SUPPRESSED.value
            delivery.last_error_code = "notification_email_channel_disabled"
            delivery.save(update_fields=["status", "last_error_code", "updated_at"])
            return delivery
        delivery.status = NotificationDeliveryStatus.SENDING.value
        delivery.attempt_count += 1
        delivery.last_attempt_at = now
        delivery.last_error_code = ""
        delivery.save(
            update_fields=[
                "status",
                "attempt_count",
                "last_attempt_at",
                "last_error_code",
                "updated_at",
            ]
        )

    content = render_notification(delivery.event.event_type, delivery.locale)
    try:
        provider_message_id = adapter.send(
            recipient_email=delivery.recipient.email,
            subject=content.title,
            body=content.body,
            idempotency_key=delivery.dedupe_key,
        )
    except Exception:
        logger.warning("Notification email delivery failed for delivery %s", delivery.pk)
        with transaction.atomic():
            failed = NotificationDelivery.objects.select_for_update().get(pk=delivery.pk)
            failed.status = NotificationDeliveryStatus.FAILED.value
            failed.last_error_code = "notification_email_delivery_failed"
            failed.available_at = _retry_at(timezone.now(), failed.attempt_count)
            failed.save(update_fields=["status", "last_error_code", "available_at", "updated_at"])
        return failed

    with transaction.atomic():
        delivered = NotificationDelivery.objects.select_for_update().get(pk=delivery.pk)
        delivered.status = NotificationDeliveryStatus.SENT.value
        delivered.delivered_at = timezone.now()
        delivered.provider_message_id = str(provider_message_id)[:240]
        delivered.last_error_code = ""
        delivered.save(
            update_fields=[
                "status",
                "delivered_at",
                "provider_message_id",
                "last_error_code",
                "updated_at",
            ]
        )
        return delivered


@measure_job_timing("notifications_dispatch")
def dispatch_pending_notifications(*, limit: int = 100) -> dict[str, int]:
    bounded_limit = max(1, min(limit, 500))
    now = timezone.now()
    outbox_ids = list(
        NotificationOutbox.objects.filter(
            status__in=[
                NotificationDeliveryStatus.QUEUED.value,
                NotificationDeliveryStatus.FAILED.value,
            ],
            available_at__lte=now,
        )
        .filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now))
        .values_list("pk", flat=True)[:bounded_limit]
    )
    materialized = 0
    failed = 0
    for outbox_id in outbox_ids:
        try:
            event = materialize_outbox(outbox_id)
            if event is not None:
                materialized += 1
            else:
                failed += 1
        except NotificationOutbox.DoesNotExist:
            continue
    email_ids = list(
        NotificationDelivery.objects.filter(
            channel=NotificationChannel.EMAIL.value,
            status__in=[
                NotificationDeliveryStatus.QUEUED.value,
                NotificationDeliveryStatus.FAILED.value,
            ],
            available_at__lte=now,
        ).values_list("pk", flat=True)[:bounded_limit]
    )
    email_sent = 0
    for delivery_id in email_ids:
        delivery = deliver_email(delivery_id)
        if delivery.status == NotificationDeliveryStatus.SENT.value:
            email_sent += 1
    return {
        "outbox_seen": len(outbox_ids),
        "events_materialized": materialized,
        "outbox_failed": failed,
        "emails_sent": email_sent,
    }


def _delivery_view(delivery: NotificationDelivery) -> dict[str, Any]:
    content = render_notification(delivery.event.event_type, delivery.locale)
    return {
        "id": delivery.pk,
        "event_id": delivery.event_id,
        "event_type": delivery.event.event_type,
        "channel": delivery.channel,
        "status": delivery.status,
        "title": content.title,
        "body": content.body,
        "locale": delivery.locale,
        "link_path": delivery.link_path,
        "read_at": delivery.read_at,
        "created_at": delivery.created_at,
        "delivered_at": delivery.delivered_at,
    }


def list_in_app_notifications(
    user: User,
    *,
    unread_only: bool = False,
    limit: int = 50,
    before: str | None = None,
) -> dict[str, Any]:
    bounded_limit = max(1, min(limit, 100))
    queryset = NotificationDelivery.objects.filter(
        recipient=user,
        channel=NotificationChannel.IN_APP.value,
        status=NotificationDeliveryStatus.SENT.value,
    ).select_related("event")
    unread_count = queryset.filter(read_at__isnull=True).count()
    if unread_only:
        queryset = queryset.filter(read_at__isnull=True)
    if before:
        cursor_created_at, cursor_id = _decode_cursor(before)
        queryset = queryset.filter(
            Q(created_at__lt=cursor_created_at) | Q(created_at=cursor_created_at, id__lt=cursor_id)
        )
    items = list(queryset[: bounded_limit + 1])
    has_more = len(items) > bounded_limit
    items = items[:bounded_limit]
    return {
        "items": [_delivery_view(item) for item in items],
        "unread_count": unread_count,
        "next_cursor": _encode_cursor(items[-1]) if has_more and items else None,
    }


@transaction.atomic  # type: ignore[untyped-decorator]
def mark_notification_read(user: User, delivery_id: UUID | str) -> dict[str, Any]:
    try:
        delivery = (
            NotificationDelivery.objects.select_for_update()
            .select_related("event")
            .get(
                pk=delivery_id,
                recipient=user,
                channel=NotificationChannel.IN_APP.value,
                status=NotificationDeliveryStatus.SENT.value,
            )
        )
    except NotificationDelivery.DoesNotExist as exc:
        raise NotificationError(
            "The notification was not found.", code="notification_not_found"
        ) from exc
    if delivery.read_at is None:
        delivery.read_at = timezone.now()
        delivery.save(update_fields=["read_at", "updated_at"])
    return _delivery_view(delivery)


@transaction.atomic  # type: ignore[untyped-decorator]
def mark_all_notifications_read(user: User) -> int:
    return NotificationDelivery.objects.filter(
        recipient=user,
        channel=NotificationChannel.IN_APP.value,
        status=NotificationDeliveryStatus.SENT.value,
        read_at__isnull=True,
    ).update(read_at=timezone.now(), updated_at=timezone.now())


def list_preferences(user: User) -> list[dict[str, Any]]:
    existing = {
        item.event_type: item
        for item in NotificationPreference.objects.filter(
            user=user, event_type__in=supported_event_types()
        )
    }
    result: list[dict[str, Any]] = []
    for event_type in supported_event_types():
        preference = existing.get(event_type)
        result.append(
            {
                "event_type": event_type,
                "in_app_enabled": preference.in_app_enabled if preference else True,
                "email_enabled": preference.email_enabled if preference else False,
                "locale": preference.locale if preference else "es-CO",
            }
        )
    return result


@transaction.atomic  # type: ignore[untyped-decorator]
def update_preference(
    user: User,
    event_type: str,
    *,
    in_app_enabled: bool,
    email_enabled: bool,
    locale: str,
) -> dict[str, Any]:
    if event_type not in supported_event_types():
        raise NotificationError(
            "The notification type is not supported.", code="notification_type_invalid"
        )
    preference, _ = NotificationPreference.objects.get_or_create(user=user, event_type=event_type)
    preference.in_app_enabled = in_app_enabled
    preference.email_enabled = email_enabled
    preference.locale = normalize_locale(locale)
    preference.save(update_fields=["in_app_enabled", "email_enabled", "locale", "updated_at"])
    return {
        "event_type": preference.event_type,
        "in_app_enabled": preference.in_app_enabled,
        "email_enabled": preference.email_enabled,
        "locale": preference.locale,
    }


def safe_notification_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return only non-sensitive operational identifiers for diagnostics/tests."""

    if not payload:
        return {}
    allowed = {"publication_event_id", "message_key"}
    return {str(key): value for key, value in payload.items() if str(key) in allowed}
