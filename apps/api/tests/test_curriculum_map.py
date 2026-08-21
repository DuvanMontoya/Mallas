from __future__ import annotations

import datetime
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from domain.enums import AttemptOrigin, AttemptStatus, OfferingStatus
from modules.curriculum.models import CourseVersion, CurriculumRevision
from modules.imports.application.services import import_curriculum_baseline
from modules.offerings.models import AcademicTerm, CourseOffering
from modules.student_records.models import CourseAttempt, ProgramEnrollment, StudentProfile

BASELINE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "curricula"
    / "unal"
    / "bogota"
    / "estadistica"
    / "2514"
    / "plan_2514_acuerdo_496_2023.json"
)


class CurriculumMapApiTests(TestCase):
    def setUp(self) -> None:
        imported = import_curriculum_baseline(BASELINE)
        self.revision = CurriculumRevision.objects.get(pk=imported.revision_id)
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            email="map-reader@example.test", password="safe-test-password"
        )

    def test_map_requires_authentication_and_preserves_layout_and_provenance(self) -> None:
        self.assertEqual(self.client.get("/api/v1/curriculum-map").status_code, 401)
        self.client.force_login(self.user)
        response = self.client.get("/api/v1/curriculum-map")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["revision"]["status"], "DRAFT")
        self.assertFalse(payload["revision"]["normative"])
        self.assertFalse(payload["layout_policy"]["normative"])
        self.assertEqual(
            {item["id"] for item in payload["layout_policy"]["available_layouts"]},
            {"dependency-depth", "suggested-path", "user-scenario", "component-lanes"},
        )
        self.assertEqual(len(payload["components"]), 3)
        self.assertEqual(len(payload["groups"]), 12)
        self.assertEqual(len(payload["courses"]), 102)
        self.assertIn("CURRICULUM_REVISION_NOT_PUBLISHED", payload["warnings"])
        self.assertIn("LAYOUTS_ARE_NOT_NORMATIVE", payload["warnings"])
        self.assertIsNotNone(response.headers.get("ETag"))
        self.assertIsNone(payload["offering_context"]["term_code"])
        self.assertTrue(all(item["offering_state"] == "UNKNOWN" for item in payload["courses"]))

        course = next(item for item in payload["courses"] if item["code"] == "2016360")
        self.assertGreaterEqual(course["dependency_depth"] or 0, 1)
        self.assertIn("2016379", course["dependencies"])
        self.assertTrue(course["source_evidence"])
        self.assertTrue(course["requirements"])
        self.assertIn("ast", course["requirements"][0])

    def test_map_exposes_selected_offering_and_private_personal_state(self) -> None:
        institution = self.revision.plan.program.faculty.campus.institution
        campus = self.revision.plan.program.faculty.campus
        term = AcademicTerm.objects.create(
            institution=institution,
            campus=campus,
            code="2026-1",
            starts_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            ends_at=datetime.datetime(2026, 6, 30, tzinfo=datetime.UTC),
        )
        version = CourseVersion.objects.get(course__institution=institution, course__code="2015168")
        CourseOffering.objects.create(
            course_version=version,
            term=term,
            status=OfferingStatus.PUBLISHED.value,
        )
        user = get_user_model().objects.create_user(
            email="map-student@example.test", password="safe-test-password"
        )
        student = StudentProfile.objects.create(
            user=user,
            institution=institution,
            student_number="MAP-1",
            legacy_display_name="Map Student",
        )
        enrollment = ProgramEnrollment.objects.create(
            student=student,
            program=self.revision.plan.program,
            plan=self.revision.plan,
            revision_basis=self.revision,
            admission_term=term,
        )
        CourseAttempt.objects.create(
            enrollment=enrollment,
            course_version=version,
            term=term,
            attempt_number=1,
            status=AttemptStatus.PASSED.value,
            grade="4.5",
            credits_earned=4,
            origin=AttemptOrigin.MANUAL.value,
            entered_by=user,
        )
        self.assertTrue(
            self.client.login(email="map-student@example.test", password="safe-test-password")
        )

        response = self.client.get("/api/v1/curriculum-map?term_code=2026-1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["personal"]["available"])
        self.assertEqual(payload["personal"]["enrollment_id"], str(enrollment.pk))
        course = next(item for item in payload["courses"] if item["code"] == "2015168")
        self.assertEqual(course["personal_status"], "PASSED")
        self.assertEqual(course["offering_state"], "AVAILABLE")
        self.assertEqual(course["offerings"][0]["term_code"], "2026-1")

    def test_explicit_enrollment_cannot_cross_student_boundary(self) -> None:
        institution = self.revision.plan.program.faculty.campus.institution
        campus = self.revision.plan.program.faculty.campus
        term = AcademicTerm.objects.create(
            institution=institution,
            campus=campus,
            code="2026-2",
            starts_at=datetime.datetime(2026, 7, 1, tzinfo=datetime.UTC),
            ends_at=datetime.datetime(2026, 12, 20, tzinfo=datetime.UTC),
        )
        owner = get_user_model().objects.create_user(
            email="map-owner@example.test", password="safe-test-password"
        )
        other = get_user_model().objects.create_user(
            email="map-other@example.test", password="safe-test-password"
        )
        student = StudentProfile.objects.create(user=owner, institution=institution)
        enrollment = ProgramEnrollment.objects.create(
            student=student,
            program=self.revision.plan.program,
            plan=self.revision.plan,
            revision_basis=self.revision,
            admission_term=term,
        )
        self.assertTrue(self.client.login(email=other.email, password="safe-test-password"))

        response = self.client.get(f"/api/v1/curriculum-map?enrollment_id={enrollment.pk}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "MAP_FORBIDDEN")
