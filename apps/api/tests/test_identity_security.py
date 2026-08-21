from __future__ import annotations

import os
import re
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.db import DatabaseError, connection, transaction
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from domain.enums import UserRole
from domain.errors import AuditEventImmutableError, PublishedRevisionImmutableError
from modules.curriculum.application.services import (
    CurriculumRevisionService,
    RevisionTransitionError,
)
from modules.curriculum.models import CurriculumRevision
from modules.identity.api import email_verification_token_generator
from modules.identity.application.audit import record_audit_event
from modules.identity.application.authorization import (
    can_edit_revision,
    can_edit_student_history,
    can_publish_revision,
    can_view_student,
)
from modules.identity.application.rate_limit import consume_rate_limit
from modules.identity.models import (
    AuditEvent,
    IdentityVerificationMethod,
    PersonProfile,
    RoleAssignment,
    User,
)
from modules.student_records.models import StudentAdvisorAssignment
from tests.factories import foundation


class LocalAdminBootstrapCommandTests(TestCase):
    def credentials_file(self) -> Path:
        return settings.PROJECT_ROOT / "var" / f"test-local-admin-{uuid4().hex}.txt"

    def test_creates_local_superuser_and_private_credentials_file(self) -> None:
        credentials_file = self.credentials_file()
        try:
            with override_settings(DEBUG=True):
                call_command("bootstrap_local_admin", credentials_file=str(credentials_file))

            user = User.objects.get(email="admin@localhost")
            content = credentials_file.read_text(encoding="utf-8")

            self.assertTrue(user.is_superuser)
            self.assertTrue(user.is_staff)
            self.assertTrue(CurriculumRevision.objects.filter(plan__code="2514").exists())
            self.assertIn("EMAIL=admin@localhost", content)
            self.assertEqual(os.stat(credentials_file).st_mode & 0o777, 0o600)
            password = next(
                line.removeprefix("PASSWORD=")
                for line in content.splitlines()
                if line.startswith("PASSWORD=")
            )
            self.assertTrue(user.check_password(password))
        finally:
            credentials_file.unlink(missing_ok=True)

    def test_existing_account_is_idempotent_and_password_is_preserved(self) -> None:
        user = User.objects.create_superuser(
            email="admin@localhost", password="LocalAdminPassword!2026"
        )
        credentials_file = self.credentials_file()
        try:
            with override_settings(DEBUG=True):
                call_command("bootstrap_local_admin", credentials_file=str(credentials_file))

            user.refresh_from_db()
            self.assertTrue(user.check_password("LocalAdminPassword!2026"))
            self.assertFalse(credentials_file.exists())
            self.assertTrue(CurriculumRevision.objects.filter(plan__code="2514").exists())
        finally:
            credentials_file.unlink(missing_ok=True)

    def test_refuses_to_run_outside_debug_mode(self) -> None:
        with override_settings(DEBUG=False), self.assertRaises(CommandError):
            call_command("bootstrap_local_admin", credentials_file=str(self.credentials_file()))


