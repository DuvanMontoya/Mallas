from __future__ import annotations

import datetime

from django.test import Client, TestCase
from django.utils import timezone

from domain.enums import (
    NotificationChannel,
    NotificationDeliveryStatus,
    RevisionStatus,
)
from modules.curriculum.models import CurriculumRevision
from modules.governance.models import (
    ChangeProposal,
    NormativeDocument,
    Publication,
    PublicationEvent,
    SourceSnapshot,
)
from modules.identity.models import User
from modules.notifications.application.services import (
    deliver_email,
    dispatch_pending_notifications,
    list_in_app_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    materialize_outbox,
)
from modules.notifications.models import (
    NotificationDelivery,
    NotificationEvent,
    NotificationOutbox,
    NotificationPreference,
)
from tests.factories import foundation


class FakeEmailAdapter:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, str]] = []
        self.seen: set[str] = set()

    def send(
        self,
        *,
        recipient_email: str,
        subject: str,
        body: str,
        idempotency_key: str,
    ) -> str:
        if self.fail:
            raise RuntimeError("provider failure must not escape into user-visible detail")
        if idempotency_key not in self.seen:
            self.seen.add(idempotency_key)
            self.calls.append(
                {
                    "recipient_email": recipient_email,
                    "subject": subject,
                    "body": body,
                    "idempotency_key": idempotency_key,
                }
            )
        return f"provider:{idempotency_key}"


