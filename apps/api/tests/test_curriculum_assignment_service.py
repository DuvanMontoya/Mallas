from __future__ import annotations

import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.core.exceptions import ValidationError
from django.db import OperationalError, close_old_connections, connection, transaction
from django.test import Client, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from domain.enums import (
    CurriculumAssignmentContext,
    CurriculumAssignmentPolicyStatus,
    EpistemicStatus,
    RevisionStatus,
    UserRole,
)
from domain.errors import PublishedAssignmentPolicyImmutableError
from domain.revision import canonical_content_hash
from modules.curriculum.application.assignment import (
    CurriculumAssignmentPolicyError,
    publish_assignment_policy,
    resolve_assignment_preview,
    submit_assignment_policy,
)
from modules.curriculum.application.services import CurriculumRevisionService
from modules.curriculum.models import (
    CurriculumAssignmentPolicy,
    CurriculumAssignmentPolicyEvidence,
)
from modules.governance.models import Evidence, NormativeDocument, SourceSnapshot
from modules.identity.application.audit import digest_identifier
from modules.identity.models import RoleAssignment, User
from modules.offerings.application.importer import (
    OfferingImportError,
    SourceDescriptor,
    import_offering_payload,
)
from modules.offerings.models import AcademicTerm
from modules.student_records.application.administration import (
    StudentAdministrationError,
    verify_admission_fact,
)
from modules.student_records.models import (
    AcademicException,
    CurriculumAssignmentDecision,
    CurriculumAssignmentOverrideAuthorization,
    EnrollmentTransition,
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
        self.scope_evidence = Evidence.objects.create(
            snapshot=snapshot,
            page=3,
            section="Article 2 scope",
            excerpt_hash="5" * 64,
            excerpt="Admissions from 2026-1 are within scope.",
        )
        self.target_evidence = Evidence.objects.create(
            snapshot=snapshot,
            page=4,
            section="Article 3 target",
            excerpt_hash="6" * 64,
            excerpt="The target is the archived curriculum revision.",
        )
        self.context_evidence = Evidence.objects.create(
            snapshot=snapshot,
            page=5,
            section="Article 4 context",
            excerpt_hash="7" * 64,
            excerpt="The contextual rule is explicitly documented.",
        )
        self.override_evidence = Evidence.objects.create(
            snapshot=snapshot,
            page=6,
            section="Article 5 override authority",
            excerpt_hash="8" * 64,
            excerpt="A governed individual assignment override may be authorized.",
        )
        RoleAssignment.objects.create(
            user=self.author,
            role=UserRole.EDITOR.value,
            institution=self.data["institution"],
            program=self.data["program"],
        )
        RoleAssignment.objects.create(
            user=self.data["user"],
            role=UserRole.REVIEWER.value,
            institution=self.data["institution"],
            program=self.data["program"],
        )
        self.admission_verifier = User.objects.create_user(
            email="admission.verifier@example.test", password="safe-test-password"
        )
        RoleAssignment.objects.create(
            user=self.admission_verifier,
            role=UserRole.ADMIN.value,
            institution=self.data["institution"],
            program=self.data["program"],
        )
        self.admission_reference = "SIA-ADM-2026-001"
        self.admission_evidence = self.make_admission_evidence(
            self.data["term"], self.admission_reference
        )
        verify_admission_fact(
            actor=self.admission_verifier,
            program_id=self.data["program"].pk,
            admission_term_id=self.data["term"].pk,
            evidence_id=self.admission_evidence.pk,
            record_reference=self.admission_reference,
        )

    def make_admission_evidence(
        self,
        term: AcademicTerm,
        record_reference: str,
        *,
        subject_identifier: str = "AUTO-001",
    ) -> Evidence:
        reference_hash = digest_identifier(f"admission-record:{record_reference}")
        document = NormativeDocument.objects.create(
            issuer="Test University Admissions Registry",
            document_type="Institutional admission record",
            number=f"ADM-{record_reference}",
            year=term.starts_at.year,
            title=f"Signed admission receipt {term.code}",
            publication_date=term.starts_at.date(),
        )
        snapshot = SourceSnapshot.objects.create(
            document=document,
            captured_at=timezone.now(),
            sha256=canonical_content_hash(
                {"record_reference_hash": reference_hash, "term_id": str(term.pk)}
            ),
            mime_type="application/json",
            storage_key=f"test/admissions/{reference_hash}.json",
            metadata={
                "purpose": "STUDENT_ADMISSION_FACT",
                "artifact_type": "INSTITUTIONAL_ADMISSION_RECORD",
                "provider": "TEST_SIA_ADAPTER",
                "institution_id": str(self.data["institution"].pk),
                "program_id": str(self.data["program"].pk),
                "academic_term_id": str(term.pk),
                "record_reference_hash": reference_hash,
                "subject_identifier_hash": digest_identifier(
                    f"admission-subject:{subject_identifier}"
                ),
            },
        )
        excerpt = (
            "Signed institutional receipt binds the protected record reference to program and term."
        )
        return Evidence.objects.create(
            snapshot=snapshot,
            section="signed admission manifest",
            excerpt=excerpt,
            excerpt_hash=canonical_content_hash({"excerpt": excerpt}),
        )

    def policy(self, **overrides: object) -> CurriculumAssignmentPolicy:
        requested_status = overrides.pop("status", CurriculumAssignmentPolicyStatus.IN_REVIEW.value)
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
            "status": CurriculumAssignmentPolicyStatus.DRAFT.value,
            "epistemic_status": EpistemicStatus.VERIFIED.value,
            "prepared_by": self.author,
        }
        values.update(overrides)
        policy = CurriculumAssignmentPolicy.objects.create(**values)
        for evidence, purpose in (
            (self.evidence, "NORMATIVE_PUBLICATION"),
            (self.scope_evidence, "ASSIGNMENT_SCOPE"),
            (self.target_evidence, "TARGET_REVISION"),
            (self.context_evidence, "CONTEXT_RULE"),
            (self.override_evidence, "ASSIGNMENT_OVERRIDE_AUTHORITY"),
        ):
            CurriculumAssignmentPolicyEvidence.objects.create(
                policy=policy,
                evidence=evidence,
                purpose=purpose,
            )
        if requested_status == CurriculumAssignmentPolicyStatus.IN_REVIEW.value:
            policy = submit_assignment_policy(policy.pk, actor=self.author)
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
            admission_verification_method="VERIFIED_ADMISSION_FACT",
            admission_source_snapshot_id=self.admission_evidence.snapshot_id,
            admission_source_sha256=self.admission_evidence.snapshot.sha256,
            admission_fact_id=self.admission_evidence.admission_facts.get().pk,
            admission_fact_content_hash=self.admission_evidence.admission_facts.get().content_hash,
        )
        self.assertEqual(decision["status"], "RESOLVED")
        self.assertEqual(decision["selected_policy_id"], str(policy.pk))
        self.assertEqual(decision["selected_revision_id"], str(self.data["revision"].pk))

    def test_draft_must_be_submitted_by_preparer_before_distinct_reviewer_publishes(
        self,
    ) -> None:
        RoleAssignment.objects.create(
            user=self.author,
            role=UserRole.EDITOR.value,
            institution=self.data["institution"],
            program=self.data["program"],
        )
        RoleAssignment.objects.create(
            user=self.author,
            role=UserRole.REVIEWER.value,
            institution=self.data["institution"],
            program=self.data["program"],
        )
        policy = self.policy(status=CurriculumAssignmentPolicyStatus.DRAFT.value)
        with pytest.raises(CurriculumAssignmentPolicyError) as not_submitted:
            publish_assignment_policy(policy.pk, actor=self.data["user"])
        self.assertEqual(not_submitted.value.code, "assignment_policy_transition_invalid")

        policy = submit_assignment_policy(policy.pk, actor=self.author)
        self.assertEqual(policy.status, CurriculumAssignmentPolicyStatus.IN_REVIEW.value)
        with pytest.raises(CurriculumAssignmentPolicyError) as same_person:
            publish_assignment_policy(policy.pk, actor=self.author)
        self.assertEqual(same_person.value.code, "assignment_policy_separation_required")

        policy = publish_assignment_policy(policy.pk, actor=self.data["user"])
        self.assertEqual(policy.status, CurriculumAssignmentPolicyStatus.PUBLISHED.value)
        self.assertEqual(policy.approved_by_id, self.data["user"].pk)

    def test_verified_policy_cannot_publish_without_publication_date(self) -> None:
        policy = self.policy(
            normative_published_on=None,
            status=CurriculumAssignmentPolicyStatus.DRAFT.value,
        )
        with pytest.raises(CurriculumAssignmentPolicyError) as error:
            submit_assignment_policy(policy.pk, actor=self.author)
        self.assertEqual(error.value.code, "assignment_policy_publication_date_required")

    def test_normative_policy_evidence_cannot_be_relabelled_as_individual_admission(self) -> None:
        with pytest.raises(StudentAdministrationError) as error:
            verify_admission_fact(
                actor=self.admission_verifier,
                program_id=self.data["program"].pk,
                admission_term_id=self.data["term"].pk,
                evidence_id=self.evidence.pk,
                record_reference="SIA-NOT-IN-THE-MANIFEST",
            )
        self.assertEqual(error.value.code, "student_admin_admission_evidence_not_unique")

    def test_verified_admission_fact_freezes_term_before_enrollment_exists(self) -> None:
        term = AcademicTerm.objects.create(
            institution=self.data["institution"],
            campus=self.data["campus"],
            code="2029-1-ADMISSION-LOCK",
            starts_at=timezone.now() + datetime.timedelta(days=1095),
            ends_at=timezone.now() + datetime.timedelta(days=1230),
        )
        reference = "SIA-LOCK-2029-001"
        verify_admission_fact(
            actor=self.admission_verifier,
            program_id=self.data["program"].pk,
            admission_term_id=term.pk,
            evidence_id=self.make_admission_evidence(term, reference).pk,
            record_reference=reference,
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admission_verifier)
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        patched = client.patch(
            f"/api/v1/academic-terms/{term.pk}",
            data={"starts_at": (term.starts_at + datetime.timedelta(days=1)).isoformat()},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(patched.status_code, 409, patched.content)
        with self.assertRaises(OfferingImportError):
            import_offering_payload(
                {
                    "schema_version": "offerings/1.0.0",
                    "term": {
                        "code": term.code,
                        "starts_at": (term.starts_at + datetime.timedelta(days=1)).isoformat(),
                        "ends_at": term.ends_at.isoformat(),
                        "status": "PLANNED",
                    },
                    "offerings": [],
                },
                institution=self.data["institution"],
                campus=self.data["campus"],
                descriptor=SourceDescriptor(
                    key="test.admission-term-lock",
                    name="Test admission term lock",
                    url="https://example.test/term-lock.json",
                ),
            )

    def test_published_policy_and_evidence_are_immutable(self) -> None:
        policy = publish_assignment_policy(self.policy().pk, actor=self.data["user"])
        policy.cohort_code = "changed"
        with pytest.raises(PublishedAssignmentPolicyImmutableError):
            policy.save()
        link = policy.evidence_links.order_by("id").first()
        assert link is not None
        link.purpose = "changed"
        with pytest.raises(PublishedAssignmentPolicyImmutableError):
            link.save()

    def test_policy_and_evidence_are_frozen_while_under_review(self) -> None:
        policy = self.policy()
        review_hash = policy.content_hash
        policy.metadata = {"changed_after_submission": True}
        with pytest.raises(PublishedAssignmentPolicyImmutableError):
            policy.save()
        link = policy.evidence_links.order_by("id").first()
        assert link is not None
        with pytest.raises(PublishedAssignmentPolicyImmutableError):
            link.delete()
        policy.refresh_from_db()
        self.assertEqual(policy.content_hash, review_hash)

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
            admission_verification_method="VERIFIED_ADMISSION_FACT",
            admission_source_snapshot_id=self.admission_evidence.snapshot_id,
            admission_source_sha256=self.admission_evidence.snapshot.sha256,
            admission_fact_id=self.admission_evidence.admission_facts.get().pk,
            admission_fact_content_hash=self.admission_evidence.admission_facts.get().content_hash,
        )
        self.evidence.excerpt = "A later annotation must not rewrite a sealed decision."
        self.evidence.excerpt_hash = "9" * 64
        self.evidence.save(update_fields=("excerpt", "excerpt_hash", "updated_at"))
        after = resolve_assignment_preview(
            program_id=self.data["program"].pk,
            admission_date=datetime.date(2026, 2, 1),
            context="ADMISSION",
            admission_verification_method="VERIFIED_ADMISSION_FACT",
            admission_source_snapshot_id=self.admission_evidence.snapshot_id,
            admission_source_sha256=self.admission_evidence.snapshot.sha256,
            admission_fact_id=self.admission_evidence.admission_facts.get().pk,
            admission_fact_content_hash=self.admission_evidence.admission_facts.get().content_hash,
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
        verify_admission_fact(
            actor=self.admission_verifier,
            program_id=self.data["program"].pk,
            admission_term_id=self.data["term"].pk,
            evidence_id=self.make_admission_evidence(
                self.data["term"], "SIA-PENDING-001", subject_identifier="PENDING-001"
            ).pk,
            record_reference="SIA-PENDING-001",
        )
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
        publish_assignment_policy(
            self.policy(
                policy_code="STAT-OVERRIDE-EVIDENCE",
                context=CurriculumAssignmentContext.REENTRY.value,
                previous_plan=self.data["plan"],
            ).pk,
            actor=self.data["user"],
        )
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
        unrelated_evidence = Evidence.objects.create(
            snapshot=self.evidence.snapshot,
            page=9,
            section="Individual case for another student",
            excerpt_hash="7" * 64,
            excerpt="This individual record must not be shared within the program.",
        )
        unrelated_exception = AcademicException.objects.create(
            enrollment=self.data["enrollment"],
            exception_type="INDIVIDUAL_RECORD",
            rationale="Individual evidence isolation test",
        )
        unrelated_exception.evidence.add(unrelated_evidence)
        evidence_catalog = client.get(
            f"/api/v1/admin/students/enrollments/{created.json()['id']}"
            "/assignment-override-evidence"
        )
        self.assertEqual(evidence_catalog.status_code, 200, evidence_catalog.content)
        self.assertNotIn(
            str(unrelated_evidence.pk),
            {item["id"] for item in evidence_catalog.json()["items"]},
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
                "evidence_id": str(self.override_evidence.pk),
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
                "evidence_id": str(self.override_evidence.pk),
                "reason_code": "ADMISSION_POLICY_EXCEPTION",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(prepared.status_code, 201, prepared.content)
        self.assertEqual(prepared.json()["status"], "DRAFT")
        self.assertEqual(
            prepared.json()["evidence_source_title"],
            self.override_evidence.snapshot.document.title,
        )
        self.assertEqual(prepared.json()["evidence_locator"], "Article 5 override authority")
        self.assertEqual(prepared.json()["evidence_excerpt"], self.override_evidence.excerpt)
        frozen_excerpt_hash = prepared.json()["evidence_excerpt_hash"]
        self.override_evidence.excerpt = "A later edit must not change what the approver reviews."
        self.override_evidence.excerpt_hash = "9" * 64
        self.override_evidence.save(update_fields=("excerpt", "excerpt_hash", "updated_at"))
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
        self.assertEqual(approved.json()["evidence_excerpt_hash"], frozen_excerpt_hash)
        self.assertNotEqual(approved.json()["evidence_excerpt"], self.override_evidence.excerpt)
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
        self.assertEqual(decision.override_evidence_id, self.override_evidence.pk)
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
        self.data["enrollment"].status = "SUSPENDED"
        self.data["enrollment"].review_reasons = []
        self.data["enrollment"].save(update_fields=("status", "review_reasons", "updated_at"))
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
        reentry_reference = "SIA-REENTRY-2027-001"
        verify_admission_fact(
            actor=self.admission_verifier,
            program_id=self.data["program"].pk,
            admission_term_id=term.pk,
            evidence_id=self.make_admission_evidence(
                term,
                reentry_reference,
                subject_identifier=self.data["student"].student_number,
            ).pk,
            record_reference=reentry_reference,
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
                "admission_record_reference": reentry_reference,
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
                "admission_record_reference": reentry_reference,
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
        transition = EnrollmentTransition.objects.get(target_enrollment=new_enrollment)
        self.assertEqual(transition.source_enrollment_id, self.data["enrollment"].pk)
        self.assertEqual(transition.context, "REENTRY")
        self.assertEqual(transition.source_result_status, "SUSPENDED")

    def test_plan_transition_closes_source_and_rejects_reverse_chronology(self) -> None:
        RoleAssignment.objects.create(
            user=self.data["user"],
            role=UserRole.ADMIN.value,
            institution=self.data["institution"],
        )
        publish_assignment_policy(
            self.policy(
                policy_code="STAT-PLAN-TRANSITION",
                context=CurriculumAssignmentContext.PLAN_TRANSITION.value,
                previous_plan=self.data["plan"],
            ).pk,
            actor=self.data["user"],
        )
        later_term = AcademicTerm.objects.create(
            institution=self.data["institution"],
            campus=self.data["campus"],
            code="2028-1-TRANSITION",
            starts_at=self.data["term"].starts_at + datetime.timedelta(days=730),
            ends_at=self.data["term"].ends_at + datetime.timedelta(days=730),
            source_snapshot=self.data["term"].source_snapshot,
        )
        transition_reference = "SIA-TRANSITION-2028-001"
        verify_admission_fact(
            actor=self.admission_verifier,
            program_id=self.data["program"].pk,
            admission_term_id=later_term.pk,
            evidence_id=self.make_admission_evidence(
                later_term,
                transition_reference,
                subject_identifier=self.data["student"].student_number,
            ).pk,
            record_reference=transition_reference,
        )
        earlier_term = AcademicTerm.objects.create(
            institution=self.data["institution"],
            campus=self.data["campus"],
            code="2024-1-INVALID",
            starts_at=self.data["term"].starts_at - datetime.timedelta(days=365),
            ends_at=self.data["term"].ends_at - datetime.timedelta(days=365),
            source_snapshot=self.data["term"].source_snapshot,
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.data["user"])
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        path = f"/api/v1/admin/students/enrollments/{self.data['enrollment'].pk}"
        self.data["enrollment"].status = "NEEDS_REVIEW"
        self.data["enrollment"].review_reasons = ["LEGACY_REVIEW"]
        self.data["enrollment"].save(update_fields=("status", "review_reasons", "updated_at"))
        held = client.post(
            f"{path}/transition-preview",
            data={
                "admission_term_id": str(later_term.pk),
                "context": "PLAN_TRANSITION",
                "admission_record_reference": transition_reference,
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(held.status_code, 422, held.content)
        self.data["enrollment"].status = "ACTIVE"
        self.data["enrollment"].review_reasons = []
        self.data["enrollment"].save(update_fields=("status", "review_reasons", "updated_at"))
        invalid = client.post(
            f"{path}/transition-preview",
            data={"admission_term_id": str(earlier_term.pk), "context": "PLAN_TRANSITION"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(invalid.status_code, 422, invalid.content)
        preview = client.post(
            f"{path}/transition-preview",
            data={
                "admission_term_id": str(later_term.pk),
                "context": "PLAN_TRANSITION",
                "admission_record_reference": transition_reference,
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(preview.status_code, 200, preview.content)
        created = client.post(
            f"{path}/transitions",
            data={
                "admission_term_id": str(later_term.pk),
                "context": "PLAN_TRANSITION",
                "expected_assignment_hash": preview.json()["decision_hash"],
                "admission_record_reference": transition_reference,
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(created.status_code, 201, created.content)
        self.data["enrollment"].refresh_from_db()
        self.assertEqual(self.data["enrollment"].status, "TRANSITIONED")
        self.assertEqual(self.data["enrollment"].review_reasons, [])
        transition = EnrollmentTransition.objects.get(target_enrollment_id=created.json()["id"])
        self.assertEqual(transition.source_previous_status, "ACTIVE")
        self.assertEqual(transition.source_result_status, "TRANSITIONED")
        with pytest.raises(ValidationError):
            transition.delete()
        moved_term = client.patch(
            f"/api/v1/academic-terms/{later_term.pk}",
            data={
                "starts_at": (self.data["term"].starts_at - datetime.timedelta(days=30)).isoformat()
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(moved_term.status_code, 409, moved_term.content)

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
        verified_fact = client.post(
            "/api/v1/admin/students/admission-facts/verify",
            data={
                "program_id": str(self.data["program"].pk),
                "admission_term_id": str(self.data["term"].pk),
                "record_reference": self.admission_reference,
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(verified_fact.status_code, 200, verified_fact.content)
        self.assertEqual(verified_fact.json()["status"], "VERIFIED")
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
        self.assertEqual(body["admission_term_source_status"], "UNKNOWN")

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
        self.assertEqual(
            decision.admission_fact_id, self.admission_evidence.admission_facts.get().pk
        )

        reused = client.post(
            "/api/v1/admin/students/enrollments",
            data={
                "email": "reused.admission@example.test",
                "temporary_password": "SafeEnrollment!2026-Xp4",
                "first_name": "Admisión",
                "first_surname": "Reutilizada",
                "birth_date": "2004-08-19",
                "student_number": "AUTO-REUSED",
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
        self.assertEqual(reused.status_code, 409, reused.content)
        self.assertFalse(User.objects.filter(email="reused.admission@example.test").exists())

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

    def test_students_cannot_list_governance_assignment_policies(self) -> None:
        student_user = User.objects.create_user(
            email="policy.student@example.test", password="safe-test-password"
        )
        RoleAssignment.objects.create(
            user=student_user,
            role=UserRole.STUDENT.value,
            institution=self.data["institution"],
            program=self.data["program"],
        )
        client = Client()
        client.force_login(student_user)
        response = client.get("/api/v1/governance/assignment-policies")
        self.assertEqual(response.status_code, 403, response.content)

    def test_admission_manifest_cannot_be_consumed_by_a_different_student_number(self) -> None:
        RoleAssignment.objects.create(
            user=self.data["user"],
            role=UserRole.ADMIN.value,
            institution=self.data["institution"],
        )
        publish_assignment_policy(self.policy().pk, actor=self.data["user"])
        reference = "SIA-ADM-SUBJECT-BOUND"
        evidence = self.make_admission_evidence(
            self.data["term"], reference, subject_identifier="MANIFEST-OWNER"
        )
        with pytest.raises(StudentAdministrationError) as error:
            verify_admission_fact(
                actor=self.admission_verifier,
                program_id=self.data["program"].pk,
                admission_term_id=self.data["term"].pk,
                evidence_id=evidence.pk,
                record_reference=reference,
                source_enrollment_id=self.data["enrollment"].pk,
            )
        self.assertEqual(error.value.code, "student_admin_admission_subject_mismatch")

        fact = verify_admission_fact(
            actor=self.admission_verifier,
            program_id=self.data["program"].pk,
            admission_term_id=self.data["term"].pk,
            evidence_id=evidence.pk,
            record_reference=reference,
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.data["user"])
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        preview = client.post(
            "/api/v1/admin/students/assignment-preview",
            data={
                "program_id": str(self.data["program"].pk),
                "admission_term_id": str(self.data["term"].pk),
                "context": "ADMISSION",
                "cohort_code": self.data["term"].code,
                "admission_record_reference": reference,
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(preview.status_code, 200, preview.content)
        response = client.post(
            "/api/v1/admin/students/enrollments",
            data={
                "email": "wrong.subject@example.test",
                "temporary_password": "SafeEnrollment!2026-Xp4",
                "first_name": "Sujeto",
                "first_surname": "Incorrecto",
                "birth_date": "2004-08-19",
                "student_number": "DIFFERENT-STUDENT",
                "institution_id": str(self.data["institution"].pk),
                "program_id": str(self.data["program"].pk),
                "admission_term_id": str(self.data["term"].pk),
                "cohort_code": self.data["term"].code,
                "assignment_context": "ADMISSION",
                "admission_record_reference": reference,
                "expected_assignment_hash": preview.json()["decision_hash"],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )

        self.assertEqual(response.status_code, 422, response.content)
        self.assertEqual(response.json()["code"], "STUDENT_ADMIN_ADMISSION_SUBJECT_MISMATCH")
        self.assertFalse(User.objects.filter(email="wrong.subject@example.test").exists())
        self.assertFalse(CurriculumAssignmentDecision.objects.filter(admission_fact=fact).exists())

    def test_verified_admission_fact_uses_sealed_subject_after_snapshot_metadata_changes(
        self,
    ) -> None:
        snapshot = self.admission_evidence.snapshot
        snapshot.metadata = {
            **snapshot.metadata,
            "subject_identifier_hash": digest_identifier(
                f"admission-subject:{self.data['student'].student_number}"
            ),
        }
        snapshot.save(update_fields=("metadata", "updated_at"))

        with pytest.raises(StudentAdministrationError) as error:
            verify_admission_fact(
                actor=self.admission_verifier,
                program_id=self.data["program"].pk,
                admission_term_id=self.data["term"].pk,
                evidence_id=self.admission_evidence.pk,
                record_reference=self.admission_reference,
                source_enrollment_id=self.data["enrollment"].pk,
            )

        self.assertEqual(error.value.code, "student_admin_admission_subject_mismatch")


class CurriculumAssignmentPolicyConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self) -> None:
        self.data = foundation(suffix="-assignment-policy-lock")
        revision = self.data["revision"]
        revision.status = RevisionStatus.PUBLISHED.value
        revision.published_at = timezone.now()
        revision.content_hash = "a" * 64
        revision.source_set_hash = "b" * 64
        revision.save(
            update_fields=(
                "status",
                "published_at",
                "content_hash",
                "source_set_hash",
                "updated_at",
            )
        )
        author = User.objects.create_user(
            email="policy.lock.author@example.test", password="safe-test-password"
        )
        reviewer = User.objects.create_user(
            email="policy.lock.reviewer@example.test", password="safe-test-password"
        )
        for user, role in ((author, UserRole.EDITOR.value), (reviewer, UserRole.REVIEWER.value)):
            RoleAssignment.objects.create(
                user=user,
                role=role,
                institution=self.data["institution"],
                program=self.data["program"],
            )
        document = NormativeDocument.objects.create(
            issuer="Test University",
            document_type="Academic agreement",
            number="LOCK-17",
            year=2025,
            title="Concurrent assignment policy evidence",
            publication_date=datetime.date(2025, 6, 1),
        )
        snapshot = SourceSnapshot.objects.create(
            document=document,
            captured_at=timezone.now(),
            sha256="c" * 64,
            mime_type="application/pdf",
            storage_key="test/policy-lock-17.pdf",
        )
        policy = CurriculumAssignmentPolicy.objects.create(
            policy_code="STAT-LOCK",
            version=1,
            program=self.data["program"],
            plan=self.data["plan"],
            revision_basis=revision,
            context=CurriculumAssignmentContext.ADMISSION.value,
            admission_from=datetime.date(2026, 1, 1),
            normative_published_on=datetime.date(2025, 6, 1),
            effective_from=datetime.date(2026, 1, 1),
            status=CurriculumAssignmentPolicyStatus.DRAFT.value,
            epistemic_status=EpistemicStatus.VERIFIED.value,
            prepared_by=author,
        )
        purposes = (
            "NORMATIVE_PUBLICATION",
            "ASSIGNMENT_SCOPE",
            "TARGET_REVISION",
            "CONTEXT_RULE",
            "ASSIGNMENT_OVERRIDE_AUTHORITY",
        )
        for index, purpose in enumerate(purposes, start=1):
            excerpt = f"Verified concurrent policy evidence {index}."
            evidence = Evidence.objects.create(
                snapshot=snapshot,
                page=index,
                section=f"Section {index}",
                excerpt=excerpt,
                excerpt_hash=canonical_content_hash({"excerpt": excerpt}),
            )
            CurriculumAssignmentPolicyEvidence.objects.create(
                policy=policy, evidence=evidence, purpose=purpose
            )
        self.policy = submit_assignment_policy(policy.pk, actor=author)
        self.reviewer_id = reviewer.pk

    @skipUnlessDBFeature("has_select_for_update_of")  # type: ignore[untyped-decorator]
    def test_retirement_serializes_before_policy_publication(self) -> None:
        revision_id = self.data["revision"].pk
        policy_id = self.policy.pk
        retired = threading.Event()
        release_retirement = threading.Event()

        def retire_revision() -> None:
            close_old_connections()
            try:
                with transaction.atomic():
                    CurriculumRevisionService.retire(revision_id)
                    retired.set()
                    if not release_retirement.wait(timeout=5):
                        raise TimeoutError("The publication worker did not reach the lock in time.")
            finally:
                close_old_connections()

        def publish_policy() -> str:
            close_old_connections()
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("SET LOCAL lock_timeout = '500ms'")
                    reviewer = User.objects.get(pk=self.reviewer_id)
                    publish_assignment_policy(policy_id, actor=reviewer)
            except OperationalError:
                return "lock_timeout"
            finally:
                close_old_connections()
            return "published_without_waiting"

        with ThreadPoolExecutor(max_workers=2) as executor:
            retirement_future = executor.submit(retire_revision)
            self.assertTrue(retired.wait(timeout=5))
            publication_future = executor.submit(publish_policy)
            try:
                self.assertEqual(
                    publication_future.result(timeout=5),
                    "lock_timeout",
                    "Publication did not attempt to lock the revision row.",
                )
            finally:
                release_retirement.set()
            retirement_future.result(timeout=5)

        self.policy.refresh_from_db()
        self.assertEqual(self.policy.status, CurriculumAssignmentPolicyStatus.IN_REVIEW.value)
