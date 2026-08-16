from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse

from modules.common.api import ensure_correlation_id, problem_response


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
            response["Access-Control-Allow-Headers"] = "Content-Type, X-CSRFToken, X-Request-ID"
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