class IdentityApiTests(TestCase):
    def setUp(self) -> None:
        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            email="student@example.test",
            password="correct horse battery staple",
        )
        self.user.email_verified_at = timezone.now()
        self.user.save(update_fields=["email_verified_at"])

    def csrf_headers(self) -> dict[str, str]:
        response = self.client.get("/api/v1/auth/csrf")
        self.assertEqual(response.status_code, 200)
        return {"HTTP_X_CSRFTOKEN": response.json()["csrf_token"]}

    def test_csrf_login_session_me_and_logout(self) -> None:
        denied = self.client.post(
            "/api/v1/auth/login",
            {"email": self.user.email, "password": "correct horse battery staple"},
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)

        headers = self.csrf_headers()
        logged_in = self.client.post(
            "/api/v1/auth/login",
            {"email": self.user.email, "password": "correct horse battery staple"},
            content_type="application/json",
            **headers,
        )
        self.assertEqual(logged_in.status_code, 200)
        self.assertEqual(logged_in.json()["user"]["email"], self.user.email)
        self.assertTrue(logged_in.cookies["curriculum_session"].get("httponly"))

        me = self.client.get("/api/v1/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["id"], self.user.pk)

        headers = self.csrf_headers()
        logged_out = self.client.post("/api/v1/auth/logout", {}, **headers)
        self.assertEqual(logged_out.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)
        self.assertTrue(
            AuditEvent.objects.filter(action="AUTH_LOGIN_SUCCEEDED", actor=self.user).exists()
        )
        self.assertTrue(AuditEvent.objects.filter(action="AUTH_LOGOUT", actor=self.user).exists())

    def test_person_can_create_rectify_and_export_own_identity(self) -> None:
        self.client.force_login(self.user)
        empty = self.client.get("/api/v1/auth/profile")
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.headers["Cache-Control"], "private, no-store")
        self.assertEqual(empty.json()["version"], "missing")
        self.assertNotIn("birth_date", self.client.get("/api/v1/auth/me").json())

        updated = self.client.patch(
            "/api/v1/auth/profile",
            {
                "first_name": "  María ",
                "middle_names": "  Fernanda ",
                "first_surname": " De la Cruz ",
                "second_surname": " Gómez ",
                "preferred_name": "Mafe",
                "birth_date": "2003-08-19",
            },
            content_type="application/json",
            HTTP_IF_MATCH='"missing"',
            **self.csrf_headers(),
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.headers["Cache-Control"], "private, no-store")
        self.assertEqual(updated.json()["first_name"], "María")
        self.assertEqual(updated.json()["first_surname"], "De la Cruz")
        self.assertEqual(updated.json()["age"], PersonProfile.objects.get(user=self.user).age_on())

        export = self.client.get("/api/v1/auth/profile/export")
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.headers["Cache-Control"], "private, no-store")
        self.assertEqual(export.json()["schema_version"], "person-profile-export/1.0.0")
        self.assertEqual(export.json()["identity"]["birth_date"], "2003-08-19")
        audit = AuditEvent.objects.get(action="PERSON_IDENTITY_SELF_RECTIFIED")
        self.assertEqual(
            audit.metadata["changed_fields"],
            [
                "birth_date",
                "first_name",
                "first_surname",
                "middle_names",
                "preferred_name",
                "second_surname",
            ],
        )
        self.assertNotIn("María", str(audit.metadata))
        self.assertTrue(AuditEvent.objects.filter(action="PERSON_IDENTITY_EXPORTED").exists())

    def test_person_profile_update_requires_csrf_and_current_version(self) -> None:
        self.client.force_login(self.user)
        profile = PersonProfile.objects.create(
            user=self.user,
            first_name="Actual",
            first_surname="Persona",
            birth_date="2000-01-01",
            birth_date_purpose="ACADEMIC_ADMINISTRATION",
            data_status="CONFIRMED",
            verification_method=IdentityVerificationMethod.INSTITUTION_VERIFIED,
        )
        payload = {
            "first_name": "Cambio",
            "first_surname": "Persona",
            "birth_date": "2000-01-01",
        }
        denied = self.client.patch(
            "/api/v1/auth/profile",
            payload,
            content_type="application/json",
            HTTP_IF_MATCH=f'"{profile.updated_at.isoformat()}"',
        )
        self.assertEqual(denied.status_code, 403)
        stale = self.client.patch(
            "/api/v1/auth/profile",
            payload,
            content_type="application/json",
            HTTP_IF_MATCH='"stale"',
            **self.csrf_headers(),
        )
        self.assertEqual(stale.status_code, 409)
        profile.refresh_from_db()
        self.assertEqual(profile.first_name, "Actual")

        institutional = self.client.patch(
            "/api/v1/auth/profile",
            payload,
            content_type="application/json",
            HTTP_IF_MATCH=f'"{profile.updated_at.isoformat()}"',
            **self.csrf_headers(),
        )
        self.assertEqual(institutional.status_code, 409)
        profile.refresh_from_db()
        self.assertEqual(profile.first_name, "Actual")
        self.assertEqual(
            profile.verification_method,
            IdentityVerificationMethod.INSTITUTION_VERIFIED,
        )

    @override_settings(API_MUTATION_RATE_LIMIT_PER_MINUTE=1)  # type: ignore[untyped-decorator]
    def test_person_profile_update_uses_authenticated_mutation_rate_limit(self) -> None:
        self.client.force_login(self.user)
        self.assertTrue(
            consume_rate_limit(key=f"user:{self.user.pk}", action="api:mutation", limit=1)
        )
        response = self.client.patch(
            "/api/v1/auth/profile",
            {
                "first_name": "Ana",
                "first_surname": "Persona",
                "birth_date": "2000-01-01",
            },
            content_type="application/json",
            HTTP_IF_MATCH='"missing"',
            **self.csrf_headers(),
        )
        self.assertEqual(response.status_code, 429)
        self.assertFalse(PersonProfile.objects.filter(user=self.user).exists())

    @override_settings(  # type: ignore[untyped-decorator]
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        PASSWORD_RESET_EMAIL_ENABLED=True,
    )
    def test_password_reset_is_non_enumerating_and_invalidates_token(self) -> None:
        self.user.must_change_password = True
        self.user.initial_password_expires_at = timezone.now() - timedelta(minutes=1)
        self.user.save(update_fields=["must_change_password", "initial_password_expires_at"])
        headers = self.csrf_headers()
        unknown = self.client.post(
            "/api/v1/auth/password-reset/request",
            {"email": "missing@example.test"},
            content_type="application/json",
            **headers,
        )
        self.assertEqual(unknown.status_code, 202)
        self.assertEqual(len(mail.outbox), 0)

        requested = self.client.post(
            "/api/v1/auth/password-reset/request",
            {"email": self.user.email},
            content_type="application/json",
            **headers,
        )
        self.assertEqual(requested.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)
        match = re.search(r"uid=([^&]+)&token=([^\s]+)", mail.outbox[0].body)
        self.assertIsNotNone(match)
        assert match is not None
        uid, token = match.groups()
        confirmed = self.client.post(
            "/api/v1/auth/password-reset/confirm",
            {"uid": uid, "token": token, "new_password": "a-new-safe-password-2026"},
            content_type="application/json",
            **headers,
        )
        self.assertEqual(confirmed.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("a-new-safe-password-2026"))
        self.assertFalse(self.user.must_change_password)
        self.assertIsNone(self.user.initial_password_expires_at)
        replay = self.client.post(
            "/api/v1/auth/password-reset/confirm",
            {"uid": uid, "token": token, "new_password": "another-password-2026"},
            content_type="application/json",
            **headers,
        )
        self.assertEqual(replay.status_code, 400)

    def test_password_reset_is_unavailable_until_email_delivery_is_configured(self) -> None:
        response = self.client.post(
            "/api/v1/auth/password-reset/request",
            {"email": self.user.email},
            content_type="application/json",
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(AuditEvent.objects.filter(action="AUTH_PASSWORD_RESET_REQUESTED").exists())

    def test_expired_initial_password_invalidates_an_already_open_session(self) -> None:
        self.user.must_change_password = True
        self.user.initial_password_expires_at = timezone.now() + timedelta(minutes=5)
        self.user.save(update_fields=["must_change_password", "initial_password_expires_at"])
        logged_in = self.client.post(
            "/api/v1/auth/login",
            {"email": self.user.email, "password": "correct horse battery staple"},
            content_type="application/json",
            **self.csrf_headers(),
        )
        self.assertEqual(logged_in.status_code, 200)
        change_headers = self.csrf_headers()
        self.user.initial_password_expires_at = timezone.now() - timedelta(seconds=1)
        self.user.save(update_fields=["initial_password_expires_at"])

        changed = self.client.post(
            "/api/v1/auth/password/change",
            {
                "current_password": "correct horse battery staple",
                "new_password": "a-different-safe-password-2026",
            },
            content_type="application/json",
            **change_headers,
        )
        self.assertEqual(changed.status_code, 401)
        self.assertEqual(changed.json()["code"], "INITIAL_PASSWORD_EXPIRED")
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)

    def test_identity_tokens_are_not_valid_for_the_other_purpose(self) -> None:
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        headers = self.csrf_headers()
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        verification_token = email_verification_token_generator.make_token(self.user)
        response = self.client.post(
            "/api/v1/auth/password-reset/confirm",
            {
                "uid": uid,
                "token": verification_token,
                "new_password": "a-new-safe-password-2026",
            },
            content_type="application/json",
            **headers,
        )
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("correct horse battery staple"))

    def test_rate_limit_blocks_repeated_authentication_attempts(self) -> None:
        headers = self.csrf_headers()
        with override_settings(AUTH_RATE_LIMIT_PER_MINUTE=1, AUTH_RATE_LIMIT_IP_PER_MINUTE=20):
            first = self.client.post(
                "/api/v1/auth/login",
                {"email": self.user.email, "password": "wrong"},
                content_type="application/json",
                **headers,
            )
            second = self.client.post(
                "/api/v1/auth/login",
                {"email": self.user.email, "password": "wrong"},
                content_type="application/json",
                **headers,
            )
        self.assertEqual(first.status_code, 401)
        self.assertEqual(second.status_code, 429)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")  # type: ignore[untyped-decorator]
    def test_email_verification_request_and_confirmation(self) -> None:
        self.user.email_verified_at = None
        self.user.save(update_fields=["email_verified_at"])
        headers = self.csrf_headers()
        logged_in = self.client.post(
            "/api/v1/auth/login",
            {"email": self.user.email, "password": "correct horse battery staple"},
            content_type="application/json",
            **headers,
        )
        self.assertEqual(logged_in.status_code, 200)
        headers = self.csrf_headers()
        requested = self.client.post(
            "/api/v1/auth/email-verification/request",
            {},
            content_type="application/json",
            **headers,
        )
        self.assertEqual(requested.status_code, 200)
        match = re.search(r"uid=([^&]+)&token=([^\s]+)", mail.outbox[0].body)
        self.assertIsNotNone(match)
        assert match is not None
        uid, token = match.groups()
        confirmed = self.client.post(
            "/api/v1/auth/email-verification/confirm",
            {"uid": uid, "token": token},
            content_type="application/json",
            **headers,
        )
        self.assertEqual(confirmed.status_code, 200)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.email_verified_at)

    def test_untrusted_origin_is_rejected(self) -> None:
        response = self.client.get("/api/v1/health/live", HTTP_ORIGIN="https://attacker.example")
        self.assertEqual(response.status_code, 403)


