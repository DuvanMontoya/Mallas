from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse

from modules.common.api import ensure_correlation_id, problem_response
from modules.identity.application.rate_limit import consume_rate_limit


class OriginAndSecurityMiddleware:
    """Enforce the first-party origin policy and emit API security headers."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = ensure_correlation_id(request)
        origin = request.headers.get("Origin")
        allowed_origins = set(getattr(settings, "CORS_ALLOWED_ORIGINS", []))
        if origin and origin not in allowed_origins and request.path.startswith("/api/"):
            response = problem_response(
                request,
                status=403,
                code="ORIGIN_NOT_ALLOWED",
                title="Origin not allowed",
                detail="The request origin is not allowed for this API.",
            )
            response["X-Request-ID"] = correlation_id
            return response
        if origin and request.method == "OPTIONS" and origin in allowed_origins:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)
        if origin and origin in allowed_origins:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Headers"] = (
                "Content-Type, X-CSRFToken, X-Request-ID, Idempotency-Key, If-Match, X-Metrics-Token"
            )
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response["Vary"] = "Origin"
        response.setdefault(
            "Content-Security-Policy",
            getattr(
                settings,
                "CONTENT_SECURITY_POLICY",
                "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'; object-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'",
            ),
        )
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response["X-Request-ID"] = correlation_id
        return response


class PasswordChangeSessionMiddleware:
    """Invalidate sessions created before a password reset/change."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            changed_at = getattr(user, "password_changed_at", None)
            expected = changed_at.isoformat() if changed_at else ""
            if request.session.get("password_changed_at", "") != expected:
                logout(request)
            else:
                request.session["password_changed_at"] = expected
        return self.get_response(request)


class PrivilegedMfaSessionMiddleware:
    """Expose only a server-side IdP assurance marker to authorization code.

    No request header is accepted as proof of MFA. A trusted institutional IdP
    adapter must set the configured session key after validating its assertion;
    production otherwise fails closed for reviewer/admin publication actions.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            setattr(
                user,
                "_privileged_mfa_verified",
                bool(request.session.get(settings.PRIVILEGED_MFA_SESSION_KEY)),
            )
        return self.get_response(request)


class MutationRateLimitMiddleware:
    """Apply a shared database rate limit to state-changing API requests.

    Authentication endpoints keep their stricter identifier/IP limits in the
    identity router. This middleware covers upload, governance, planning,
    history, notification and optimizer mutations so an authenticated session
    cannot bypass protection by rotating request paths or using another worker.
    """

    _MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    @staticmethod
    def _bucket(request: HttpRequest) -> tuple[str, int, str] | None:
        if request.method not in MutationRateLimitMiddleware._MUTATING_METHODS:
            return None
        path = request.path
        if not path.startswith("/api/v1/") or path.startswith("/api/v1/auth/"):
            return None
        if path in {"/api/v1/health/ready", "/api/v1/health/metrics"}:
            return None
        user = getattr(request, "user", None)
        user_pk = getattr(user, "pk", None) if user is not None else None
        if getattr(user, "is_authenticated", False) and user_pk:
            key = f"user:{user_pk}"
        else:
            key = f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"
        if "/history/imports" in path and request.method == "POST":
            return key, 10, "api:history-upload"
        if "/governance/" in path:
            return key, 60, "api:governance-mutation"
        return key, 120, "api:mutation"

    def __call__(self, request: HttpRequest) -> HttpResponse:
        bucket = self._bucket(request)
        if bucket is not None:
            key, default_limit, action = bucket
            if action == "api:history-upload":
                limit = int(getattr(settings, "API_UPLOAD_RATE_LIMIT_PER_MINUTE", default_limit))
            elif action == "api:governance-mutation":
                limit = int(
                    getattr(settings, "API_GOVERNANCE_RATE_LIMIT_PER_MINUTE", default_limit)
                )
            else:
                limit = int(getattr(settings, "API_MUTATION_RATE_LIMIT_PER_MINUTE", default_limit))
            if not consume_rate_limit(key=key, action=action, limit=limit):
                response = problem_response(
                    request,
                    status=429,
                    code="RATE_LIMITED",
                    title="Too many requests",
                    detail="Retry after the current rate-limit window has elapsed.",
                )
                response["Retry-After"] = "60"
                return response
        return self.get_response(request)
