from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from domain.enums import (
    NotificationChannel,
    NotificationDeliveryStatus,
    NotificationEventType,
    enum_choices,
)
from modules.common.models import UUIDTimestampedModel


class NotificationEvent(UUIDTimestampedModel):
    """Immutable, privacy-safe notification event materialized after commit."""

    event_key = models.CharField(max_length=240, unique=True)
    event_type = models.CharField(
        max_length=120,
        choices=enum_choices(NotificationEventType),
        default=NotificationEventType.CURRICULUM_REVISION_PUBLISHED.value,
    )
    schema_version = models.PositiveIntegerField(default=1)
    publication_event = models.OneToOneField(
        "governance.PublicationEvent",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="notification_event",
    )
    message_key = models.CharField(max_length=160)
    locale = models.CharField(max_length=16, default="es-CO")
    payload = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(default=timezone.now)
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-published_at", "-id"]
        indexes = [
            models.Index(fields=["event_type", "published_at"], name="notification_event_type_idx"),
            models.Index(
                fields=["publication_event", "published_at"], name="notification_event_source_idx"
            ),
        ]

    def clean(self) -> None:
        if (
            self.event_type == NotificationEventType.CURRICULUM_REVISION_PUBLISHED.value
            and not self.publication_event_id
        ):
            raise ValidationError(
                {"publication_event": "A curriculum publication event is required."}
            )

    def save(self, *args: object, **kwargs: object) -> None:
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Notification events are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("Notification events cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.event_type} — {self.event_key}"


class NotificationPreference(UUIDTimestampedModel):
    """Per-user channel and locale preferences for one notification type."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    event_type = models.CharField(max_length=120)
    in_app_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=False)
    locale = models.CharField(max_length=16, default="es-CO")

    class Meta:
        ordering = ["event_type", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event_type"], name="notification_preference_unique"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "event_type"], name="notif_pref_user_type_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} — {self.event_type}"


class NotificationDelivery(UUIDTimestampedModel):
    """A deduplicated delivery and read-state projection for one recipient/channel."""

    event = models.ForeignKey(
        NotificationEvent,
        on_delete=models.PROTECT,
        related_name="deliveries",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notification_deliveries",
    )
    channel = models.CharField(max_length=16, choices=enum_choices(NotificationChannel))
    status = models.CharField(
        max_length=24,
        choices=enum_choices(NotificationDeliveryStatus),
        default=NotificationDeliveryStatus.QUEUED.value,
    )
    dedupe_key = models.CharField(max_length=240, unique=True)
    locale = models.CharField(max_length=16, default="es-CO")
    title_key = models.CharField(max_length=160)
    body_key = models.CharField(max_length=160)
    link_path = models.CharField(max_length=240, blank=True)
    payload = models.JSONField(default=dict)
    available_at = models.DateTimeField(default=timezone.now)
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    provider_message_id = models.CharField(max_length=240, blank=True)
    last_error_code = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "recipient", "channel"],
                name="notification_delivery_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["recipient", "channel", "status", "created_at"],
                name="notification_delivery_feed_idx",
            ),
            models.Index(
                fields=["channel", "status", "available_at"], name="notif_delivery_queue_idx"
            ),
        ]

    def clean(self) -> None:
        if self.channel != NotificationChannel.IN_APP.value and self.read_at is not None:
            raise ValidationError({"read_at": "Only in-app deliveries have read state."})

    def __str__(self) -> str:
        return f"{self.event_id} — {self.recipient_id} — {self.channel} ({self.status})"


class NotificationOutbox(UUIDTimestampedModel):
    """Transactional notification request consumed by a replaceable worker."""

    publication_event = models.ForeignKey(
        "governance.PublicationEvent",
        on_delete=models.PROTECT,
        related_name="notification_requests",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notification_outbox",
    )
    event_type = models.CharField(max_length=120, default="notification.requested")
    dedupe_key = models.CharField(max_length=240, unique=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=24,
        choices=enum_choices(NotificationDeliveryStatus),
        default=NotificationDeliveryStatus.QUEUED.value,
    )
    available_at = models.DateTimeField()
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=120, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["available_at", "created_at", "id"]
        indexes = [
            models.Index(fields=["status", "available_at"], name="notification_queue_idx"),
            models.Index(fields=["recipient", "created_at"], name="notification_recipient_idx"),
            models.Index(
                fields=["publication_event", "recipient"], name="notif_event_recipient_idx"
            ),
            models.Index(fields=["status", "next_attempt_at"], name="notification_retry_queue_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} → {self.recipient_id} ({self.status})"