class AuthorizationAndOwnershipTests(TestCase):
    def test_student_cannot_access_other_history_and_advisor_requires_assignment(self) -> None:
        first = foundation(suffix="owner-a")
        second = foundation(suffix="owner-b")
        self.assertTrue(can_view_student(first["user"], first["student"]))
        self.assertFalse(can_view_student(first["user"], second["student"]))
        self.assertFalse(can_edit_student_history(first["user"], second["student"]))

        advisor = User.objects.create_user(email="advisor@example.test", password="safe-password")
        RoleAssignment.objects.create(
            user=advisor,
            role=UserRole.ADVISOR.value,
            institution=second["institution"],
        )
        self.assertFalse(can_view_student(advisor, second["student"]))
        StudentAdvisorAssignment.objects.create(
            student=second["student"],
            advisor=advisor,
            rationale="Assigned for academic advising.",
        )
        self.assertTrue(can_view_student(advisor, second["student"]))
        self.assertFalse(can_view_student(advisor, first["student"]))

    def test_role_assignment_cannot_cross_program_institution_scope(self) -> None:
        first = foundation(suffix="role-scope-a")
        second = foundation(suffix="role-scope-b")
        reviewer = User.objects.create_user(
            email="scope-reviewer@example.test", password="safe-password"
        )
        with self.assertRaises(ValidationError):
            RoleAssignment.objects.create(
                user=reviewer,
                role=UserRole.REVIEWER.value,
                institution=first["institution"],
                program=second["program"],
            )

    def test_editor_cannot_publish_reviewer_can_and_published_is_not_editable(self) -> None:
        data = foundation(suffix="rbac")
        editor = User.objects.create_user(email="editor@example.test", password="safe-password")
        reviewer = User.objects.create_user(email="reviewer@example.test", password="safe-password")
        for user, role in ((editor, UserRole.EDITOR), (reviewer, UserRole.REVIEWER)):
            RoleAssignment.objects.create(
                user=user,
                role=role.value,
                institution=data["institution"],
                program=data["program"],
            )
        self.assertTrue(can_edit_revision(editor, data["revision"]))
        self.assertFalse(can_publish_revision(editor, data["revision"]))
        self.assertTrue(can_publish_revision(reviewer, data["revision"]))
        with self.assertRaises(RevisionTransitionError):
            CurriculumRevisionService.publish(data["revision"].pk, actor=editor)
        published = CurriculumRevisionService.publish(data["revision"].pk, actor=reviewer)
        self.assertEqual(published.status, "PUBLISHED")
        self.assertFalse(can_edit_revision(reviewer, published))
        published.total_required_credits = 142
        with self.assertRaises(PublishedRevisionImmutableError):
            published.save(update_fields=["total_required_credits"])
        self.assertTrue(
            AuditEvent.objects.filter(
                action="CURRICULUM_REVISION_PUBLISHED", actor=reviewer
            ).exists()
        )

    @override_settings(PRIVILEGED_MFA_REQUIRED=True)  # type: ignore[untyped-decorator]
    def test_privileged_publication_fails_closed_until_server_side_mfa_assurance(self) -> None:
        data = foundation(suffix="mfa-gate")
        reviewer = User.objects.create_user(
            email="mfa-reviewer@example.test", password="safe-password"
        )
        RoleAssignment.objects.create(
            user=reviewer,
            role=UserRole.REVIEWER.value,
            institution=data["institution"],
            program=data["program"],
        )

        reviewer._privileged_mfa_verified = False
        self.assertFalse(can_publish_revision(reviewer, data["revision"]))

        # The authorization boundary consumes only the server-side assurance
        # marker populated by the trusted IdP/session adapter. A request header
        # is intentionally not part of this contract.
        reviewer._privileged_mfa_verified = True
        self.assertTrue(can_publish_revision(reviewer, data["revision"]))


