from __future__ import annotations

from typing import Any, NoReturn
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from ninja import Header, Router, Schema
from ninja.security import django_auth

from modules.common.api import raise_problem, with_problem_responses
from modules.student_records.application.onboarding import (
    StudentOnboardingError,
    onboarding_view,
    update_onboarding,
)

router = Router(tags=["Student onboarding"])


class StudentOnboardingView(Schema):
    enrollment_id: UUID
    program_name: str
    program_code: str
    admission_term_code: str
    enrollment_status: str
    plan_code: str | None
    revision_code: str | None
    assignment_reason_codes: list[str]
    identity_confirmed: bool
    history_step_status: str
    current_term_id: UUID | None
    planning_load_target: int | None
    tour_status: str
    completed: bool
    version: str


class StudentOnboardingPayload(Schema):
    identity_confirmed: bool
    history_step_status: str
    current_term_id: UUID
    planning_load_target: int
    tour_status: str
    complete: bool = False


def _error(error: StudentOnboardingError) -> NoReturn:
    status = (
        428
        if error.code == "onboarding_precondition_required"
        else 409
        if error.code in {"onboarding_stale_resource", "onboarding_already_complete"}
        else 422
    )
    raise_problem(
        status=status,
        code=error.code.upper(),
        title="Student onboarding request failed",
        detail=str(error),
    )


@router.get("", auth=django_auth, response=with_problem_responses(StudentOnboardingView))
def get_onboarding(request: HttpRequest, response: HttpResponse) -> dict[str, Any]:
    try:
        result = onboarding_view(request.auth)
    except StudentOnboardingError as error:
        _error(error)
    response["Cache-Control"] = "private, no-store"
    return result


@router.patch("", auth=django_auth, response=with_problem_responses(StudentOnboardingView))
def patch_onboarding(
    request: HttpRequest,
    response: HttpResponse,
    payload: StudentOnboardingPayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        result = update_onboarding(
            user=request.auth,
            expected_version=if_match,
            request=request,
            **payload.model_dump(),
        )
    except StudentOnboardingError as error:
        _error(error)
    response["Cache-Control"] = "private, no-store"
    return result
