from __future__ import annotations

import datetime
import json

from django.test import Client, TransactionTestCase

from domain.enums import RevisionStatus, UserRole
from modules.curriculum.models import CurriculumRevision
from modules.identity.models import AuditEvent, RoleAssignment, User
from modules.student_records.models import ProgramEnrollment, StudentProfile
from tests.factories import foundation


class StudentAdministrationApiTests(TransactionTestCase):
    def setUp(self) -> None:
        self.data = foundation(suffix="-student-admin")
        self.data["revision"].status = RevisionStatus.PUBLISHED.value
        self.data["revision"].save(update_fields=["status", "updated_at"])
        self.admin = self.data["user"]
        RoleAssignment.objects.create(
            user=self.admin,
            role=UserRole.ADMIN.value,
            institution=self.data["institution"],
        )
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.admin)

    def csrf_headers(self) -> dict[str, str]:
        response = self.client.get("/api/v1/auth/csrf")
        self.assertEqual(response.status_code, 200)
        return {"HTTP_X_CSRFTOKEN": response.json()["csrf_token"]}

    def test_admin_creates_account_profile_enrollment_and_student_role_atomically(self) -> None:
        catalog = self.client.get("/api/v1/admin/students/catalog")
        self.assertEqual(catalog.status_code, 200, catalog.content)
        self.assertEqual(catalog.json()["institutions"][0]["id"], str(self.data["institution"].pk))
        self.assertEqual(
            [item["id"] for item in catalog.json()["revisions"]],
            [str(self.data["revision"].pk)],
        )

        response = self.client.post(
            "/api/v1/admin/students/enrollments",
            json.dumps(
                {
                    "email": "new.student@example.test",
                    "temporary_password": "SafeEnrollment!2026-Xp4",
                    "display_name": "Nueva Estudiante",
                    "student_number": "S-NEW-001",
                    "institution_id": str(self.data["institution"].pk),
                    "program_id": str(self.data["program"].pk),
                    "plan_id": str(self.data["plan"].pk),
                    "revision_basis_id": str(self.data["revision"].pk),
                    "admission_term_id": str(self.data["term"].pk),
                    "cohort_code": "2026-1",
                }
            ),
            content_type="application/json",
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, 201, response.content)
        user = User.objects.get(email="new.student@example.test")
        self.assertTrue(user.check_password("SafeEnrollment!2026-Xp4"))
        student = StudentProfile.objects.get(user=user)
        enrollment = ProgramEnrollment.objects.get(student=student)
        self.assertEqual(response.json()["id"], str(enrollment.pk))
        self.assertTrue(
            RoleAssignment.objects.filter(
                user=user,
                role=UserRole.STUDENT.value,
                institution=self.data["institution"],
                program=self.data["program"],
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action="STUDENT_ENROLLMENT_CREATED", object_id=str(enrollment.pk)
            ).exists()
        )

        duplicate = self.client.post(
            "/api/v1/admin/students/enrollments",
            json.dumps(
                {
                    "email": "new.student@example.test",
                    "temporary_password": "SafeEnrollment!2026-Xp4",
                    "display_name": "Duplicada",
                    "student_number": "S-NEW-002",
                    "institution_id": str(self.data["institution"].pk),
                    "program_id": str(self.data["program"].pk),
                    "plan_id": str(self.data["plan"].pk),
                    "revision_basis_id": str(self.data["revision"].pk),
                    "admission_term_id": str(self.data["term"].pk),
                }
            ),
            content_type="application/json",
            **self.csrf_headers(),
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(User.objects.filter(email="new.student@example.test").count(), 1)

    def test_draft_revision_is_not_offered_or_accepted_for_a_new_enrollment(self) -> None:
        draft = CurriculumRevision.objects.create(
            plan=self.data["plan"],
            revision_code="future-draft",
            effective_from=datetime.date(2027, 1, 1),
            total_required_credits=141,
        )
        catalog = self.client.get("/api/v1/admin/students/catalog")
        self.assertNotIn(str(draft.pk), {item["id"] for item in catalog.json()["revisions"]})

        response = self.client.post(
            "/api/v1/admin/students/enrollments",
            json.dumps(
                {
                    "email": "draft.student@example.test",
                    "temporary_password": "SafeEnrollment!2026-Xp4",
                    "display_name": "Draft Student",
                    "student_number": "S-DRAFT-001",
                    "institution_id": str(self.data["institution"].pk),
                    "program_id": str(self.data["program"].pk),
                    "plan_id": str(self.data["plan"].pk),
                    "revision_basis_id": str(draft.pk),
                    "admission_term_id": str(self.data["term"].pk),
                }
            ),
            content_type="application/json",
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "STUDENT_ADMIN_REVISION_NOT_PUBLISHED")
        self.assertFalse(User.objects.filter(email="draft.student@example.test").exists())

    def test_non_admin_cannot_read_or_write_native_student_administration(self) -> None:
        other = foundation(suffix="-student-admin-forbidden")
        self.client.force_login(other["user"])

        catalog = self.client.get("/api/v1/admin/students/catalog")
        enrollments = self.client.get("/api/v1/admin/students/enrollments")

        self.assertEqual(catalog.status_code, 403)
        self.assertEqual(enrollments.status_code, 403)
        self.assertEqual(catalog.json()["code"], "STUDENT_ADMIN_FORBIDDEN")
