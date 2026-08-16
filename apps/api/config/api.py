from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection
from django.http import Http404, HttpRequest, HttpResponse
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from ninja.errors import ValidationError as NinjaValidationError

from modules.common.api import (
    ApiProblemError,
    problem_response,
    with_problem_responses,
)
from modules.identity.api import router as identity_router
from modules.imports.api import router as history_router
from modules.student_records.api import router as student_records_router

logger = logging.getLogger(__name__)


class HealthResponse(Schema):
    status: str
    service: str
    version: str


class ReadyResponse(Schema):
    status: str
    service: str
    database: str


api = NinjaAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="API versionada para navegación curricular y planificación académica explicable.",
    urls_namespace="curriculum_navigator_api",
)


def _http_problem_code(status: int) -> tuple[str, str]:
    return {
        400: ("INVALID_REQUEST", "Invalid request"),
        401: ("AUTHENTICATION_REQUIRED", "Authentication required"),
        403: ("FORBIDDEN", "Forbidden"),
        404: ("NOT_FOUND", "Resource not found"),
        409: ("CONFLICT", "Conflict"),
        422: ("VALIDATION_ERROR", "Request validation failed"),
        428: ("PRECONDITION_REQUIRED", "Precondition required"),
        429: ("RATE_LIMITED", "Too many requests"),
    }.get(status, ("HTTP_ERROR", "Request failed"))


def _validation_fields(errors: list[dict[str, Any]]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for error in errors:
        location = error.get("loc", ())
        key = ".".join(str(part) for part in location) or "request"
        fields[key] = error.get("msg", "Invalid value")
    return fields


def _django_validation_fields(error: DjangoValidationError) -> dict[str, Any]:
    if hasattr(error, "message_dict"):
        return {str(key): value for key, value in error.message_dict.items()}
    return {"request": error.messages}


@api.exception_handler(ApiProblemError)
def api_problem_handler(request: HttpRequest, error: ApiProblemError) -> HttpResponse:
    return problem_response(
        request,
        status=error.status,
        code=error.code,
        title=error.title,
        detail=error.detail,
        fields=error.fields,
    )


@api.exception_handler(NinjaValidationError)
def ninja_validation_handler(request: HttpRequest, error: NinjaValidationError) -> HttpResponse:
    return problem_response(
        request,
        status=422,
        code="VALIDATION_ERROR",
        title="Request validation failed",
        detail="One or more request fields are invalid.",
        fields=_validation_fields(error.errors),
    )


@api.exception_handler(DjangoValidationError)
def django_validation_handler(request: HttpRequest, error: DjangoValidationError) -> HttpResponse:
    return problem_response(
        request,
        status=422,
        code="VALIDATION_ERROR",
        title="Request validation failed",
        detail="The requested data does not satisfy domain constraints.",
        fields=_django_validation_fields(error),
    )


@api.exception_handler(HttpError)
def http_error_handler(request: HttpRequest, error: HttpError) -> HttpResponse:
    if "csrf" in str(error).lower():
        return problem_response(
            request,
            status=403,
            code="CSRF_FAILED",
            title="CSRF validation failed",
            detail="The request could not be verified. Obtain a fresh CSRF token and retry.",
        )
    code, title = _http_problem_code(error.status_code)
    return problem_response(
        request,
        status=error.status_code,
        code=code,
        title=title,
        detail=str(error),
    )


@api.exception_handler(Http404)
def not_found_handler(request: HttpRequest, error: Http404) -> HttpResponse:
    del error
    return problem_response(
        request,
        status=404,
        code="NOT_FOUND",
        title="Resource not found",
        detail="The requested resource does not exist.",
    )


@api.exception_handler(PermissionDenied)
def permission_denied_handler(request: HttpRequest, error: PermissionDenied) -> HttpResponse:
    del error
    return problem_response(
        request,
        status=403,
        code="FORBIDDEN",
        title="Forbidden",
        detail="You are not allowed to perform this operation.",
    )


@api.exception_handler(Exception)
def unhandled_api_exception(request: HttpRequest, error: Exception) -> HttpResponse:
    logger.exception("Unhandled API exception", exc_info=error)
    return problem_response(
        request,
        status=500,
        code="INTERNAL_ERROR",
        title="Internal server error",
        detail="An unexpected error occurred. Use correlation_id when contacting support.",
    )


api.add_router("/auth", identity_router)
api.add_router("/history", history_router)
api.add_router("/history", student_records_router)


@api.get("/health/live", response=with_problem_responses(HealthResponse), tags=["Operations"])
def live_health(request: object) -> dict[str, str]:
    del request
    return {"status": "ok", "service": "api", "version": "0.1.0"}


@api.get("/health/ready", response=with_problem_responses(ReadyResponse), tags=["Operations"])
def ready_health(request: object) -> dict[str, str]:
    del request
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return {"status": "ready", "service": "api", "database": "ok"}
