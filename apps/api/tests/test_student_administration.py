from __future__ import annotations

import datetime
import json

from django.test import Client, TransactionTestCase

from domain.enums import RevisionStatus, UserRole
from modules.curriculum.models import CurriculumPlan, CurriculumRevision
from modules.identity.models import AuditEvent, RoleAssignment, User
from modules.institutions.models import Program
from modules.offerings.models import AcademicTerm
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
        self.assertIsNotNone(user.email_verified_at)
        self.client.logout()
        login = self.client.post(
            "/api/v1/auth/login",
            json.dumps(
                {
                    "email": "new.student@example.test",
                    "password": "SafeEnrollment!2026-Xp4",
                }
            ),
            content_type="application/json",
            **self.csrf_headers(),
        )
        self.assertEqual(login.status_code, 200, login.content)
        self.assertTrue(login.json()["user"]["must_change_password"])
        blocked = self.client.get("/api/v1/academic-overview")
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json()["code"], "INITIAL_PASSWORD_CHANGE_REQUIRED")
        changed = self.client.post(
            "/api/v1/auth/password/change",
            json.dumps(
                {
                    "current_password": "SafeEnrollment!2026-Xp4",
                    "new_password": "PrivateStudent!2026-Zp8",
                }
            ),
            content_type="application/json",
            **self.csrf_headers(),
        )
        self.assertEqual(changed.status_code, 200, changed.content)
        user.refresh_from_db()
        self.assertFalse(user.must_change_password)
        self.assertIsNone(user.initial_password_expires_at)
        self.assertTrue(user.check_password("PrivateStudent!2026-Zp8"))
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 200)
        self.client.force_login(self.admin)
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

    def test_program_scoped_admin_cannot_list_or_create_students_in_sibling_program(self) -> None:
        RoleAssignment.objects.filter(user=self.admin, role=UserRole.ADMIN.value).delete()
        RoleAssignment.objects.create(
            user=self.admin,
            role=UserRole.ADMIN.value,
            institution=self.data["institution"],
            program=self.data["program"],
        )
        sibling_program = Program.objects.create(
            faculty=self.data["faculty"],
            code="MATH-SIBLING",
            name="Matemáticas",
            degree_name="Matemático",
        )
        sibling_plan = CurriculumPlan.objects.create(
            program=sibling_program, code="MATH-PLAN", title="Plan Matemáticas"
        )
        sibling_revision = CurriculumRevision.objects.create(
            plan=sibling_plan,
            revision_code="MATH-2023",
            effective_from=datetime.date(2023, 1, 1),
            status=RevisionStatus.PUBLISHED.value,
        )
        sibling_user = User.objects.create(email="sibling.student@example.test")
        sibling_profile = StudentProfile.objects.create(
            user=sibling_user,
            institution=self.data["institution"],
            student_number="S-SIBLING",
        )
        ProgramEnrollment.objects.create(
            student=sibling_profile,
            program=sibling_program,
            plan=sibling_plan,
            revision_basis=sibling_revision,
            admission_term=self.data["term"],
        )

        catalog = self.client.get("/api/v1/admin/students/catalog")
        listed = self.client.get("/api/v1/admin/students/enrollments", {"search": "S-SIBLING"})
        self.assertEqual(
            {item["id"] for item in catalog.json()["programs"]},
            {str(self.data["program"].pk)},
        )
        self.assertEqual(listed.json()["total"], 0)

        forbidden = self.client.post(
            "/api/v1/admin/students/enrollments",
            json.dumps(
                {
                    "email": "blocked.sibling@example.test",
                    "temporary_password": "SafeEnrollment!2026-Xp4",
                    "display_name": "Fuera de alcance",
                    "student_number": "S-BLOCKED",
                    "institution_id": str(self.data["institution"].pk),
                    "program_id": str(sibling_program.pk),
                    "plan_id": str(sibling_plan.pk),
                    "revision_basis_id": str(sibling_revision.pk),
                    "admission_term_id": str(self.data["term"].pk),
                }
            ),
            content_type="application/json",
            **self.csrf_headers(),
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertFalse(User.objects.filter(email="blocked.sibling@example.test").exists())

    def test_revision_outside_admission_date_creates_needs_review_enrollment(self) -> None:
        historical_term = AcademicTerm.objects.create(
            institution=self.data["institution"],
            campus=self.data["campus"],
            code="2022-1-HISTORICAL",
            starts_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.UTC),
            ends_at=datetime.datetime(2022, 6, 30, tzinfo=datetime.UTC),
        )
        response = self.client.post(
            "/api/v1/admin/students/enrollments",
            json.dumps(
                {
                    "email": "historical.student@example.test",
                    "temporary_password": "SafeEnrollment!2026-Xp4",
                    "display_name": "Ingreso histórico",
                    "student_number": "S-HISTORICAL",
                    "institution_id": str(self.data["institution"].pk),
                    "program_id": str(self.data["program"].pk),
                    "plan_id": str(self.data["plan"].pk),
                    "revision_basis_id": str(self.data["revision"].pk),
                    "admission_term_id": str(historical_term.pk),
                }
            ),
            content_type="application/json",
            **self.csrf_headers(),
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["status"], "NEEDS_REVIEW")

    def test_enrollment_list_reports_total_pages_and_searches_beyond_first_page(self) -> None:
        for index in range(55):
            user = User.objects.create(email=f"paged-{index:03d}@example.test")
            profile = StudentProfile.objects.create(
                user=user,
                institution=self.data["institution"],
                student_number=f"PAGE-{index:03d}",
                display_name=f"Paged Student {index:03d}",
            )
            ProgramEnrollment.objects.create(
                student=profile,
                program=self.data["program"],
                plan=self.data["plan"],
                revision_basis=self.data["revision"],
                admission_term=self.data["term"],
            )

        first = self.client.get("/api/v1/admin/students/enrollments", {"limit": 20, "offset": 0})
        second = self.client.get("/api/v1/admin/students/enrollments", {"limit": 20, "offset": 20})
        searched = self.client.get("/api/v1/admin/students/enrollments", {"search": "PAGE-054"})

        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(first.json()["total"], 56)
        self.assertEqual(first.json()["next_offset"], 20)
        self.assertEqual(second.json()["previous_offset"], 0)
        self.assertEqual(searched.json()["total"], 1)
        self.assertEqual(searched.json()["items"][0]["student_number"], "PAGE-054")
