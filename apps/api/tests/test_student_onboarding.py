from __future__ import annotations

import json
from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from modules.offerings.models import AcademicTerm
from modules.student_records.models import ProgramEnrollment, StudentOnboarding
from tests.factories import foundation


class StudentOnboardingApiTests(TestCase):
    def setUp(self) -> None:
        self.data = foundation(suffix="-onboarding")
        self.state = StudentOnboarding.objects.create(enrollment=self.data["enrollment"])
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.data["user"])

    def csrf_headers(self) -> dict[str, str]:
        csrf = self.client.get("/api/v1/auth/csrf").json()["csrf_token"]
        return {"HTTP_X_CSRFTOKEN": csrf}

    def test_onboarding_is_reanudable_and_updates_session_requirement(self) -> None:
        me = self.client.get("/api/v1/auth/me")
        self.assertTrue(me.json()["onboarding_required"])
        initial = self.client.get("/api/v1/onboarding")
        self.assertEqual(initial.status_code, 200, initial.content)
        self.assertEqual(initial.headers["Cache-Control"], "private, no-store")
        self.assertEqual(initial.json()["program_code"], self.data["program"].code)
        self.assertEqual(initial.json()["plan_code"], self.data["plan"].code)

        payload = {
            "identity_confirmed": True,
            "history_step_status": "SKIPPED",
            "current_term_id": str(self.data["term"].pk),
            "planning_load_target": 16,
            "tour_status": "SKIPPED",
            "complete": False,
        }
        missing_precondition = self.client.patch(
            "/api/v1/onboarding",
            json.dumps(payload),
            content_type="application/json",
            **self.csrf_headers(),
        )
        self.assertEqual(missing_precondition.status_code, 428)

        saved = self.client.patch(
            "/api/v1/onboarding",
            json.dumps(payload),
            content_type="application/json",
            HTTP_IF_MATCH=f'"{initial.json()["version"]}"',
            **self.csrf_headers(),
        )
        self.assertEqual(saved.status_code, 200, saved.content)
        self.assertFalse(saved.json()["completed"])
        self.assertEqual(saved.json()["planning_load_target"], 16)

        payload["complete"] = True
        completed = self.client.patch(
            "/api/v1/onboarding",
            json.dumps(payload),
            content_type="application/json",
            HTTP_IF_MATCH=f'"{saved.json()["version"]}"',
            **self.csrf_headers(),
        )
        self.assertEqual(completed.status_code, 200, completed.content)
        self.assertTrue(completed.json()["completed"])
        self.assertFalse(self.client.get("/api/v1/auth/me").json()["onboarding_required"])

    def test_pending_curriculum_is_shown_without_an_invented_plan(self) -> None:
        enrollment = self.data["enrollment"]
        enrollment.status = "NEEDS_REVIEW"
        enrollment.plan = None
        enrollment.revision_basis = None
        enrollment.review_reasons = ["CURRICULUM_ASSIGNMENT"]
        enrollment.save(
            update_fields=(
                "status",
                "plan",
                "revision_basis",
                "review_reasons",
                "updated_at",
            )
        )
        response = self.client.get("/api/v1/onboarding")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["enrollment_status"], "NEEDS_REVIEW")
        self.assertIsNone(response.json()["plan_code"])
        self.assertIsNone(response.json()["revision_code"])
        analytics = self.client.get("/api/v1/analytics/student")
        self.assertEqual(analytics.status_code, 200, analytics.content)
        self.assertEqual(analytics.json()["data_state"], "ENROLLMENT_NEEDS_REVIEW")
        self.assertIsNone(analytics.json()["plan_code"])
        public_map = self.client.get(
            "/api/v1/curriculum-map", {"plan_code": self.data["plan"].code}
        )
        self.assertEqual(public_map.status_code, 200, public_map.content)
        self.assertFalse(public_map.json()["personal"]["available"])
        self.assertEqual(public_map.json()["personal"]["state"], "NEEDS_REVIEW")

    def test_incomplete_second_enrollment_is_selected_after_first_is_complete(self) -> None:
        self.state.completed_at = timezone.now()
        self.state.save(update_fields=("completed_at", "updated_at"))
        term = AcademicTerm.objects.create(
            institution=self.data["institution"],
            campus=self.data["campus"],
            code="ONBOARDING-SECOND",
            starts_at=timezone.now() + timedelta(days=180),
            ends_at=timezone.now() + timedelta(days=300),
        )
        enrollment = ProgramEnrollment.objects.create(
            student=self.data["student"],
            program=self.data["program"],
            plan=self.data["plan"],
            revision_basis=self.data["revision"],
            admission_term=term,
            status="ACTIVE",
        )
        StudentOnboarding.objects.create(enrollment=enrollment)

        self.assertTrue(self.client.get("/api/v1/auth/me").json()["onboarding_required"])
        response = self.client.get("/api/v1/onboarding")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["enrollment_id"], str(enrollment.pk))
        self.assertFalse(response.json()["completed"])
