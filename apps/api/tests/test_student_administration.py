from __future__ import annotations

import datetime
import json

from django.conf import settings
from django.test import Client, TransactionTestCase, override_settings

from domain.enums import RevisionStatus, UserRole
from modules.curriculum.models import CurriculumPlan, CurriculumRevision
from modules.identity.application.rate_limit import consume_rate_limit
from modules.identity.models import (
    AuditEvent,
    IdentityDataStatus,
    PersonProfile,
    RoleAssignment,
    User,
)
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
                    "first_name": "Nueva",
                    "middle_names": "María",
                    "first_surname": "Estudiante",
                    "second_surname": "Ejemplo",
                    "preferred_name": "Nue",
                    "birth_date": "2004-08-19",
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
        person = PersonProfile.objects.get(user=user)
        enrollment = ProgramEnrollment.objects.get(student=student)
        self.assertEqual(response.json()["id"], str(enrollment.pk))
        self.assertEqual(response.json()["display_name"], "Nueva María Estudiante Ejemplo")
        self.assertNotIn("age", response.json())
        self.assertEqual(person.age_on(datetime.date(2026, 8, 18)), 21)
        self.assertEqual(person.first_name, "Nueva")
        self.assertEqual(person.middle_names, "María")
        self.assertEqual(person.first_surname, "Estudiante")
        self.assertEqual(person.data_status, IdentityDataStatus.CONFIRMED)
        self.assertEqual(student.legacy_display_name, "")
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
        me = self.client.get("/api/v1/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertNotIn("birth_date", me.content.decode())
        self.client.force_login(self.admin)
        event = AuditEvent.objects.get(
            action="STUDENT_ENROLLMENT_CREATED", object_id=str(enrollment.pk)
        )
        self.assertNotIn("birth", json.dumps(event.metadata))
        by_surname = self.client.get("/api/v1/admin/students/enrollments", {"search": "Ejemplo"})
        self.assertEqual(by_surname.status_code, 200)
        self.assertEqual(by_surname.json()["total"], 1)

        duplicate = self.client.post(
            "/api/v1/admin/students/enrollments",
            json.dumps(
                {
                    "email": "new.student@example.test",
                    "temporary_password": "SafeEnrollment!2026-Xp4",
                    "first_name": "Cuenta",
                    "first_surname": "Duplicada",
                    "birth_date": "2004-08-19",
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

    def test_legacy_create_contract_preserves_name_without_guessing_identity(self) -> None:
        response = self.client.post(
            "/api/v1/admin/students/enrollments",
            json.dumps(
                {
                    "email": "legacy.contract@example.test",
                    "temporary_password": "SafeEnrollment!2026-Xp4",
                    "display_name": "María del Pilar De la O",
                    "student_number": "S-LEGACY-001",
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
        self.assertEqual(response.status_code, 201, response.content)
        enrollment = ProgramEnrollment.objects.get(pk=response.json()["id"])
        self.assertEqual(enrollment.student.legacy_display_name, "María del Pilar De la O")
        self.assertEqual(enrollment.student.user.person_profile.first_name, "")
        self.assertEqual(
            enrollment.student.user.person_profile.data_status,
            IdentityDataStatus.LEGACY_UNSTRUCTURED,
        )
        self.assertEqual(enrollment.status, "NEEDS_REVIEW")

    @override_settings(PRIVILEGED_MFA_REQUIRED=True)  # type: ignore[untyped-decorator]
    def test_student_creation_requires_privileged_step_up(self) -> None:
        payload = {
            "email": "mfa.create@example.test",
            "temporary_password": "SafeEnrollment!2026-Xp4",
            "first_name": "Alta",
            "first_surname": "Verificada",
            "birth_date": "2004-08-19",
            "student_number": "S-MFA-001",
            "institution_id": str(self.data["institution"].pk),
            "program_id": str(self.data["program"].pk),
            "plan_id": str(self.data["plan"].pk),
            "revision_basis_id": str(self.data["revision"].pk),
            "admission_term_id": str(self.data["term"].pk),
        }
        denied = self.client.post(
            "/api/v1/admin/students/enrollments",
            json.dumps(payload),
            content_type="application/json",
            **self.csrf_headers(),
        )
        self.assertEqual(denied.status_code, 403)
        self.assertFalse(User.objects.filter(email=payload["email"]).exists())

        session = self.client.session
        session[settings.PRIVILEGED_MFA_SESSION_KEY] = "verified-by-test-idp"
        session.save()
        allowed = self.client.post(
            "/api/v1/admin/students/enrollments",
            json.dumps(payload),
            content_type="application/json",
            **self.csrf_headers(),
        )
        self.assertEqual(allowed.status_code, 201, allowed.content)
        self.assertNotIn("birth_date", allowed.json())
        self.assertTrue(User.objects.filter(email=payload["email"]).exists())

    def test_draft_revision_input_cannot_become_an_unverified_assignment(self) -> None:
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
                    "first_name": "Draft",
                    "first_surname": "Student",
                    "birth_date": "2004-08-19",
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

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["status"], "NEEDS_REVIEW")
        self.assertIsNone(response.json()["plan_id"])
        self.assertIsNone(response.json()["revision_basis_id"])
        self.assertTrue(User.objects.filter(email="draft.student@example.test").exists())

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
                    "first_name": "Fuera",
                    "first_surname": "Alcance",
                    "birth_date": "2004-08-19",
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
                    "first_name": "Ingreso",
                    "first_surname": "Histórico",
                    "birth_date": "2004-08-19",
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

        resolved = self.client.patch(
            f"/api/v1/admin/students/enrollments/{response.json()['id']}/revision",
            json.dumps(
                {
                    "revision_basis_id": str(self.data["revision"].pk),
                    "rationale": "Confirmación institucional de la revisión histórica aplicable.",
                }
            ),
            content_type="application/json",
            HTTP_IF_MATCH=f'"{response.json()["version"]}"',
            **self.csrf_headers(),
        )
        self.assertEqual(resolved.status_code, 422, resolved.content)
        self.assertEqual(resolved.json()["code"], "STUDENT_ADMIN_ASSIGNMENT_NEEDS_REVIEW")
        enrollment = ProgramEnrollment.objects.get(pk=response.json()["id"])
        self.assertEqual(enrollment.status, "NEEDS_REVIEW")
        self.assertIsNone(enrollment.plan_id)
        self.assertFalse(
            AuditEvent.objects.filter(
                action="STUDENT_ENROLLMENT_REVISION_CONFIRMED",
                object_id=str(response.json()["id"]),
            ).exists()
        )

    def test_admin_rectifies_structured_identity_with_version_and_redacted_audit(self) -> None:
        listed = self.client.get("/api/v1/admin/students/enrollments")
        item = next(
            value
            for value in listed.json()["items"]
            if value["id"] == str(self.data["enrollment"].pk)
        )
        self.assertNotIn("birth_date", item)
        detail_response = self.client.get(
            f"/api/v1/admin/students/enrollments/{item['id']}/identity"
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.headers["Cache-Control"], "private, no-store")
        detail = detail_response.json()
        payload = {
            "first_name": "Ana",
            "middle_names": "María",
            "first_surname": "López",
            "second_surname": "Ruiz",
            "preferred_name": "Ani",
            "birth_date": "2003-07-15",
            "rationale": "STUDENT_REQUEST_VERIFIED",
        }
        response = self.client.patch(
            f"/api/v1/admin/students/enrollments/{item['id']}/identity",
            json.dumps(payload),
            content_type="application/json",
            HTTP_IF_MATCH=f'"{detail["identity_version"]}"',
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["display_name"], "Ana María López Ruiz")
        self.assertEqual(response.json()["preferred_name"], "Ani")
        self.assertEqual(response.json()["birth_date"], "2003-07-15")
        event = AuditEvent.objects.get(action="PERSON_IDENTITY_RECTIFIED")
        self.assertIn("birth_date", event.metadata["changed_fields"])
        serialized_metadata = json.dumps(event.metadata, ensure_ascii=False)
        self.assertNotIn("2003-07-15", serialized_metadata)
        self.assertNotIn("Ana", serialized_metadata)
        self.assertEqual(event.metadata["reason_code"], "STUDENT_REQUEST_VERIFIED")
        self.assertNotIn("rationale", event.metadata)

        stale = self.client.patch(
            f"/api/v1/admin/students/enrollments/{item['id']}/identity",
            json.dumps(payload),
            content_type="application/json",
            HTTP_IF_MATCH=f'"{detail["identity_version"]}"',
            **self.csrf_headers(),
        )
        self.assertEqual(stale.status_code, 409)

    def test_identity_rectification_releases_only_the_identity_hold(self) -> None:
        enrollment = self.data["enrollment"]
        enrollment.status = "NEEDS_REVIEW"
        enrollment.review_reasons = ["IDENTITY_REVIEW"]
        enrollment.save(update_fields=("status", "review_reasons", "updated_at"))
        second_term = AcademicTerm.objects.create(
            institution=self.data["institution"],
            campus=self.data["campus"],
            code="2027-2-IDENTITY-HOLD",
            starts_at=self.data["term"].starts_at + datetime.timedelta(days=365),
            ends_at=self.data["term"].ends_at + datetime.timedelta(days=365),
        )
        second_enrollment = ProgramEnrollment.objects.create(
            student=enrollment.student,
            program=enrollment.program,
            plan=None,
            revision_basis=None,
            admission_term=second_term,
            status="NEEDS_REVIEW",
            review_reasons=["CURRICULUM_ASSIGNMENT", "IDENTITY_REVIEW"],
        )
        detail = self.client.get(
            f"/api/v1/admin/students/enrollments/{enrollment.pk}/identity"
        ).json()
        response = self.client.patch(
            f"/api/v1/admin/students/enrollments/{enrollment.pk}/identity",
            json.dumps(
                {
                    "first_name": "Ana",
                    "middle_names": "",
                    "first_surname": "López",
                    "second_surname": "",
                    "preferred_name": "",
                    "birth_date": "2003-07-15",
                    "rationale": "AUTHORIZED_SOURCE_VERIFIED",
                }
            ),
            content_type="application/json",
            HTTP_IF_MATCH=f'"{detail["identity_version"]}"',
            **self.csrf_headers(),
        )
        self.assertEqual(response.status_code, 200, response.content)
        enrollment.refresh_from_db()
        second_enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, "ACTIVE")
        self.assertEqual(enrollment.review_reasons, [])
        self.assertEqual(second_enrollment.status, "NEEDS_REVIEW")
        self.assertEqual(second_enrollment.review_reasons, ["CURRICULUM_ASSIGNMENT"])

    @override_settings(PRIVILEGED_MFA_REQUIRED=True)  # type: ignore[untyped-decorator]
    def test_private_identity_detail_requires_privileged_step_up(self) -> None:
        path = f"/api/v1/admin/students/enrollments/{self.data['enrollment'].pk}/identity"
        denied = self.client.get(path)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "STUDENT_ADMIN_STEP_UP_REQUIRED")

        session = self.client.session
        session[settings.PRIVILEGED_MFA_SESSION_KEY] = "verified-by-test-idp"
        session.save()
        allowed = self.client.get(path)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.headers["Cache-Control"], "private, no-store")

    @override_settings(SENSITIVE_IDENTITY_READ_RATE_LIMIT_PER_MINUTE=1)  # type: ignore[untyped-decorator]
    def test_private_identity_detail_has_a_read_rate_limit(self) -> None:
        self.assertTrue(
            consume_rate_limit(
                key=f"user:{self.admin.pk}",
                action="identity:admin-detail-read",
                limit=1,
            )
        )
        response = self.client.get(
            f"/api/v1/admin/students/enrollments/{self.data['enrollment'].pk}/identity"
        )
        self.assertEqual(response.status_code, 429)
        self.assertFalse(AuditEvent.objects.filter(action="PERSON_IDENTITY_VIEWED").exists())

    @override_settings(PRIVILEGED_MFA_REQUIRED=True)  # type: ignore[untyped-decorator]
    def test_identity_rectification_rechecks_privileged_step_up(self) -> None:
        person = self.data["user"].person_profile
        path = f"/api/v1/admin/students/enrollments/{self.data['enrollment'].pk}/identity"
        payload = {
            "first_name": "Identidad",
            "first_surname": "Verificada",
            "birth_date": "2000-01-01",
            "rationale": "AUTHORIZED_SOURCE_VERIFIED",
        }
        denied = self.client.patch(
            path,
            json.dumps(payload),
            content_type="application/json",
            HTTP_IF_MATCH=f'"{person.updated_at.isoformat()}"',
            **self.csrf_headers(),
        )
        self.assertEqual(denied.status_code, 403)
        person.refresh_from_db()
        self.assertEqual(person.first_name, "Test")

        session = self.client.session
        session[settings.PRIVILEGED_MFA_SESSION_KEY] = "verified-by-test-idp"
        session.save()
        allowed = self.client.patch(
            path,
            json.dumps(payload),
            content_type="application/json",
            HTTP_IF_MATCH=f'"{person.updated_at.isoformat()}"',
            **self.csrf_headers(),
        )
        self.assertEqual(allowed.status_code, 200, allowed.content)
        person.refresh_from_db()
        self.assertEqual(person.first_name, "Identidad")

    def test_enrollment_list_reports_total_pages_and_searches_beyond_first_page(self) -> None:
        for index in range(55):
            user = User.objects.create(email=f"paged-{index:03d}@example.test")
            profile = StudentProfile.objects.create(
                user=user,
                institution=self.data["institution"],
                student_number=f"PAGE-{index:03d}",
                legacy_display_name=f"Paged Student {index:03d}",
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
