from __future__ import annotations

import logging
from binascii import Error as Base64Error
from datetime import date, datetime
from typing import Any

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from ninja import Header, Router, Schema, Status
from ninja.errors import HttpError
from ninja.security import APIKeyCookie, django_auth

from modules.common.api import with_problem_responses
from modules.identity.application.audit import digest_identifier, record_audit_event
from modules.identity.application.authorization import roles_for
from modules.identity.application.profile import (
    PersonProfileError,
    person_profile_export,
    person_profile_view,
    update_own_person_profile,
)
from modules.identity.application.rate_limit import consume_rate_limit
from modules.identity.models import User

logger = logging.getLogger(__name__)


class _IdentityTokenGenerator(PasswordResetTokenGenerator):
    """Keep password-reset and email-verification links purpose-specific."""

    def __init__(self, purpose: str) -> None:
        super().__init__()
        self.purpose = purpose

    def _make_hash_value(self, user: User, timestamp: int) -> str:
        return f"{self.purpose}:{super()._make_hash_value(user, timestamp)}"


password_reset_token_generator = _IdentityTokenGenerator("password-reset")
email_verification_token_generator = _IdentityTokenGenerator("email-verification")


class CsrfOnlyAuth(APIKeyCookie):
    """Run Ninja's cookie CSRF check without requiring an authenticated session."""

    param_name = settings.SESSION_COOKIE_NAME

    def authenticate(self, request: HttpRequest, key: str | None) -> bool:
        del request, key
        return True


csrf_only_auth = CsrfOnlyAuth()
router = Router(tags=["Identity"])


class LoginPayload(Schema):
    email: str
    password: str


class PasswordResetRequestPayload(Schema):
    email: str


class PasswordResetConfirmPayload(Schema):
    uid: str
    token: str
    new_password: str


class PasswordChangePayload(Schema):
    current_password: str
    new_password: str


class TokenPayload(Schema):
    uid: str
    token: str


class UserView(Schema):
    id: int
    email: str
    email_verified: bool
    roles: list[str]
    student_profile_id: str | None
    must_change_password: bool
    onboarding_required: bool


class AuthView(Schema):
    detail: str
    user: UserView


class MessageView(Schema):
    detail: str


class CsrfView(Schema):
    csrf_token: str


class PersonProfileView(Schema):
    email: str
    first_name: str
    middle_names: str
    first_surname: str
    second_surname: str
    preferred_name: str
    birth_date: date | None
    age: int | None
    data_status: str
    verification_method: str
    version: str


class PersonProfileUpdatePayload(Schema):
    first_name: str
    middle_names: str = ""
    first_surname: str
    second_surname: str = ""
    preferred_name: str = ""
    birth_date: date


class PersonProfileExportAccount(Schema):
    email: str


class PersonProfileExportIdentity(Schema):
    first_name: str
    middle_names: str
    first_surname: str
    second_surname: str
    preferred_name: str
    birth_date: date | None
    data_status: str
    verification_method: str


class PersonProfileExportView(Schema):
    schema_version: str
    exported_at: datetime
    account: PersonProfileExportAccount
    identity: PersonProfileExportIdentity


def _user_view(user: User) -> dict[str, Any]:
    try:
        student_profile = user.student_profile
        student_profile_id: str | None = str(student_profile.pk)
        onboarding_required = student_profile.program_enrollments.filter(
            onboarding__completed_at__isnull=True
        ).exists()
    except User.student_profile.RelatedObjectDoesNotExist:
        student_profile_id = None
        onboarding_required = False
    return {
        "id": user.pk,
        "email": user.email,
        "email_verified": user.email_verified_at is not None,
        "roles": list(roles_for(user)),
        "student_profile_id": student_profile_id,
        "must_change_password": user.must_change_password,
        "onboarding_required": onboarding_required,
    }


def _client_ip(request: HttpRequest) -> str:
    return request.META.get("REMOTE_ADDR", "unknown") or "unknown"


def _rate_limited(request: HttpRequest, identifier: str, action: str) -> bool:
    ip_allowed = consume_rate_limit(
        key=f"ip:{_client_ip(request)}",
        action=f"{action}:ip",
        limit=settings.AUTH_RATE_LIMIT_IP_PER_MINUTE,
    )
    identifier_allowed = consume_rate_limit(
        key=f"identifier:{identifier}",
        action=f"{action}:identifier",
        limit=settings.AUTH_RATE_LIMIT_PER_MINUTE,
    )
    return not (ip_allowed and identifier_allowed)


def _decode_user(uid: str) -> User:
    try:
        decoded = force_str(urlsafe_base64_decode(uid))
        return User.objects.get(pk=decoded, is_active=True)
    except (
        Base64Error,
        ValueError,
        TypeError,
        OverflowError,
        UnicodeDecodeError,
        User.DoesNotExist,
    ):
        raise HttpError(400, "Invalid token.") from None