class NotificationServiceTests(TestCase):
    def setUp(self) -> None:
        context = foundation(suffix="-notifications")
        self.user = context["user"]
        self.user.email = "notification-student@example.test"
        self.user.email_verified_at = timezone.now()
        self.user.save(update_fields=["email", "email_verified_at"])
        self.revision = context["revision"]
        self.revision.status = RevisionStatus.PUBLISHED.value
        self.revision.content_hash = "c" * 64
        self.revision.source_set_hash = "s" * 64
        self.revision.published_at = timezone.now()
        self.revision.save(
            update_fields=[
                "status",
                "content_hash",
                "source_set_hash",
                "published_at",
                "updated_at",
            ]
        )
        document = NormativeDocument.objects.create(
            issuer="Test University",
            document_type="RESOLUTION",
            number="notifications-1",
            year=2026,
            title="Notification source",
        )
        self.snapshot = SourceSnapshot.objects.create(
            document=document,
            captured_at=timezone.now(),
            sha256="d" * 64,
            mime_type="application/pdf",
            storage_key="private/notifications-source.pdf",
        )
        candidate = CurriculumRevision.objects.create(
            plan=context["plan"],
            revision_code="2026-notification-correction",
            effective_from=datetime.date(2026, 1, 1),
            total_required_credits=141,
            content_hash="n" * 64,
            source_set_hash="t" * 64,
        )
        proposal = ChangeProposal.objects.create(
            proposal_key="notifications:test:proposal",
            title="Notification test publication",
            status="APPLIED",
            base_revision=self.revision,
            candidate_revision=candidate,
            source_snapshot=self.snapshot,
            content_fingerprint="f" * 64,
            semantic_diff={"has_changes": True},
            created_by=self.user,
        )
        publication = Publication.objects.create(
            proposal=proposal,
            revision=self.revision,
            published_by=self.user,
            published_at=timezone.now(),
            content_hash=self.revision.content_hash,
            source_set_hash=self.revision.source_set_hash,
            validation_report={"ok": True},
            semantic_diff={"has_changes": True},
            confirmation="Reviewed and approved for notification tests.",
        )
        self.publication_event = PublicationEvent.objects.create(
            event_key="curriculum.revision.published:notifications-test",
            publication=publication,
            revision=self.revision,
            created_by=self.user,
            changed_courses=[{"operation": "ADD", "key": "STAT201"}],
            impact_summary={"affected_enrollments": 1},
        )
        self.outbox = NotificationOutbox.objects.create(
            publication_event=self.publication_event,
            recipient=self.user,
            event_type="notification.requested",
            dedupe_key="curriculum-publication:notifications-test:user",
            payload={
                "publication_event_id": str(self.publication_event.pk),
                "revision_code": "must-never-be-rendered",
                "message_key": "curriculum.revision.published.impact_review",
            },
            status=NotificationDeliveryStatus.QUEUED.value,
            available_at=timezone.now(),
        )

    def test_materialization_is_idempotent_and_read_state_is_private(self) -> None:
        event = materialize_outbox(self.outbox.pk)
        self.assertIsNotNone(event)
        self.assertEqual(materialize_outbox(self.outbox.pk), event)
        self.assertEqual(NotificationEvent.objects.count(), 1)
        self.assertEqual(
            NotificationDelivery.objects.filter(
                event=event, channel=NotificationChannel.IN_APP.value
            ).count(),
            1,
        )
        self.assertEqual(
            NotificationDelivery.objects.filter(
                event=event, channel=NotificationChannel.EMAIL.value
            )
            .get()
            .status,
            NotificationDeliveryStatus.SUPPRESSED.value,
        )
        self.assertNotIn("revision_code", event.payload)
        feed = list_in_app_notifications(self.user)
        self.assertEqual(feed["unread_count"], 1)
        self.assertEqual(len(feed["items"]), 1)
        self.assertNotIn(self.user.email, feed["items"][0]["body"])

        delivery_id = feed["items"][0]["id"]
        mark_notification_read(self.user, delivery_id)
        self.assertEqual(list_in_app_notifications(self.user)["unread_count"], 0)
        self.assertEqual(mark_all_notifications_read(self.user), 0)

    def test_preferences_suppress_channels_without_deleting_event(self) -> None:
        NotificationPreference.objects.create(
            user=self.user,
            event_type=self.publication_event.event_type,
            in_app_enabled=False,
            email_enabled=False,
        )
        event = materialize_outbox(self.outbox.pk)
        self.assertIsNotNone(event)
        self.assertEqual(NotificationEvent.objects.count(), 1)
        self.assertFalse(
            NotificationDelivery.objects.filter(
                event=event, status=NotificationDeliveryStatus.SENT.value
            ).exists()
        )
        self.assertEqual(
            NotificationDelivery.objects.filter(
                event=event, status=NotificationDeliveryStatus.SUPPRESSED.value
            ).count(),
            2,
        )
        self.assertEqual(list_in_app_notifications(self.user)["items"], [])

    def test_email_adapter_uses_dedupe_key_across_retry(self) -> None:
        NotificationPreference.objects.create(
            user=self.user,
            event_type=self.publication_event.event_type,
            in_app_enabled=False,
            email_enabled=True,
        )
        event = materialize_outbox(self.outbox.pk)
        self.assertIsNotNone(event)
        delivery = NotificationDelivery.objects.get(
            event=event, channel=NotificationChannel.EMAIL.value
        )
        failing = FakeEmailAdapter(fail=True)
        failed = deliver_email(delivery.pk, adapter=failing)
        self.assertEqual(failed.status, NotificationDeliveryStatus.FAILED.value)
        successful = FakeEmailAdapter()
        sent = deliver_email(delivery.pk, adapter=successful)
        sent_again = deliver_email(delivery.pk, adapter=successful)
        self.assertEqual(sent.status, NotificationDeliveryStatus.SENT.value)
        self.assertEqual(sent_again.status, NotificationDeliveryStatus.SENT.value)
        self.assertEqual(len(successful.calls), 1)
        self.assertNotIn(self.user.email, successful.calls[0]["body"])

    def test_draft_source_is_never_materialized(self) -> None:
        draft_revision = CurriculumRevision.objects.create(
            plan=self.revision.plan,
            revision_code="2027-notification-draft",
            effective_from=datetime.date(2027, 1, 1),
            total_required_credits=141,
        )
        proposal = ChangeProposal.objects.create(
            proposal_key="notifications:test:draft",
            title="Draft notification source",
            status="DRAFT",
            base_revision=self.revision,
            candidate_revision=draft_revision,
            source_snapshot=self.snapshot,
            content_fingerprint="g" * 64,
            semantic_diff={"has_changes": True},
            created_by=self.user,
        )
        publication = Publication.objects.create(
            proposal=proposal,
            revision=draft_revision,
            published_by=self.user,
            published_at=timezone.now(),
            content_hash="g" * 64,
            source_set_hash="h" * 64,
            validation_report={"ok": False},
            semantic_diff={"has_changes": True},
            confirmation="This publication must not be dispatched.",
        )
        draft_event = PublicationEvent.objects.create(
            event_key="curriculum.revision.published:notifications-draft",
            publication=publication,
            revision=draft_revision,
            created_by=self.user,
        )
        draft_outbox = NotificationOutbox.objects.create(
            publication_event=draft_event,
            recipient=self.user,
            event_type="notification.requested",
            dedupe_key="curriculum-publication:notifications-draft:user",
            payload={"publication_event_id": str(draft_event.pk)},
            status=NotificationDeliveryStatus.QUEUED.value,
            available_at=timezone.now(),
        )
        self.assertIsNone(materialize_outbox(draft_outbox.pk))
        self.assertFalse(NotificationEvent.objects.exists())
        draft_outbox.refresh_from_db()
        self.assertEqual(draft_outbox.status, NotificationDeliveryStatus.FAILED.value)
        self.assertEqual(draft_outbox.last_error_code, "notification_source_not_published")

    def test_dispatch_and_http_center_prevent_cross_user_access(self) -> None:
        result = dispatch_pending_notifications(limit=10)
        self.assertEqual(result["events_materialized"], 1)
        self.assertEqual(dispatch_pending_notifications(limit=10)["events_materialized"], 0)
        self.client = Client()
        self.client.force_login(self.user)
        response = self.client.get("/api/v1/notifications")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["unread_count"], 1)
        invalid_cursor = self.client.get("/api/v1/notifications?before=not-a-cursor")
        self.assertEqual(invalid_cursor.status_code, 400, invalid_cursor.content)
        self.assertEqual(invalid_cursor.json()["code"], "NOTIFICATION_CURSOR_INVALID")
        other = User.objects.create_user(
            email="other-notification-student@example.test", password="safe-test-password"
        )
        self.client.force_login(other)
        cross_user = self.client.post(
            f"/api/v1/notifications/{response.json()['items'][0]['id']}/read",
            data={},
            content_type="application/json",
        )
        self.assertEqual(cross_user.status_code, 404, cross_user.content)
        self.client.force_login(self.user)
        preference = self.client.put(
            f"/api/v1/notifications/preferences/{self.publication_event.event_type}",
            data={"in_app_enabled": True, "email_enabled": False, "locale": "en-US"},
            content_type="application/json",
        )
        self.assertEqual(preference.status_code, 200, preference.content)
        self.assertEqual(preference.json()["locale"], "en")
        read = self.client.post(
            f"/api/v1/notifications/{response.json()['items'][0]['id']}/read",
            data={},
            content_type="application/json",
        )
        self.assertEqual(read.status_code, 200, read.content)
