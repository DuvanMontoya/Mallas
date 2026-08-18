from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from modules.audit.application.services import run_degree_audit
from modules.identity.models import RoleAssignment
from modules.student_records.models import ProgramEnrollment, StudentProfile
from tests.factories import foundation


class AnalyticsApiTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.data = foundation(suffix="-analytics")
        self.revision = self.data["revision"]
        self.revision.total_required_credits = 4
        self.revision.status = "PUBLISHED"
        self.revision.published_at = timezone.now()
        self.revision.content_hash = "published-analytics-revision"
        self.revision.save(
            update_fields=["status", "published_at", "content_hash", "total_required_credits"]
        )
        run_degree_audit(self.data["enrollment"].pk)

    def test_definitions_are_visible_without_private_records(self) -> None:
        response = self.client.get("/api/v1/analytics/definitions")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["schema_version"], "1.0")
        self.assertTrue(
            any(item["key"] == "credits.applied" for item in response.json()["definitions"])
        )

    def test_student_analytics_uses_persisted_snapshot_and_minimizes_identity(self) -> None:
        self.client.force_login(self.data["user"])

        response = self.client.get("/api/v1/analytics/student")

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["data_state"], "PERSISTED_PUBLISHED_AUDIT")
        self.assertEqual(payload["metrics"]["credits"]["applied"], 0)
        self.assertEqual(len(payload["metrics"]["trend"]), 1)
        self.assertNotIn(self.data["user"].email, response.content.decode())
        self.assertNotIn(self.data["student"].student_number, response.content.decode())

    def test_needs_review_returns_a_complete_safe_analytics_payload(self) -> None:
        self.data["enrollment"].status = "NEEDS_REVIEW"
        self.data["enrollment"].save(update_fields=["status", "updated_at"])
        self.client.force_login(self.data["user"])

        response = self.client.get("/api/v1/analytics/student")

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["data_state"], "ENROLLMENT_NEEDS_REVIEW")
        self.assertIsNone(payload["metrics"]["credits"])
        self.assertTrue(payload["definitions"])
        self.assertTrue(payload["warnings"])

    def test_student_cannot_read_institutional_analytics_without_role(self) -> None:
        self.client.force_login(self.data["user"])

        response = self.client.get(
            f"/api/v1/analytics/institutional?institution_id={self.data['institution'].pk}"
        )

        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(response.json()["code"], "ANALYTICS_FORBIDDEN")

    @override_settings(ANALYTICS_MIN_CELL_SIZE=2)  # type: ignore[untyped-decorator]
    def test_institutional_analytics_is_role_gated_aggregated_and_exportable(self) -> None:
        analyst = get_user_model().objects.create_user(
            email="analyst-analytics@example.test", password="safe-test-password"
        )
        RoleAssignment.objects.create(
            user=analyst,
            role="ANALYST",
            institution=self.data["institution"],
            rationale="Analytics test scope",
        )
        second_user = get_user_model().objects.create_user(
            email="second-analytics@example.test", password="safe-test-password"
        )
        second_student = StudentProfile.objects.create(
            user=second_user,
            institution=self.data["institution"],
            student_number="S-analytics-2",
            display_name="Second Student",
        )
        second_enrollment = ProgramEnrollment.objects.create(
            student=second_student,
            program=self.data["program"],
            plan=self.data["plan"],
            revision_basis=self.revision,
            admission_term=self.data["term"],
        )
        run_degree_audit(second_enrollment.pk)
        self.client.force_login(analyst)

        response = self.client.get(
            f"/api/v1/analytics/institutional?institution_id={self.data['institution'].pk}"
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["data_state"], "AGGREGATED")
        self.assertEqual(payload["population"]["enrollment_count"], 2)
        self.assertFalse(payload["privacy"]["contains_student_identifiers"])
        self.assertNotIn("analyst-analytics@example.test", response.content.decode())
        self.assertNotIn("S-analytics-2", response.content.decode())

        csv_response = self.client.get(
            f"/api/v1/analytics/institutional/export?institution_id={self.data['institution'].pk}&format=csv"
        )
        self.assertEqual(csv_response.status_code, 200, csv_response.content)
        self.assertEqual(csv_response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment;", csv_response["Content-Disposition"])
        self.assertNotIn("S-analytics-2", csv_response.content.decode())