def _set_session_password_marker(request: HttpRequest, user: User) -> None:
    request.session["password_changed_at"] = (
        user.password_changed_at.isoformat() if user.password_changed_at else ""
    )


def _send_link(*, user: User, path: str, token: str, uid: str, subject: str) -> None:
    url = f"{settings.PUBLIC_APP_URL.rstrip('/')}{path}?uid={uid}&token={token}"
    try:
        send_mail(
            subject,
            f"Use este enlace para continuar: {url}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=not settings.DEBUG,
        )
    except Exception:
        logger.exception("Unable to send an identity email")


@router.get("/csrf", response=with_problem_responses(CsrfView))
def csrf_token(request: HttpRequest) -> dict[str, str]:
    return {"csrf_token": get_token(request)}


@router.post("/login", auth=csrf_only_auth, response=with_problem_responses(AuthView))
def login_view(request: HttpRequest, payload: LoginPayload) -> dict[str, Any]:
    email = payload.email.strip().lower()
    if _rate_limited(request, email, "login"):
        record_audit_event(
            request,
            action="AUTH_RATE_LIMITED",
            metadata={"action": "login", "identifier_digest": digest_identifier(email)},
        )
        raise HttpError(429, "Too many authentication attempts.")
    user = authenticate(request, username=email, password=payload.password)
    if user is None or not getattr(user, "is_active", False):
        record_audit_event(
            request,
            action="AUTH_LOGIN_FAILED",
            metadata={"identifier_digest": digest_identifier(email)},
        )
        raise HttpError(401, "Invalid credentials.")
    if settings.EMAIL_VERIFICATION_REQUIRED and user.email_verified_at is None:
        record_audit_event(
            request,
            action="AUTH_LOGIN_UNVERIFIED",
            actor=user,
            metadata={"identifier_digest": digest_identifier(email)},
        )
        raise HttpError(401, "Invalid credentials.")
    if user.initial_password_expires_at and user.initial_password_expires_at <= timezone.now():
        record_audit_event(request, action="AUTH_INITIAL_PASSWORD_EXPIRED", actor=user)
        raise HttpError(401, "Invalid credentials.")
    login(request, user)
    _set_session_password_marker(request, user)
    record_audit_event(request, action="AUTH_LOGIN_SUCCEEDED", actor=user)
    return {"detail": "Authenticated.", "user": _user_view(user)}


@router.post("/password/change", auth=django_auth, response=with_problem_responses(MessageView))
def password_change(request: HttpRequest, payload: PasswordChangePayload) -> dict[str, str]:
    user: User = request.auth
    if not user.check_password(payload.current_password):
        raise HttpError(400, "Current password is invalid.")
    if payload.new_password == payload.current_password:
        raise HttpError(400, "The new password must differ from the current password.")
    try:
        from django.contrib.auth.password_validation import validate_password

        validate_password(payload.new_password, user)
    except ValidationError as error:
        raise HttpError(400, str(error)) from error
    user.set_password(payload.new_password)
    user.password_changed_at = timezone.now()
    user.must_change_password = False
    user.initial_password_expires_at = None
    user.save(
        update_fields=[
            "password",
            "password_changed_at",
            "must_change_password",
            "initial_password_expires_at",
        ]
    )
    update_session_auth_hash(request, user)
    _set_session_password_marker(request, user)
    record_audit_event(request, action="AUTH_INITIAL_PASSWORD_CHANGED", actor=user)
    return {"detail": "Password updated."}


@router.post("/logout", auth=django_auth, response=with_problem_responses(MessageView))
def logout_view(request: HttpRequest) -> dict[str, str]:
    user = request.auth
    record_audit_event(request, action="AUTH_LOGOUT", actor=user)
    logout(request)
    return {"detail": "Signed out."}


@router.get("/me", auth=django_auth, response=with_problem_responses(UserView))
def me_view(request: HttpRequest) -> dict[str, Any]:
    return _user_view(request.auth)


@router.get("/profile", auth=django_auth, response=with_problem_responses(PersonProfileView))
def profile_view(request: HttpRequest, response: HttpResponse) -> dict[str, Any]:
    response["Cache-Control"] = "private, no-store"
    return person_profile_view(request.auth)


