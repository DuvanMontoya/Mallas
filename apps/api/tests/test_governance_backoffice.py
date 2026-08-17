from __future__ import annotations

import json
from typing import Any

from django.test import Client, TestCase
from django.utils import timezone

from domain.enums import EpistemicStatus, ProposalStatus, RequirementPurpose, UserRole
from modules.curriculum.models import CurriculumRevision
from modules.governance.models import (
    ChangeProposal,
    Evidence,
    ExtractionCandidate,
    NormativeDocument,
    Publication,
    SourceSnapshot,
)
from modules.identity.models import AuditEvent, RoleAssignment
from modules.rules.models import Requirement
from tests.factories import foundation


class GovernanceBackofficeTests(TestCase):
    def setUp(self) -> None:
        self.context = foundation(suffix="-governance")
        self.institution = self.context["institution"]
        self.program = self.context["program"]
        self.revision: CurriculumRevision = self.context["revision"]
        self.editor = self.context["user"]
        self.editor.email = "editor-governance@example.test"
        self.editor.save(update_fields=["email"])
        self.reviewer = type(self.editor).objects.create_user(
            email="reviewer-governance@example.test", password="safe-password"
        )
        for user, role in ((self.editor, UserRole.EDITOR), (self.reviewer, UserRole.REVIEWER)):
            RoleAssignment.objects.create(
                user=user,
                role=role.value,
                institution=self.institution,
                program=self.program,
            )
        document = NormativeDocument.objects.create(
            issuer="Test University",
            document_type="RESOLUTION",
            number="1",
            year=2026,
            title="Curriculum source",
        )
        self.snapshot = SourceSnapshot.objects.create(
            document=document,
            captured_at=timezone.now(),
            sha256="a" * 64,
            mime_type="application/pdf",
            storage_key="private/sources/test.pdf",
        )
        self.evidence = Evidence.objects.create(
            snapshot=self.snapshot,
            page=1,
            line_locator="page:1/paragraph:1",
            excerpt_hash="b" * 64,
            excerpt="The source establishes the test rule.",
            annotation="Archived test evidence.",
        )
        self.requirement = Requirement.objects.create(
            revision=self.revision,
            owner_type="COURSE",
            owner_id=self.context["course_version"].course_id,
            code="TEST:PREREQUISITE",
            purpose=RequirementPurpose.ENROLLMENT_PREREQUISITE.value,
            ast={"type": "COURSE_PASSED", "course_code": "STAT000"},
            epistemic_status=EpistemicStatus.VERIFIED.value,
            explanation_key="test.rule",
        )
        self.requirement.evidence.add(self.evidence)
        self.proposal = ChangeProposal.objects.create(
            proposal_key="test:governance:1",
            title="Test governance proposal",
            status=ProposalStatus.DRAFT.value,
            candidate_revision=self.revision,
            source_snapshot=self.snapshot,
            content_fingerprint="c" * 64,
            semantic_diff={
                "base_fingerprint": None,
                "candidate_fingerprint": "c" * 64,
                "added": {"courses": [{"code": "STAT000", "credits": 3}]},
                "removed": {},
                "changed": [],
                "has_changes": True,
            },
            rationale="A test proposal with explicit provenance.",
            created_by=self.editor,
        )
        self.candidate = ExtractionCandidate.objects.create(
            proposal=self.proposal,
            source_snapshot=self.snapshot,
            entity="courses",
            entity_key="STAT000",
            operation="ADD",
            after={"code": "STAT000", "name": "Test course", "credits": 3},
        )
        self.client = Client()

    def _json(
        self, method: str, path: str, payload: dict[str, Any] | None = None, **kwargs: Any
    ) -> Any:
        body = json.dumps(payload) if payload is not None else None
        return getattr(self.client, method.lower())(
            path, data=body, content_type="application/json", **kwargs
        )

    def _login(self, user: Any) -> None:
        self.client.force_login(user)

    def test_source_inbox_and_detail_expose_provenance_and_rule_inspector(self) -> None:
        self._login(self.editor)
        inbox = self.client.get("/api/v1/governance/inbox")
        self.assertEqual(inbox.status_code, 200, inbox.content)
        self.assertEqual(inbox.json()["proposals"][0]["id"], str(self.proposal.pk))
        detail = self.client.get(f"/api/v1/governance/proposals/{self.proposal.pk}")
        self.assertEqual(detail.status_code, 200, detail.content)
        payload = detail.json()
        self.assertEqual(payload["semantic_diff"]["added"]["courses"][0]["code"], "STAT000")
        self.assertEqual(
            payload["requirements"][0]["human_explanation"], "Haber aprobado el curso STAT000."
        )
        self.assertEqual(payload["requirements"][0]["evidence"][0]["snapshot_sha256"], "a" * 64)
        self.assertEqual(detail["ETag"], f'"{payload["version"]}"')
        snapshot = self.client.get(f"/api/v1/governance/snapshots/{self.snapshot.pk}")
        self.assertEqual(snapshot.status_code, 200, snapshot.content)
        self.assertFalse(snapshot.json()["archived_content"]["available"])

    def test_scoped_editor_cannot_enumerate_another_program_source_inbox(self) -> None:
        other = foundation(suffix="-governance-other")
        other_document = NormativeDocument.objects.create(
            issuer="Other University",
            document_type="RESOLUTION",
            number="2",
            year=2026,
            title="Other curriculum source",
        )
        other_snapshot = SourceSnapshot.objects.create(
            document=other_document,
            captured_at=timezone.now(),
            sha256="d" * 64,
            mime_type="application/pdf",
            storage_key="private/sources/other.pdf",
        )
        other_proposal = ChangeProposal.objects.create(
            proposal_key="test:governance:other",
            title="Other governance proposal",
            status=ProposalStatus.DRAFT.value,
            candidate_revision=other["revision"],
            source_snapshot=other_snapshot,
            content_fingerprint="e" * 64,
            semantic_diff={"added": {}, "removed": {}, "changed": [], "has_changes": False},
            rationale="A proposal outside the editor's assigned scope.",
            created_by=self.editor,
        )
        self._login(self.editor)

        inbox = self.client.get("/api/v1/governance/inbox")
        self.assertEqual(inbox.status_code, 200, inbox.content)
        self.assertEqual(
            {item["id"] for item in inbox.json()["proposals"]}, {str(self.proposal.pk)}
        )
        self.assertNotIn(str(other_document.pk), {item["id"] for item in inbox.json()["documents"]})
        self.assertNotIn(str(other_snapshot.pk), {item["id"] for item in inbox.json()["snapshots"]})
        other_detail = self.client.get(f"/api/v1/governance/proposals/{other_proposal.pk}")
        self.assertEqual(other_detail.status_code, 403, other_detail.content)
        other_snapshot_detail = self.client.get(f"/api/v1/governance/snapshots/{other_snapshot.pk}")
        self.assertEqual(other_snapshot_detail.status_code, 404, other_snapshot_detail.content)

    def test_editor_cannot_approve_and_optimistic_lock_conflict_is_visible(self) -> None:
        self._login(self.editor)
        version = self.proposal.updated_at.isoformat()
        submitted = self._json(
            "post",
            f"/api/v1/governance/proposals/{self.proposal.pk}/submit",
            {"comment": "Ready for independent review."},
            HTTP_IF_MATCH=f'"{version}"',
        )
        self.assertEqual(submitted.status_code, 200, submitted.content)
        current_version = submitted.json()["version"]
        editor_approval = self._json(
            "post",
            f"/api/v1/governance/proposals/{self.proposal.pk}/review",
            {"decision": "APPROVE", "comment": "I approve my own work."},
            HTTP_IF_MATCH=f'"{current_version}"',
        )
        self.assertEqual(editor_approval.status_code, 403, editor_approval.content)
        self.assertEqual(editor_approval.json()["code"], "GOVERNANCE_REVIEWER_REQUIRED")
        stale = self._json(
            "post",
            f"/api/v1/governance/proposals/{self.proposal.pk}/submit",
            {},
            HTTP_IF_MATCH=f'"{version}"',
        )
        self.assertEqual(stale.status_code, 409, stale.content)
        self.assertEqual(stale.json()["code"], "GOVERNANCE_CONCURRENCY_CONFLICT")

    def test_bulk_preview_performs_no_write_and_apply_requires_preview_token(self) -> None:
        second = ExtractionCandidate.objects.create(
            proposal=self.proposal,
            source_snapshot=self.snapshot,
            entity="courses",
            entity_key="STAT001",
            operation="ADD",
            after={"code": "STAT001", "name": "Another test course", "credits": 3},
        )
        self._login(self.editor)
        preview = self._json(
            "post",
            f"/api/v1/governance/proposals/{self.proposal.pk}/candidates/bulk-preview",
            {
                "candidate_ids": [str(self.candidate.pk), str(second.pk)],
                "status": "ACCEPTED",
                "epistemic_status": "INFERRED_PENDING_REVIEW",
                "evidence_ids": [],
            },
        )
        self.assertEqual(preview.status_code, 200, preview.content)
        self.assertFalse(preview.json()["writes_performed"])
        self.candidate.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.candidate.status, "PENDING")
        self.assertEqual(second.status, "PENDING")
        missing_token = self._json(
            "post",
            f"/api/v1/governance/proposals/{self.proposal.pk}/candidates/bulk-review",
            {
                "candidate_ids": [str(self.candidate.pk), str(second.pk)],
                "status": "ACCEPTED",
                "epistemic_status": "INFERRED_PENDING_REVIEW",
                "evidence_ids": [],
            },
            HTTP_IF_MATCH=f'"{self.proposal.updated_at.isoformat()}"',
        )
        self.assertEqual(missing_token.status_code, 428, missing_token.content)

    def test_independent_review_publication_creates_immutable_receipt_and_audit(self) -> None:
        self._login(self.editor)
        candidate_version = self.candidate.updated_at.isoformat()
        accepted = self._json(
            "post",
            f"/api/v1/governance/proposals/{self.proposal.pk}/candidates/{self.candidate.pk}/review",
            {
                "status": "ACCEPTED",
                "epistemic_status": "INFERRED_PENDING_REVIEW",
                "note": "Accepted after source comparison.",
                "evidence_ids": [str(self.evidence.pk)],
            },
            HTTP_IF_MATCH=f'"{candidate_version}"',
        )
        self.assertEqual(accepted.status_code, 200, accepted.content)
        self.proposal.refresh_from_db()
        submitted = self._json(
            "post",
            f"/api/v1/governance/proposals/{self.proposal.pk}/submit",
            {},
            HTTP_IF_MATCH=f'"{self.proposal.updated_at.isoformat()}"',
        )
        self.assertEqual(submitted.status_code, 200, submitted.content)
        self._login(self.reviewer)
        approved = self._json(
            "post",
            f"/api/v1/governance/proposals/{self.proposal.pk}/review",
            {
                "decision": "APPROVE",
                "comment": "Evidence, diff, and validation reviewed independently.",
            },
            HTTP_IF_MATCH=f'"{submitted.json()["version"]}"',
        )
        self.assertEqual(approved.status_code, 200, approved.content)
        published = self._json(
            "post",
            f"/api/v1/governance/proposals/{self.proposal.pk}/publish",
            {
                "confirmation": "I reviewed the semantic diff, impact analysis, validation report, and evidence."
            },
            HTTP_IF_MATCH=f'"{approved.json()["version"]}"',
        )
        self.assertEqual(published.status_code, 200, published.content)
        self.revision.refresh_from_db()
        self.proposal.refresh_from_db()
        self.assertEqual(self.revision.status, "PUBLISHED")
        self.assertEqual(self.proposal.status, ProposalStatus.APPLIED.value)
        receipt = Publication.objects.get(proposal=self.proposal)
        self.assertEqual(receipt.revision_id, self.revision.pk)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="GOVERNANCE_PUBLICATION_CREATED", object_id=str(receipt.pk)
            ).exists()
        )
