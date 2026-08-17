from __future__ import annotations

import datetime

from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.utils import timezone

from domain.enums import (
    EpistemicStatus,
    ProposalStatus,
    RevisionStatus,
    UserRole,
)
from domain.errors import PublishedRevisionImmutableError
from modules.audit.application.services import run_degree_audit
from modules.audit.models import DegreeAuditRun
from modules.curriculum.application.services import CurriculumRevisionService
from modules.curriculum.models import CurriculumRevision
from modules.governance.application.services import GovernanceError, publish_proposal
from modules.governance.models import (
    ChangeProposal,
    Evidence,
    ExtractionCandidate,
    NormativeDocument,
    Publication,
    PublicationEvent,
    PublicationImpact,
    SourceSnapshot,
)
from modules.identity.models import AuditEvent, RoleAssignment
from modules.notifications.models import NotificationOutbox
from tests.factories import foundation


class PublicationImpactTests(TestCase):
    def setUp(self) -> None:
        self.context = foundation(suffix="-publication")
        self.institution = self.context["institution"]
        self.program = self.context["program"]
        self.plan = self.context["plan"]
        self.old_revision: CurriculumRevision = self.context["revision"]
        self.old_revision.total_required_credits = 4
        self.old_revision.save(update_fields=["total_required_credits", "updated_at"])
        self.editor = self.context["user"]
        self.editor.email = "editor-publication@example.test"
        self.editor.save(update_fields=["email"])
        self.reviewer = type(self.editor).objects.create_user(
            email="reviewer-publication@example.test", password="safe-password"
        )
        RoleAssignment.objects.create(
            user=self.editor,
            role=UserRole.EDITOR.value,
            institution=self.institution,
            program=self.program,
        )
        RoleAssignment.objects.create(
            user=self.reviewer,
            role=UserRole.REVIEWER.value,
            institution=self.institution,
            program=self.program,
        )
        document = NormativeDocument.objects.create(
            issuer="Test University",
            document_type="RESOLUTION",
            number="publication-1",
            year=2026,
            title="Published curriculum source",
        )
        self.snapshot = SourceSnapshot.objects.create(
            document=document,
            captured_at=timezone.now(),
            sha256="d" * 64,
            mime_type="application/pdf",
            storage_key="private/sources/publication.pdf",
        )
        self.evidence = Evidence.objects.create(
            snapshot=self.snapshot,
            page=2,
            line_locator="page:2/paragraph:3",
            excerpt_hash="e" * 64,
            excerpt="The published correction changes the course credits.",
            annotation="Archived publication evidence.",
        )

    def _publish_old_revision(self) -> DegreeAuditRun:
        self.old_revision.status = RevisionStatus.APPROVED.value
        self.old_revision.save(update_fields=["status", "updated_at"])
        CurriculumRevisionService.publish(self.old_revision.pk, actor=self.reviewer)
        _, audit_run, _ = run_degree_audit(self.context["enrollment"].pk)
        return audit_run

    def _new_proposal(self, *, base: CurriculumRevision | None) -> ChangeProposal:
        candidate = CurriculumRevision.objects.create(
            plan=self.plan,
            revision_code="2027-publication",
            effective_from=datetime.date(2027, 1, 1),
            total_required_credits=142,
        )
        proposal = ChangeProposal.objects.create(
            proposal_key="publication:test:2027",
            title="Published correction",
            status=ProposalStatus.APPROVED.value,
            base_revision=base,
            candidate_revision=candidate,
            source_snapshot=self.snapshot,
            content_fingerprint="f" * 64,
            semantic_diff={
                "base_fingerprint": base.content_hash if base else None,
                "candidate_fingerprint": "f" * 64,
                "added": {"courses": [{"code": "STAT202", "credits": 4}]},
                "removed": {"groups": [{"id": "ELECTIVES"}]},
                "changed": [
                    {
                        "entity": "requirements",
                        "key": "REQ:STAT202",
                        "before": {"minimum": 3},
                        "after": {"minimum": 4},
                    }
                ],
                "has_changes": True,
            },
            rationale="Correction prepared from an archived source and reviewed independently.",
            created_by=self.editor,
        )
        candidate.status = RevisionStatus.APPROVED.value
        candidate.save(update_fields=["status", "updated_at"])
        ExtractionCandidate.objects.create(
            proposal=proposal,
            source_snapshot=self.snapshot,
            entity="courses",
            entity_key="STAT202",
            operation="ADD",
            status="ACCEPTED",
            epistemic_status=EpistemicStatus.INFERRED_PENDING_REVIEW.value,
            after={"code": "STAT202", "credits": 4},
        )
        return proposal

    def test_publication_supersedes_old_revision_and_persists_impact_outbox(self) -> None:
        old_audit = self._publish_old_revision()
        proposal = self._new_proposal(base=self.old_revision)

        receipt = publish_proposal(
            self.reviewer,
            proposal.pk,
            confirmation="I reviewed the correction, impact, validation, and evidence.",
            expected_version=proposal.updated_at.isoformat(),
        )

        self.old_revision.refresh_from_db()
        proposal.refresh_from_db()
        new_revision = receipt.revision
        new_revision.refresh_from_db()
        self.assertEqual(self.old_revision.status, RevisionStatus.SUPERSEDED.value)
        self.assertEqual(new_revision.status, RevisionStatus.PUBLISHED.value)
        self.assertEqual(new_revision.supersedes_id, self.old_revision.pk)
        self.assertEqual(proposal.status, ProposalStatus.APPLIED.value)

        old_audit.refresh_from_db()
        self.assertEqual(old_audit.revision_id, self.old_revision.pk)
        self.assertTrue(old_audit.result_hash)
        self.assertEqual(self.context["enrollment"].revision_basis_id, self.old_revision.pk)

        event = PublicationEvent.objects.get(publication=receipt)
        impact = PublicationImpact.objects.get(publication_event=event)
        self.assertEqual(impact.enrollment_id, self.context["enrollment"].pk)
        self.assertEqual(impact.previous_audit_run_id, old_audit.pk)
        self.assertEqual(impact.previous_audit_result_hash, old_audit.result_hash)
        self.assertEqual(impact.impact_status, "RECOMPUTE_QUEUED")
        self.assertIn(str(new_revision.pk), event.recompute_plan["jobs"][0]["target_revision_id"])
        notification = NotificationOutbox.objects.get(publication_event=event)
        self.assertEqual(notification.recipient_id, self.editor.pk)
        self.assertEqual(notification.status, "QUEUED")
        self.assertEqual(notification.payload["impact_id"], str(impact.pk))
        self.assertTrue(
            AuditEvent.objects.filter(
                action="CURRICULUM_PUBLICATION_EVENT_RECORDED", object_id=str(event.pk)
            ).exists()
        )

        self.client = Client()
        self.client.force_login(self.reviewer)
        response = self.client.get(f"/api/v1/governance/publications/{receipt.pk}/impact")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["event"]["impact_summary"]["affected_enrollments"], 1)
        detail_response = self.client.get(f"/api/v1/governance/proposals/{proposal.pk}")
        self.assertEqual(detail_response.status_code, 200, detail_response.content)
        self.assertTrue(
            any(
                item["object_type"] == "PublicationEvent" and item["object_id"] == str(event.pk)
                for item in detail_response.json()["audit_events"]
            )
        )

        with self.assertRaises(PublishedRevisionImmutableError):
            new_revision.total_required_credits = 999
            new_revision.save(update_fields=["total_required_credits", "updated_at"])
        with self.assertRaises(ValidationError):
            event.event_type = "tampered"
            event.save(update_fields=["event_type", "updated_at"])

    def test_invalid_publication_has_no_event_impact_or_notification_and_keeps_old_revision(
        self,
    ) -> None:
        old_audit = self._publish_old_revision()
        proposal = self._new_proposal(base=self.old_revision)
        pending = proposal.extraction_candidates.get()
        pending.status = "PENDING"
        pending.save(update_fields=["status", "updated_at"])

        with self.assertRaises(GovernanceError) as raised:
            publish_proposal(
                self.reviewer,
                proposal.pk,
                confirmation="Attempted invalid publication must be blocked.",
                expected_version=proposal.updated_at.isoformat(),
            )

        self.assertEqual(raised.exception.code, "candidates_pending")
        self.old_revision.refresh_from_db()
        self.assertEqual(self.old_revision.status, RevisionStatus.PUBLISHED.value)
        self.assertFalse(Publication.objects.filter(proposal=proposal).exists())
        self.assertFalse(PublicationEvent.objects.exists())
        self.assertFalse(NotificationOutbox.objects.exists())
        self.assertEqual(
            DegreeAuditRun.objects.get(pk=old_audit.pk).result_hash, old_audit.result_hash
        )

    def test_stale_base_requires_new_correction_proposal_instead_of_rollback(self) -> None:
        self._publish_old_revision()
        proposal = self._new_proposal(base=None)

        with self.assertRaises(GovernanceError) as raised:
            publish_proposal(
                self.reviewer,
                proposal.pk,
                confirmation="This stale proposal must not overwrite the current revision.",
                expected_version=proposal.updated_at.isoformat(),
            )

        self.assertEqual(raised.exception.code, "publication_base_stale")
        self.assertEqual(
            CurriculumRevision.objects.get(pk=self.old_revision.pk).status,
            RevisionStatus.PUBLISHED.value,
        )
        self.assertFalse(Publication.objects.filter(proposal=proposal).exists())
