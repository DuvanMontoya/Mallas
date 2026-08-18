from __future__ import annotations

from django.test import Client, TestCase

from domain.enums import (
    AttemptStatus,
    EnrollmentStatus,
    EpistemicStatus,
    MembershipRole,
    RequirementGroupKind,
    RequirementPurpose,
)
from modules.audit.application.services import run_degree_audit
from modules.curriculum.models import Course, CourseVersion, PlanMembership, RequirementGroup
from modules.governance.models import Evidence, NormativeDocument, SourceSnapshot
from modules.rules.models import Requirement
from modules.student_records.models import CourseAttempt
from tests.factories import foundation


class AcademicOverviewApiTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.data = foundation(suffix="-overview")
        self.user = self.data["user"]
        self.enrollment = self.data["enrollment"]
        self.revision = self.data["revision"]
        self.revision.total_required_credits = 4
        self.revision.save(update_fields=["total_required_credits"])

    def test_empty_enrollment_is_explicitly_no_history(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get("/api/v1/academic-overview")

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["state"], "NO_HISTORY")
        self.assertFalse(payload["history"]["has_records"])
        self.assertEqual(payload["audit"]["overall"]["applied_credits"], 0)
        self.assertTrue(any(item["code"] == "HISTORY_NOT_LOADED" for item in payload["warnings"]))
        etag_value = (
            payload["audit"]["metadata"]["result_hash"]
            or payload["audit"]["metadata"]["revision_hash"]
        )
        self.assertEqual(response["ETag"], f'"{etag_value}"')

    def test_needs_review_enrollment_fails_closed_without_audit_conclusions(self) -> None:
        self.enrollment.status = EnrollmentStatus.NEEDS_REVIEW.value
        self.enrollment.save(update_fields=["status", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get("/api/v1/academic-overview")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "ENROLLMENT_NEEDS_REVIEW")
        self.assertNotIn("audit", response.json())

    def test_read_model_preserves_unknown_external_requirement_and_backend_eligibility(
        self,
    ) -> None:
        component = self.data["group"]
        component.metadata = {"source_component_id": "CORE-overview"}
        component.save(update_fields=["metadata"])
        bucket = RequirementGroup.objects.create(
            revision=self.revision,
            parent=component,
            code="BUCKET-overview",
            label="Required courses",
            kind=RequirementGroupKind.GROUP.value,
            required_credits=4,
            metadata={"source_component_id": "CORE-overview"},
        )
        PlanMembership.objects.create(
            revision=self.revision,
            course_version=self.data["course_version"],
            group=bucket,
            role=MembershipRole.MANDATORY.value,
        )

        course_two = Course.objects.create(
            institution=self.data["institution"], code="STAT102-overview"
        )
        version_two = CourseVersion.objects.create(
            course=course_two,
            name="Probability foundations",
            credits=4,
            valid_from=self.data["course_version"].valid_from,
        )
        PlanMembership.objects.create(
            revision=self.revision,
            course_version=version_two,
            group=bucket,
            role=MembershipRole.ELECTIVE_OPTION.value,
        )
        course_three = Course.objects.create(
            institution=self.data["institution"], code="STAT103-overview"
        )
        version_three = CourseVersion.objects.create(
            course=course_three,
            name="Data laboratory",
            credits=4,
            valid_from=self.data["course_version"].valid_from,
        )
        PlanMembership.objects.create(
            revision=self.revision,
            course_version=version_three,
            group=bucket,
            role=MembershipRole.ELECTIVE_OPTION.value,
        )
        Requirement.objects.create(
            revision=self.revision,
            owner_type="COURSE",
            owner_id=course_two.pk,
            code="PREREQ:STAT102-overview",
            purpose=RequirementPurpose.ENROLLMENT_PREREQUISITE.value,
            ast={"type": "COURSE_PASSED", "course_code": self.data["course"].code},
            epistemic_status=EpistemicStatus.VERIFIED.value,
        )
        Requirement.objects.create(
            revision=self.revision,
            owner_type="REVISION",
            owner_id=self.revision.pk,
            code="GRADUATION:FOREIGN_LANGUAGE_B1",
            purpose=RequirementPurpose.GRADUATION.value,
            ast={"type": "EXTERNAL_REQUIREMENT", "key": "FOREIGN_LANGUAGE_B1"},
            epistemic_status=EpistemicStatus.VERIFIED.value,
            metadata={
                "note": "Acreditación externa pendiente de verificación.",
                "source_url": "https://example.test/b1",
            },
        )
        document = NormativeDocument.objects.create(
            issuer="Test University",
            document_type="REGULATION",
            number="1",
            year=2026,
            title="Academic regulation",
        )
        snapshot = SourceSnapshot.objects.create(
            document=document,
            captured_at=self.data["term"].starts_at,
            sha256="a" * 64,
            mime_type="application/pdf",
            storage_key="sources/test/regulation.pdf",
        )
        evidence = Evidence.objects.create(
            snapshot=snapshot,
            page=3,
            line_locator="graduation:b1",
            excerpt_hash="b" * 64,
            excerpt="External requirement evidence",
            annotation="Archived test evidence.",
        )
        external = Requirement.objects.get(code="GRADUATION:FOREIGN_LANGUAGE_B1")
        external.evidence.add(evidence)
        CourseAttempt.objects.create(
            enrollment=self.enrollment,
            course_version=self.data["course_version"],
            term=self.data["term"],
            status=AttemptStatus.PASSED.value,
            credits_earned=4,
        )
        run_degree_audit(self.enrollment.pk)
        self.client.force_login(self.user)

        response = self.client.get(f"/api/v1/academic-overview?enrollment_id={self.enrollment.pk}")

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["state"], "INCOMPLETE")
        self.assertEqual(payload["audit"]["overall"]["applied_credits"], 4)
        self.assertEqual(payload["audit"]["overall"]["credit_progress_percent"], 100)
        self.assertEqual(payload["audit"]["overall"]["status"], "UNKNOWN")
        external_payload = payload["external_graduation_requirements"][0]
        self.assertEqual(external_payload["status"], "UNKNOWN")
        self.assertEqual(external_payload["evidence"][0]["locator"], "graduation:b1")
        self.assertEqual(external_payload["source_url"], "https://example.test/b1")
        self.assertIn("STAT102-overview", {item["code"] for item in payload["eligible_courses"]})
        self.assertIn("STAT103-overview", {item["code"] for item in payload["unknown_courses"]})
        self.assertNotEqual(payload["audit"]["overall"]["status"], "SATISFIED")

    def test_enrollment_overview_is_not_an_idor(self) -> None:
        other = foundation(suffix="-overview-other")["user"]
        self.client.force_login(other)

        response = self.client.get(f"/api/v1/academic-overview?enrollment_id={self.enrollment.pk}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "OVERVIEW_FORBIDDEN")