@router.patch("/profile", auth=django_auth, response=with_problem_responses(PersonProfileView))
def profile_update(
    request: HttpRequest,
    response: HttpResponse,
    payload: PersonProfileUpdatePayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        profile = update_own_person_profile(
            actor=request.auth,
            expected_version=if_match,
            request=request,
            **payload.model_dump(),
        )
    except PersonProfileError as error:
        status = (
            428
            if error.code == "person_profile_precondition_required"
            else 409
            if error.code
            in {
                "person_profile_stale_resource",
                "person_profile_institutional_correction_required",
            }
            else 422
        )
        raise HttpError(status, str(error)) from error
    response["Cache-Control"] = "private, no-store"
    return person_profile_view(profile.user)


@router.get(
    "/profile/export",
    auth=django_auth,
    response=with_problem_responses(PersonProfileExportView),
)
def profile_export(request: HttpRequest, response: HttpResponse) -> dict[str, Any]:
    record_audit_event(request, action="PERSON_IDENTITY_EXPORTED", actor=request.auth)
    response["Cache-Control"] = "private, no-store"
    return person_profile_export(request.auth)


@router.post(
    "/password-reset/request",
    auth=csrf_only_auth,
    response=with_problem_responses({202: MessageView}),
)
def password_reset_request(
    request: HttpRequest, payload: PasswordResetRequestPayload
) -> Status[dict[str, str]]:
    email = payload.email.strip().lower()
    if _rate_limited(request, email, "password_reset"):
        record_audit_event(
            request,
            action="AUTH_RATE_LIMITED",
            metadata={"action": "password_reset", "identifier_digest": digest_identifier(email)},
        )
        raise HttpError(429, "Too many authentication attempts.")
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is not None:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = password_reset_token_generator.make_token(user)
        _send_link(
            user=user,
            path="/reset-password",
            token=token,
            uid=uid,
            subject="Restablecimiento de contraseña",
        )
        record_audit_event(request, action="AUTH_PASSWORD_RESET_REQUESTED", actor=user)
    return Status(202, {"detail": "If the account exists, instructions have been sent."})


@router.post(
    "/password-reset/confirm",
    auth=csrf_only_auth,
    response=with_problem_responses(MessageView),
)
def password_reset_confirm(
    request: HttpRequest, payload: PasswordResetConfirmPayload
) -> dict[str, str]:
    if _rate_limited(request, payload.uid, "password_reset_confirm"):
        record_audit_event(
            request,
            action="AUTH_RATE_LIMITED",
            metadata={
                "action": "password_reset_confirm",
                "identifier_digest": digest_identifier(payload.uid),
            },
        )
        raise HttpError(429, "Too many authentication attempts.")
    user = _decode_user(payload.uid)
    if not password_reset_token_generator.check_token(user, payload.token):
        raise HttpError(400, "Invalid or expired token.")
    try:
        from django.contrib.auth.password_validation import validate_password

        validate_password(payload.new_password, user)
    except ValidationError as error:
        raise HttpError(400, str(error)) from error
    user.set_password(payload.new_password)
    user.password_changed_at = timezone.now()
    user.must_change_password = False
    user.initial_password_expires_at = None
    user.save(
        update_fields=[
            "password",
            "password_changed_at",
            "must_change_password",
            "initial_password_expires_at",
        ]
    )
    record_audit_event(request, action="AUTH_PASSWORD_RESET_COMPLETED", actor=user)
    logout(request)
    return {"detail": "Password updated."}


@router.post(
    "/email-verification/request",
    auth=django_auth,
    response=with_problem_responses(MessageView),
)
def email_verification_request(request: HttpRequest) -> dict[str, str]:
    user: User = request.auth
    if _rate_limited(request, str(user.pk), "email_verification_request"):
        record_audit_event(
            request,
            action="AUTH_RATE_LIMITED",
            actor=user,
            metadata={"action": "email_verification_request"},
        )
        raise HttpError(429, "Too many authentication attempts.")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token_generator.make_token(user)
    _send_link(
        user=user,
        path="/verify-email",
        token=token,
        uid=uid,
        subject="Verificación de correo electrónico",
    )
    record_audit_event(request, action="AUTH_EMAIL_VERIFICATION_REQUESTED", actor=user)
    return {"detail": "If the account is eligible, instructions have been sent."}


@router.post(
    "/email-verification/confirm",
    auth=csrf_only_auth,
    response=with_problem_responses(MessageView),
)
def email_verification_confirm(request: HttpRequest, payload: TokenPayload) -> dict[str, str]:
    if _rate_limited(request, payload.uid, "email_verification_confirm"):
        record_audit_event(
            request,
            action="AUTH_RATE_LIMITED",
            metadata={
                "action": "email_verification_confirm",
                "identifier_digest": digest_identifier(payload.uid),
            },
        )
        raise HttpError(429, "Too many authentication attempts.")
    user = _decode_user(payload.uid)
    if not email_verification_token_generator.check_token(user, payload.token):
        raise HttpError(400, "Invalid or expired token.")
    if user.email_verified_at is None:
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])
    record_audit_event(request, action="AUTH_EMAIL_VERIFIED", actor=user)
    return {"detail": "Email verified."}
