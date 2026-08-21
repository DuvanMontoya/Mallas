from __future__ import annotations

from datetime import datetime
from typing import Any, NoReturn
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from ninja import Router, Schema
from ninja.security import django_auth

from modules.analytics.application.services import (
    AnalyticsError,
    analytics_definitions,
    build_institutional_analytics,
    build_student_analytics,
    export_institutional_analytics,
)
from modules.common.api import raise_problem, with_problem_responses


class AnalyticsDefinitionView(Schema):
    key: str
    label: str
    description: str
    source: str
    epistemic_status: str
    privacy: str


class AnalyticsDefinitionsView(Schema):
    schema_version: str
    definitions: list[AnalyticsDefinitionView]


class StudentAnalyticsView(Schema):
    schema_version: str
    scope: str
    data_state: str
    as_of: datetime | None
    enrollment_id: UUID
    program_code: str
    program_name: str
    plan_code: str | None
    revision_code: str | None
    snapshot: dict[str, Any] | None
    metrics: dict[str, Any]
    definitions: list[AnalyticsDefinitionView]
    warnings: list[str]


class InstitutionalAnalyticsView(Schema):
    schema_version: str
    scope: str
    data_state: str
    institution_id: UUID
    program_id: UUID | None
    term_code: str | None
    min_cell_size: int
    privacy: dict[str, Any]
    population: dict[str, Any]
    metrics: dict[str, Any]
    definitions: list[AnalyticsDefinitionView]
    warnings: list[str]


router = Router(tags=["Analytics"])


def _error(error: AnalyticsError) -> NoReturn:
    if error.code.endswith("not_found"):
        status = 404
    elif error.code.endswith("forbidden"):
        status = 403
    elif error.code in {"scope_invalid", "export_format_invalid"}:
        status = 422
    else:
        status = 400
    raise_problem(
        status=status,
        code=error.code.upper(),
        title="Analytics request cannot be completed",
        detail=str(error),
    )


@router.get(
    "/analytics/definitions",
    auth=django_auth,
    response=with_problem_responses(AnalyticsDefinitionsView),
)
def definitions(request: HttpRequest) -> dict[str, Any]:
    del request
    return {"schema_version": "1.0", "definitions": analytics_definitions()}


@router.get(
    "/analytics/student",
    auth=django_auth,
    response=with_problem_responses(StudentAnalyticsView),
)
def student_analytics(
    request: HttpRequest,
    enrollment_id: UUID | None = None,
) -> dict[str, Any]:
    try:
        return build_student_analytics(request.auth, enrollment_id=enrollment_id)
    except AnalyticsError as error:
        _error(error)


@router.get(
    "/analytics/institutional",
    auth=django_auth,
    response=with_problem_responses(InstitutionalAnalyticsView),
)
def institutional_analytics(
    request: HttpRequest,
    institution_id: UUID,
    program_id: UUID | None = None,
    term_code: str | None = None,
    min_cell_size: int | None = None,
) -> dict[str, Any]:
    try:
        return build_institutional_analytics(
            request.auth,
            institution_id=institution_id,
            program_id=program_id,
            term_code=term_code,
            requested_min_cell_size=min_cell_size,
        )
    except AnalyticsError as error:
        _error(error)


@router.get(
    "/analytics/institutional/export",
    auth=django_auth,
    response=with_problem_responses(InstitutionalAnalyticsView),
)
def institutional_export(
    request: HttpRequest,
    institution_id: UUID,
    program_id: UUID | None = None,
    term_code: str | None = None,
    min_cell_size: int | None = None,
    format: str = "json",
) -> dict[str, Any] | HttpResponse:
    try:
        return export_institutional_analytics(
            request,
            request.auth,
            institution_id=institution_id,
            program_id=program_id,
            term_code=term_code,
            requested_min_cell_size=min_cell_size,
            export_format=format,
        )
    except AnalyticsError as error:
        _error(error)
