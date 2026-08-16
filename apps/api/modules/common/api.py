from __future__ import annotations

import logging
import re
import uuid
from typing import Any, NoReturn

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from ninja import Schema
from pydantic import Field

logger = logging.getLogger(__name__)

ERROR_RESPONSE_CODES = (400, 401, 403, 404, 409, 422, 428, 429, 500)
_CORRELATION_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
_IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class ProblemDetails(Schema):
    """Stable, machine-readable error envelope for every v1 API failure."""

    type: str
    code: str
    title: str
    detail: str
    status: int
    correlation_id: str
    fields: dict[str, Any] = Field(default_factory=dict)


class ApiProblemError(RuntimeError):
    """An intentional API error with a stable code and safe public detail."""

    def __init__(
        self,
        *,
        status: int,
        code: str,
        title: str,
        detail: str,
        fields: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.fields = fields or {}


def _safe_header_value(value: str | None) -> str:
    if value and _CORRELATION_PATTERN.fullmatch(value):
        return value
    return str(uuid.uuid4())


def ensure_correlation_id(request: HttpRequest) -> str:
    """Attach a non-injectable correlation id to the request exactly once."""

    existing = getattr(request, "correlation_id", None)
    if isinstance(existing, str) and existing:
        return existing
    correlation_id = _safe_header_value(request.headers.get("X-Request-ID"))
    request.correlation_id = correlation_id
    return correlation_id


def problem_response(
    request: HttpRequest,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    fields: dict[str, Any] | None = None,
) -> HttpResponse:
    correlation_id = ensure_correlation_id(request)
    payload = {
        "type": f"{getattr(settings, 'API_PROBLEM_BASE_URL', 'https://api.curriculum-navigator.local/problems').rstrip('/')}/{code}",
        "code": code,
        "title": title,
        "detail": detail,
        "status": status,
        "correlation_id": correlation_id,
        "fields": fields or {},
    }
    # Keep the media type aligned with the generated OpenAPI response map. The
    # envelope follows Problem Details fields without forcing clients to
    # negotiate a different media type.
    response = JsonResponse(payload, status=status)
    response["X-Request-ID"] = correlation_id
    return response


def raise_problem(
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    fields: dict[str, Any] | None = None,
) -> NoReturn:
    raise ApiProblemError(
        status=status,
        code=code,
        title=title,
        detail=detail,
        fields=fields,
    )


def validate_idempotency_key(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not _IDEMPOTENCY_PATTERN.fullmatch(value):
        raise_problem(
            status=400,
            code="IDEMPOTENCY_KEY_INVALID",
            title="Invalid idempotency key",
            detail="Idempotency-Key must contain 1–128 safe ASCII characters.",
        )
    return value


def require_if_match(value: str | None) -> str:
    if value is None or value == "":
        raise_problem(
            status=428,
            code="PRECONDITION_REQUIRED",
            title="Precondition required",
            detail="This edit requires the current resource version in If-Match.",
        )
    if len(value) > 240 or any(ord(character) < 32 for character in value):
        raise_problem(
            status=400,
            code="IF_MATCH_INVALID",
            title="Invalid concurrency token",
            detail="If-Match contains an invalid resource version.",
        )
    return value.strip('"')


def with_problem_responses(response: Any) -> dict[Any, Any]:
    """Add one shared error schema to an operation without duplicating DTOs."""

    response_map = dict(response) if isinstance(response, dict) else {200: response}
    for code in ERROR_RESPONSE_CODES:
        response_map.setdefault(code, ProblemDetails)
    return response_map


def csrf_failure(request: HttpRequest, reason: str = "") -> HttpResponse:
    del reason
    return problem_response(
        request,
        status=403,
        code="CSRF_FAILED",
        title="CSRF validation failed",
        detail="The request could not be verified. Obtain a fresh CSRF token and retry.",
    )
