from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, NoReturn
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from ninja import Header, Router, Schema, Status
from ninja.security import django_auth

from modules.common.api import raise_problem, require_if_match, with_problem_responses
from modules.planning.application.scenarios import (
    ScenarioError,
    _get_scenario,
    add_planned_course,
    compare_scenarios,
    create_scenario,
    delete_planned_course,
    duplicate_scenario,
    list_scenarios,
    scenario_view,
    shared_scenario_view,
    update_planned_course,
    update_scenario,
)


class PlanningPreferenceView(Schema):
    id: UUID
    max_credits_per_term: int
    min_credits_per_term: int
    unavailable_weekdays: list[int]
    preferred_modalities: list[str]
    preferred_area_codes: list[str]
    objective_weights: dict[str, Any]


class ScenarioWarningView(Schema):
    code: str
    detail: str
    severity: str
    course_code: str | None
    term_code: str | None


class CourseValidationView(Schema):
    planned_course_id: UUID
    course_code: str
    term_code: str
    prerequisite_state: str
    offering_state: str
    reasons: list[str]


class ScenarioValidationView(Schema):
    state: str
    courses: list[CourseValidationView]
    warnings: list[ScenarioWarningView]


class PlannedCourseView(Schema):
    id: UUID
    course_version_id: UUID
    course_code: str
    course_name: str
    credits: int | None
    term_id: UUID
    term_code: str
    section_id: UUID | None
    section_group_code: str | None
    priority: int
    source: str
    notes: str
    is_locked: bool


class ScenarioAuditProjectionView(Schema):
    id: UUID
    input_fingerprint: str
    revision_hash: str
    engine_version: str
    result_hash: str
    generated_at: datetime
    unknown_count: int
    payload: dict[str, Any]


class ScenarioView(Schema):
    id: UUID
    enrollment_id: UUID
    name: str
    status: str
    version: int
    target_term_id: UUID | None
    target_term_code: str | None
    sharing_enabled: bool
    share_token: UUID | None
    created_at: datetime
    updated_at: datetime
    preferences: PlanningPreferenceView
    planned_courses: list[PlannedCourseView]
    validation: ScenarioValidationView
    audit_projection: ScenarioAuditProjectionView | None


class ScenarioCollectionView(Schema):
    items: list[ScenarioView]


class ScenarioCreatePayload(Schema):
    name: str
    enrollment_id: UUID | None = None
    target_term_id: UUID | None = None
    preferences: dict[str, Any] | None = None


class ScenarioPatchPayload(Schema):
    name: str | None = None
    status: str | None = None
    target_term_id: UUID | None = None
    sharing_enabled: bool | None = None
    preferences: dict[str, Any] | None = None


class PlannedCourseCreatePayload(Schema):
    course_version_id: UUID
    term_id: UUID
    section_id: UUID | None = None
    priority: int = 0
    notes: str = ""


class PlannedCoursePatchPayload(Schema):
    term_id: UUID | None = None
    section_id: UUID | None = None
    priority: int | None = None
    notes: str | None = None
    is_locked: bool | None = None


class DuplicateScenarioPayload(Schema):
    name: str


class ScenarioCompareSide(Schema):
    id: UUID
    name: str
    version: int


class ScenarioCompareItem(Schema):
    course_code: str
    term_code: str | None = None
    from_term: str | None = None
    to_term: str | None = None


class ScenarioCompareView(Schema):
    left: ScenarioCompareSide
    right: ScenarioCompareSide
    added: list[ScenarioCompareItem]
    removed: list[ScenarioCompareItem]
    moved: list[ScenarioCompareItem]
    unchanged: list[str]


class SharedScenarioCourseView(Schema):
    course_code: str
    course_name: str
    credits: int | None
    term_code: str


class SharedScenarioView(Schema):
    id: UUID
    name: str
    status: str
    target_term_code: str | None
    planned_courses: list[SharedScenarioCourseView]
    privacy: str


router = Router(tags=["Planning"])


def _error(error: ScenarioError) -> NoReturn:
    if error.code.endswith("forbidden") or error.code in {"enrollment_required"}:
        status = 403
    elif error.code.endswith("not_found") or error.code == "share_not_found":
        status = 404
    elif error.code in {
        "stale_resource",
        "scenario_name_duplicate",
        "planned_course_duplicate",
        "planned_course_locked",
        "compare_enrollment_mismatch",
    }:
        status = 409
    else:
        status = 400
    raise_problem(
        status=status,
        code=error.code.upper(),
        title="Planning request cannot be completed",
        detail=str(error),
    )


def _etag(version: int) -> str:
    return f'"{version}"'


def _collection_etag(payload: object) -> str:
    return (
        f'"{hashlib.sha256(json.dumps(payload, default=str, sort_keys=True).encode()).hexdigest()}"'
    )


@router.get(
    "/scenarios",
    auth=django_auth,
    response=with_problem_responses(ScenarioCollectionView),
)
def scenarios(
    request: HttpRequest,
    response: HttpResponse,
    enrollment_id: UUID | None = None,
    include_archived: bool = False,
) -> dict[str, Any]:
    try:
        payload = {
            "items": list_scenarios(
                request.auth, enrollment_id=enrollment_id, include_archived=include_archived
            )
        }
    except ScenarioError as error:
        _error(error)
    response["ETag"] = _collection_etag(payload)
    return payload


