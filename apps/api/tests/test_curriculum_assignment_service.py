from __future__ import annotations

import datetime

import pytest
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.utils import timezone

from domain.enums import (
    CurriculumAssignmentContext,
    CurriculumAssignmentPolicyStatus,
    EpistemicStatus,
    RevisionStatus,
    UserRole,
)
from domain.errors import PublishedAssignmentPolicyImmutableError
from modules.curriculum.application.assignment import (
    CurriculumAssignmentPolicyError,
    publish_assignment_policy,
    resolve_assignment_preview,
)
from modules.curriculum.models import (
    CurriculumAssignmentPolicy,
    CurriculumAssignmentPolicyEvidence,
)
from modules.governance.models import Evidence, NormativeDocument, SourceSnapshot
from modules.identity.models import RoleAssignment, User
from modules.offerings.models import AcademicTerm
from modules.student_records.models import (
    CurriculumAssignmentDecision,
    CurriculumAssignmentOverrideAuthorization,
    ProgramEnrollment,
)
from tests.factories import foundation


class CurriculumAssignmentPolicyTests(TestCase):
    def setUp(self) -> None:
        self.data = foundation(suffix="-assignment-policy")
        self.data["revision"].status = RevisionStatus.PUBLISHED.value
        self.data["revision"].published_at = timezone.now()
        self.data["revision"].content_hash = "3" * 64
        self.data["revision"].source_set_hash = "4" * 64
        self.data["revision"].save(
            update_fields=(
                "status",
                "published_at",
                "content_hash",
                "source_set_hash",
                "updated_at",
            )
        )
        document = NormativeDocument.objects.create(
            issuer="Test University",
            document_type="Academic agreement",
            number="17",
            year=2025,
            title="Verified curriculum assignment policy",
            publication_date=datetime.date(2025, 6, 1),
        )
        snapshot = SourceSnapshot.objects.create(
            document=document,
            captured_at=timezone.now(),
            sha256="1" * 64,
            mime_type="application/pdf",
            storage_key="test/policy-17.pdf",
        )
        self.data["term"].source_snapshot = snapshot
        self.data["term"].save(update_fields=("source_snapshot", "updated_at"))
        self.author = User.objects.create_user(
            email="policy.author@example.test", password="safe-test-password"
        )
        self.evidence = Evidence.objects.create(
            snapshot=snapshot,
            page=3,
            section="Article 2",
            excerpt_hash="2" * 64,
            excerpt="Applies to admissions from 2026-1.",
        )
        RoleAssignment.objects.create(
            user=self.data["user"],
            role=UserRole.REVIEWER.value,
            institution=self.data["institution"],
            program=self.data["program"],
        )

    def policy(self, **overrides: object) -> CurriculumAssignmentPolicy:
        values: dict[str, object] = {
            "policy_code": "STAT-ADMISSION",
            "version": 1,
            "program": self.data["program"],
            "plan": self.data["plan"],
            "revision_basis": self.data["revision"],
            "context": CurriculumAssignmentContext.ADMISSION.value,
            "admission_from": datetime.date(2026, 1, 1),
            "normative_published_on": datetime.date(2025, 6, 1),
            "effective_from": datetime.date(2026, 1, 1),
            "status": CurriculumAssignmentPolicyStatus.IN_REVIEW.value,
            "epistemic_status": EpistemicStatus.VERIFIED.value,
            "prepared_by": self.author,
        }
        values.update(overrides)
        policy = CurriculumAssignmentPolicy.objects.create(**values)
        CurriculumAssignmentPolicyEvidence.objects.create(
            policy=policy,
            evidence=self.evidence,
            purpose="Admission boundary and target plan",
        )
        return policy

    def test_publish_hashes_evidence_and_resolver_selects_exact_policy(self) -> None:
        policy = publish_assignment_policy(self.policy().pk, actor=self.data["user"])
        self.assertEqual(policy.status, CurriculumAssignmentPolicyStatus.PUBLISHED.value)
        self.assertEqual(len(policy.content_hash), 64)
        self.assertEqual(len(policy.source_set_hash), 64)
        decision = resolve_assignment_preview(
            program_id=self.data["program"].pk,
            admission_date=datetime.date(2026, 1, 2),
            context=CurriculumAssignmentContext.ADMISSION.value,
            admission_verification_method="SOURCE_SNAPSHOT",
            admission_source_snapshot_id=self.data["term"].source_snapshot_id,
            admission_source_sha256=self.data["term"].source_snapshot.sha256,
        )
        self.assertEqual(decision["status"], "RESOLVED")
        self.assertEqual(decision["selected_policy_id"], str(policy.pk))
        self.assertEqual(decision["selected_revision_id"], str(self.data["revision"].pk))

    def test_verified_policy_cannot_publish_without_publication_date(self) -> None:
        policy = self.policy(normative_published_on=None)
        with pytest.raises(CurriculumAssignmentPolicyError) as error:
            publish_assignment_policy(policy.pk, actor=self.data["user"])
        self.assertEqual(error.value.code, "assignment_policy_publication_date_required")

    def test_published_policy_and_evidence_are_immutable(self) -> None:
        policy = publish_assignment_policy(self.policy().pk, actor=self.data["user"])
        policy.cohort_code = "changed"
        with pytest.raises(PublishedAssignmentPolicyImmutableError):
            policy.save()
        link = policy.evidence_links.get()
        link.purpose = "changed"
        with pytest.raises(PublishedAssignmentPolicyImmutableError):
            link.save()

    def test_direct_model_publication_is_rejected(self) -> None:
        policy = self.policy()
        policy.status = CurriculumAssignmentPolicyStatus.PUBLISHED.value
        policy.content_hash = "a" * 64
        policy.source_set_hash = "b" * 64
        policy.published_at = timezone.now()
        with pytest.raises(PublishedAssignmentPolicyImmutableError):
            policy.save()

    def test_live_evidence_edits_do_not_change_the_sealed_policy_decision(self) -> None:
        policy = publish_assignment_policy(self.policy().pk, actor=self.data["user"])
        before = resolve_assignment_preview(
            program_id=self.data["program"].pk,
            admission_date=datetime.date(2026, 2, 1),
            context="ADMISSION",
            admission_verification_method="SOURCE_SNAPSHOT",
            admission_source_snapshot_id=self.data["term"].source_snapshot_id,
            admission_source_sha256=self.data["term"].source_snapshot.sha256,
        )
        self.evidence.excerpt = "A later annotation must not rewrite a sealed decision."
        self.evidence.excerpt_hash = "9" * 64
        self.evidence.save(update_fields=("excerpt", "excerpt_hash", "updated_at"))
        after = resolve_assignment_preview(
            program_id=self.data["program"].pk,
            admission_date=datetime.date(2026, 2, 1),
            context="ADMISSION",
            admission_verification_method="SOURCE_SNAPSHOT",
            admission_source_snapshot_id=self.data["term"].source_snapshot_id,
            admission_source_sha256=self.data["term"].source_snapshot.sha256,
        )
        self.assertEqual(before["decision_hash"], after["decision_hash"])
        self.assertEqual(after["selected_policy_id"], str(policy.pk))

    def test_pending_enrollment_is_activated_only_by_a_later_verified_policy(self) -> None:
        RoleAssignment.objects.create(
            user=self.data["user"],
            role=UserRole.ADMIN.value,
            institution=self.data["institution"],
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.data["user"])
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        preview = client.post(
            "/api/v1/admin/students/assignment-preview",
            data={
                "program_id": str(self.data["program"].pk),
                "admission_term_id": str(self.data["term"].pk),
                "admission_record_reference": "SIA-PENDING-001",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        ).json()
        self.assertEqual(preview["status"], "UNKNOWN")
        created = client.post(
            "/api/v1/admin/students/enrollments",
            data={
                "email": "pending.assignment@example.test",
                "temporary_password": "SafeEnrollment!2026-Xp4",
                "first_name": "Asignación",
                "first_surname": "Pendiente",
                "birth_date": "2004-08-19",
                "student_number": "PENDING-001",
                "institution_id": str(self.data["institution"].pk),
                "program_id": str(self.data["program"].pk),
                "admission_term_id": str(self.data["term"].pk),
                "admission_record_reference": "SIA-PENDING-001",
                "expected_assignment_hash": preview["decision_hash"],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.json()["status"], "NEEDS_REVIEW")
        self.assertIsNone(created.json()["plan_id"])
        enrollment = ProgramEnrollment.objects.get(pk=created.json()["id"])
        first = enrollment.assignment_decisions.get()
        self.assertEqual(first.method, "POLICY_EVALUATION")

        policy = publish_assignment_policy(self.policy().pk, actor=self.data["user"])
        activated = client.patch(
            f"/api/v1/admin/students/enrollments/{enrollment.pk}/revision",
            data={},
            content_type="application/json",
            HTTP_IF_MATCH=f'"{created.json()["version"]}"',
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(activated.status_code, 200, activated.content)
        self.assertEqual(activated.json()["status"], "ACTIVE")
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.plan_id, self.data["plan"].pk)
        decisions = list(enrollment.assignment_decisions.order_by("created_at"))
        self.assertEqual(len(decisions), 2)
        self.assertEqual(decisions[-1].policy_id, policy.pk)
        self.assertEqual(decisions[-1].method, "AUTOMATIC")
        self.assertNotEqual(decisions[0].decision_hash, decisions[-1].decision_hash)

    def test_governed_override_requires_closed_reason_evidence_and_appends_decision(self) -> None:
        RoleAssignment.objects.create(
            user=self.data["user"],
            role=UserRole.ADMIN.value,
            institution=self.data["institution"],
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.data["user"])
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        preview = client.post(
            "/api/v1/admin/students/assignment-preview",
            data={
                "program_id": str(self.data["program"].pk),
                "admission_term_id": str(self.data["term"].pk),
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        ).json()
        created = client.post(
            "/api/v1/admin/students/enrollments",
            data={
                "email": "override.assignment@example.test",
                "temporary_password": "SafeEnrollment!2026-Xp4",
                "first_name": "Asignación",
                "first_surname": "Excepcional",
                "birth_date": "2004-08-19",
                "student_number": "OVERRIDE-001",
                "institution_id": str(self.data["institution"].pk),
                "program_id": str(self.data["program"].pk),
                "admission_term_id": str(self.data["term"].pk),
                "expected_assignment_hash": preview["decision_hash"],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        authorization_path = (
            f"/api/v1/admin/students/enrollments/{created.json()['id']}"
            "/assignment-override-authorizations"
        )
        invalid = client.post(
            authorization_path,
            data={
                "plan_id": str(self.data["plan"].pk),
                "revision_basis_id": str(self.data["revision"].pk),
                "evidence_id": str(self.evidence.pk),
                "reason_code": "FREE_TEXT_IS_NOT_ALLOWED",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(invalid.status_code, 422, invalid.content)
        preparer = User.objects.create_user(
            email="override.preparer@example.test", password="safe-test-password"
        )
        RoleAssignment.objects.create(
            user=preparer,
            role=UserRole.ADMIN.value,
            institution=self.data["institution"],
        )
        client.force_login(preparer)
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        prepared = client.post(
            authorization_path,
            data={
                "plan_id": str(self.data["plan"].pk),
                "revision_basis_id": str(self.data["revision"].pk),
                "evidence_id": str(self.evidence.pk),
                "reason_code": "ADMISSION_POLICY_EXCEPTION",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(prepared.status_code, 201, prepared.content)
        self.assertEqual(prepared.json()["status"], "DRAFT")
        client.force_login(self.data["user"])
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        approved = client.post(
            "/api/v1/admin/students/assignment-override-authorizations/"
            f"{prepared.json()['id']}/approve",
            data={},
            content_type="application/json",
            HTTP_IF_MATCH=f'"{prepared.json()["version"]}"',
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(approved.status_code, 200, approved.content)
        self.assertEqual(approved.json()["status"], "APPROVED")
        overridden = client.post(
            f"/api/v1/admin/students/enrollments/{created.json()['id']}/assignment-override",
            data={"authorization_id": approved.json()["id"]},
            content_type="application/json",
            HTTP_IF_MATCH=f'"{created.json()["version"]}"',
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(overridden.status_code, 200, overridden.content)
        self.assertEqual(overridden.json()["status"], "ACTIVE")
        enrollment = ProgramEnrollment.objects.get(pk=created.json()["id"])
        decision = enrollment.assignment_decisions.order_by("-created_at").first()
        self.assertEqual(decision.method, "ADMIN_OVERRIDE")
        self.assertEqual(decision.override_evidence_id, self.evidence.pk)
        self.assertEqual(str(decision.override_authorization_id), approved.json()["id"])
        self.assertEqual(decision.override_reason_code, "ADMISSION_POLICY_EXCEPTION")
        authorization = CurriculumAssignmentOverrideAuthorization.objects.get(
            pk=approved.json()["id"]
        )
        self.assertEqual(len(authorization.content_hash), 64)
        with pytest.raises(ValidationError):
            authorization.reason_code = "LEGACY_RECORD_VERIFIED"
            authorization.save()

    def test_reentry_derives_previous_plan_and_creates_a_second_enrollment(self) -> None:
        RoleAssignment.objects.create(
            user=self.data["user"],
            role=UserRole.ADMIN.value,
            institution=self.data["institution"],
        )
        policy = publish_assignment_policy(
            self.policy(
                policy_code="STAT-REENTRY",
                context=CurriculumAssignmentContext.REENTRY.value,
                previous_plan=self.data["plan"],
            ).pk,
            actor=self.data["user"],
        )
        term = AcademicTerm.objects.create(
            institution=self.data["institution"],
            campus=self.data["campus"],
            code="2027-1-REENTRY",
            starts_at=timezone.now() + datetime.timedelta(days=365),
            ends_at=timezone.now() + datetime.timedelta(days=500),
            source_snapshot=self.data["term"].source_snapshot,
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.data["user"])
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        path = f"/api/v1/admin/students/enrollments/{self.data['enrollment'].pk}/transition-preview"
        preview = client.post(
            path,
            data={
                "admission_term_id": str(term.pk),
                "context": "REENTRY",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(preview.status_code, 200, preview.content)
        self.assertEqual(preview.json()["status"], "RESOLVED")
        self.assertEqual(preview.json()["input"]["previous_plan_id"], str(self.data["plan"].pk))
        created = client.post(
            f"/api/v1/admin/students/enrollments/{self.data['enrollment'].pk}/transitions",
            data={
                "admission_term_id": str(term.pk),
                "context": "REENTRY",
                "expected_assignment_hash": preview.json()["decision_hash"],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(created.status_code, 201, created.content)
        new_enrollment = ProgramEnrollment.objects.get(pk=created.json()["id"])
        self.assertEqual(new_enrollment.student_id, self.data["student"].pk)
        self.assertEqual(new_enrollment.plan_id, self.data["plan"].pk)
        self.assertEqual(new_enrollment.assignment_decisions.get().policy_id, policy.pk)
        self.assertEqual(
            new_enrollment.transition_events[0]["source_enrollment_id"],
            str(self.data["enrollment"].pk),
        )

    def test_unknown_published_policy_can_explain_but_not_resolve(self) -> None:
        policy = self.policy(
            epistemic_status=EpistemicStatus.UNKNOWN.value,
            normative_published_on=None,
        )
        publish_assignment_policy(policy.pk, actor=self.data["user"])
        decision = resolve_assignment_preview(
            program_id=self.data["program"].pk,
            admission_date=datetime.date(2026, 2, 1),
            context=CurriculumAssignmentContext.ADMISSION.value,
        )
        self.assertEqual(decision["status"], "NEEDS_REVIEW")
        self.assertEqual(decision["reason_codes"], ["EVIDENCE_INSUFFICIENT"])

    def test_authorized_admin_preview_returns_trace_and_never_a_first_revision_fallback(
        self,
    ) -> None:
        RoleAssignment.objects.create(
            user=self.data["user"],
            role=UserRole.ADMIN.value,
            institution=self.data["institution"],
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.data["user"])
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        unresolved = client.post(
            "/api/v1/admin/students/assignment-preview",
            data={
                "program_id": str(self.data["program"].pk),
                "admission_term_id": str(self.data["term"].pk),
                "context": "ADMISSION",
                "cohort_code": self.data["term"].code,
                "admission_record_reference": "SIA-ADM-2026-001",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(unresolved.status_code, 200, unresolved.content)
        self.assertEqual(unresolved.json()["status"], "UNKNOWN")
        self.assertIsNone(unresolved.json()["selected_revision_id"])
        self.assertEqual(unresolved.json()["reason_codes"], ["NO_APPLICABLE_POLICY"])

        policy = publish_assignment_policy(self.policy().pk, actor=self.data["user"])
        resolved = client.post(
            "/api/v1/admin/students/assignment-preview",
            data={
                "program_id": str(self.data["program"].pk),
                "admission_term_id": str(self.data["term"].pk),
                "context": "ADMISSION",
                "cohort_code": self.data["term"].code,
                "admission_record_reference": "SIA-ADM-2026-001",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(resolved.status_code, 200, resolved.content)
        body = resolved.json()
        self.assertEqual(body["status"], "RESOLVED")
        self.assertEqual(body["selected_policy_id"], str(policy.pk))
        self.assertEqual(body["selected_plan_code"], self.data["plan"].code)
        self.assertEqual(body["selected_revision_code"], self.data["revision"].revision_code)
        self.assertEqual(len(body["decision_hash"]), 64)
        self.assertEqual(body["admission_term_source_status"], "VERIFIED")

        stale_payload = {
            "email": "stale.assignment@example.test",
            "temporary_password": "SafeEnrollment!2026-Xp4",
            "first_name": "Asignación",
            "first_surname": "Obsoleta",
            "birth_date": "2004-08-19",
            "student_number": "AUTO-STALE",
            "institution_id": str(self.data["institution"].pk),
            "program_id": str(self.data["program"].pk),
            "admission_term_id": str(self.data["term"].pk),
            "cohort_code": self.data["term"].code,
            "assignment_context": "ADMISSION",
            "admission_record_reference": "SIA-ADM-2026-001",
            "expected_assignment_hash": "f" * 64,
        }
        stale = client.post(
            "/api/v1/admin/students/enrollments",
            data=stale_payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(stale.status_code, 409, stale.content)
        self.assertFalse(User.objects.filter(email=stale_payload["email"]).exists())

        created = client.post(
            "/api/v1/admin/students/enrollments",
            data={
                "email": "automatic.assignment@example.test",
                "temporary_password": "SafeEnrollment!2026-Xp4",
                "first_name": "Asignación",
                "first_surname": "Automática",
                "birth_date": "2004-08-19",
                "student_number": "AUTO-001",
                "institution_id": str(self.data["institution"].pk),
                "program_id": str(self.data["program"].pk),
                "admission_term_id": str(self.data["term"].pk),
                "cohort_code": self.data["term"].code,
                "assignment_context": "ADMISSION",
                "admission_record_reference": "SIA-ADM-2026-001",
                "expected_assignment_hash": body["decision_hash"],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(created.status_code, 201, created.content)
        enrollment = ProgramEnrollment.objects.get(pk=created.json()["id"])
        self.assertEqual(enrollment.plan_id, self.data["plan"].pk)
        self.assertEqual(enrollment.revision_basis_id, self.data["revision"].pk)
        self.assertEqual(enrollment.status, "ACTIVE")
        decision = CurriculumAssignmentDecision.objects.get(enrollment=enrollment)
        self.assertEqual(decision.policy_id, policy.pk)
        self.assertEqual(decision.method, "AUTOMATIC")
        self.assertEqual(decision.decision_hash, body["decision_hash"])

    def test_assignment_preview_is_scoped_to_authorized_administrators(self) -> None:
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.data["user"])
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/v1/admin/students/assignment-preview",
            data={
                "program_id": str(self.data["program"].pk),
                "admission_term_id": str(self.data["term"].pk),
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(response.status_code, 403, response.content)