class AppendOnlyAuditEventTests(TestCase):
    def test_audit_events_cannot_be_changed_or_deleted(self) -> None:
        user = User.objects.create_user(email="audited@example.test", password="safe-password")
        event = AuditEvent.objects.create(actor=user, action="TEST_EVENT", metadata={"ok": True})
        event.action = "MUTATED"
        with self.assertRaises(AuditEventImmutableError):
            event.save(update_fields=["action"])
        with self.assertRaises(AuditEventImmutableError):
            event.delete()
        if connection.vendor == "postgresql":
            with self.assertRaises(DatabaseError), transaction.atomic():
                AuditEvent.objects.filter(pk=event.pk).update(action="MUTATED")
            with self.assertRaises(DatabaseError), transaction.atomic():
                AuditEvent.objects.filter(pk=event.pk).delete()
        event.refresh_from_db()
        self.assertEqual(event.action, "TEST_EVENT")

    def test_nested_audit_metadata_is_redacted(self) -> None:
        event = record_audit_event(
            None,
            action="TEST_METADATA",
            metadata={
                "context": {"email": "student@example.test", "safe": "kept"},
                "items": [{"token": "do-not-store"}],
            },
        )
        self.assertEqual(event.metadata["context"]["email"], "[REDACTED]")
        self.assertEqual(event.metadata["context"]["safe"], "kept")
        self.assertEqual(event.metadata["items"][0]["token"], "[REDACTED]")