@router.post(
    "/scenarios",
    auth=django_auth,
    response=with_problem_responses({201: ScenarioView}),
)
def scenario_create(
    request: HttpRequest,
    response: HttpResponse,
    payload: ScenarioCreatePayload,
) -> Status[dict[str, Any]]:
    try:
        scenario = create_scenario(
            request.auth,
            name=payload.name,
            enrollment_id=payload.enrollment_id,
            target_term_id=payload.target_term_id,
            preferences=payload.preferences,
        )
        view = scenario_view(scenario)
    except ScenarioError as error:
        _error(error)
    response["ETag"] = _etag(view["version"])
    return Status(201, view)


@router.get(
    "/scenarios/compare",
    auth=django_auth,
    response=with_problem_responses(ScenarioCompareView),
)
def scenario_compare(
    request: HttpRequest,
    left_id: UUID,
    right_id: UUID,
) -> dict[str, Any]:
    try:
        return compare_scenarios(request.auth, left_id, right_id)
    except ScenarioError as error:
        _error(error)


@router.get(
    "/shared/scenarios/{share_token}",
    auth=django_auth,
    response=with_problem_responses(SharedScenarioView),
)
def shared_scenario(request: HttpRequest, share_token: UUID) -> dict[str, Any]:
    try:
        return shared_scenario_view(request.auth, share_token)
    except ScenarioError as error:
        _error(error)


@router.get(
    "/scenarios/{scenario_id}",
    auth=django_auth,
    response=with_problem_responses(ScenarioView),
)
def scenario_detail(
    request: HttpRequest,
    response: HttpResponse,
    scenario_id: UUID,
) -> dict[str, Any]:
    try:
        scenario = _get_scenario(request.auth, scenario_id)
        view = scenario_view(scenario)
    except ScenarioError as error:
        _error(error)
    response["ETag"] = _etag(view["version"])
    return view


@router.patch(
    "/scenarios/{scenario_id}",
    auth=django_auth,
    response=with_problem_responses(ScenarioView),
)
def scenario_patch(
    request: HttpRequest,
    response: HttpResponse,
    scenario_id: UUID,
    payload: ScenarioPatchPayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        scenario = update_scenario(
            request.auth,
            scenario_id,
            changes=payload.model_dump(exclude_unset=True),
            expected_version=require_if_match(if_match),
        )
        view = scenario_view(scenario)
    except ScenarioError as error:
        _error(error)
    response["ETag"] = _etag(view["version"])
    return view


@router.post(
    "/scenarios/{scenario_id}/duplicate",
    auth=django_auth,
    response=with_problem_responses({201: ScenarioView}),
)
def scenario_duplicate(
    request: HttpRequest,
    response: HttpResponse,
    scenario_id: UUID,
    payload: DuplicateScenarioPayload,
) -> Status[dict[str, Any]]:
    try:
        scenario = duplicate_scenario(request.auth, scenario_id, name=payload.name)
        view = scenario_view(scenario)
    except ScenarioError as error:
        _error(error)
    response["ETag"] = _etag(view["version"])
    return Status(201, view)


@router.post(
    "/scenarios/{scenario_id}/archive",
    auth=django_auth,
    response=with_problem_responses(ScenarioView),
)
def scenario_archive(
    request: HttpRequest,
    response: HttpResponse,
    scenario_id: UUID,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        scenario = update_scenario(
            request.auth,
            scenario_id,
            changes={"status": "ARCHIVED"},
            expected_version=require_if_match(if_match),
        )
        view = scenario_view(scenario)
    except ScenarioError as error:
        _error(error)
    response["ETag"] = _etag(view["version"])
    return view


@router.post(
    "/scenarios/{scenario_id}/courses",
    auth=django_auth,
    response=with_problem_responses(ScenarioView),
)
def planned_course_create(
    request: HttpRequest,
    response: HttpResponse,
    scenario_id: UUID,
    payload: PlannedCourseCreatePayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        scenario = add_planned_course(
            request.auth,
            scenario_id,
            course_version_id=payload.course_version_id,
            term_id=payload.term_id,
            section_id=payload.section_id,
            priority=payload.priority,
            notes=payload.notes,
            expected_version=if_match.strip('"') if if_match else None,
        )
        view = scenario_view(scenario)
    except ScenarioError as error:
        _error(error)
    response["ETag"] = _etag(view["version"])
    return view


@router.patch(
    "/scenarios/{scenario_id}/courses/{planned_course_id}",
    auth=django_auth,
    response=with_problem_responses(ScenarioView),
)
def planned_course_patch(
    request: HttpRequest,
    response: HttpResponse,
    scenario_id: UUID,
    planned_course_id: UUID,
    payload: PlannedCoursePatchPayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        scenario = update_planned_course(
            request.auth,
            scenario_id,
            planned_course_id,
            changes=payload.model_dump(exclude_unset=True),
            expected_version=require_if_match(if_match),
        )
        view = scenario_view(scenario)
    except ScenarioError as error:
        _error(error)
    response["ETag"] = _etag(view["version"])
    return view


@router.delete(
    "/scenarios/{scenario_id}/courses/{planned_course_id}",
    auth=django_auth,
    response=with_problem_responses(ScenarioView),
)
def planned_course_delete(
    request: HttpRequest,
    response: HttpResponse,
    scenario_id: UUID,
    planned_course_id: UUID,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        scenario = delete_planned_course(
            request.auth,
            scenario_id,
            planned_course_id,
            expected_version=require_if_match(if_match),
        )
        view = scenario_view(scenario)
    except ScenarioError as error:
        _error(error)
    response["ETag"] = _etag(view["version"])
    return view
