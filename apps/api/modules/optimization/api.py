from __future__ import annotations

from datetime import datetime
from typing import Any, NoReturn
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from ninja import Router, Schema, Status
from ninja.security import django_auth

from modules.common.api import raise_problem, with_problem_responses
from modules.optimization.application.runs import (
    MAX_TIME_LIMIT_SECONDS,
    OptimizationRunError,
    cancel_optimization_run,
    create_optimization_run,
    get_optimization_run,
    list_optimization_runs,
    optimization_run_view,
)


class OptimizationRunView(Schema):
    id: UUID
    scenario_id: UUID
    input_hash: str
    output_hash: str
    solver_version: str
    status: str
    objective_values: list[dict[str, Any]]
    solution: dict[str, Any]
    explanation: dict[str, Any]
    time_limit_seconds: int
    created_at: datetime
    started_at: datetime | None
    cancel_requested_at: datetime | None
    completed_at: datetime | None


class OptimizationRunCollectionView(Schema):
    items: list[OptimizationRunView]


class OptimizationRequestPayload(Schema):
    time_limit_seconds: int = 30
    unknown_offering_policy: str = "ALLOW_UNKNOWN"
    credit_target: int | None = None
    preferred_credits_per_term: int | None = None
    random_seed: int = 0


router = Router(tags=["Optimization"])


def _error(error: OptimizationRunError) -> NoReturn:
    if error.code.endswith("forbidden"):
        status = 403
    elif error.code.endswith("not_found") or error.code in {"optimization_terms_unknown"}:
        status = 404
    elif error.code.endswith("invalid"):
        status = 400
    else:
        status = 409
    raise_problem(
        status=status,
        code=error.code.upper(),
        title="Optimization request cannot be completed",
        detail=str(error),
    )


def _view_with_etag(response: HttpResponse, run: Any) -> dict[str, Any]:
    view = optimization_run_view(run)
    response["ETag"] = f'"{view["output_hash"] or view["input_hash"]}"'
    return view


@router.post(
    "/scenarios/{scenario_id}/optimization-runs",
    auth=django_auth,
    response=with_problem_responses({202: OptimizationRunView}),
)
def optimization_create(
    request: HttpRequest,
    response: HttpResponse,
    scenario_id: UUID,
    payload: OptimizationRequestPayload,
) -> Status[dict[str, Any]]:
    if payload.time_limit_seconds > MAX_TIME_LIMIT_SECONDS:
        raise_problem(
            status=400,
            code="OPTIMIZATION_TIME_LIMIT_INVALID",
            title="Optimization request cannot be completed",
            detail=f"El límite máximo es {MAX_TIME_LIMIT_SECONDS} segundos.",
        )
    try:
        run = create_optimization_run(
            request.auth,
            scenario_id,
            time_limit_seconds=payload.time_limit_seconds,
            unknown_offering_policy=payload.unknown_offering_policy,
            credit_target=payload.credit_target,
            preferred_credits_per_term=payload.preferred_credits_per_term,
            random_seed=payload.random_seed,
        )
    except OptimizationRunError as error:
        _error(error)
    return Status(202, _view_with_etag(response, run))


@router.get(
    "/scenarios/{scenario_id}/optimization-runs",
    auth=django_auth,
    response=with_problem_responses(OptimizationRunCollectionView),
)
def optimization_list(
    request: HttpRequest,
    scenario_id: UUID,
) -> dict[str, Any]:
    try:
        return {"items": list_optimization_runs(request.auth, scenario_id)}
    except OptimizationRunError as error:
        _error(error)


@router.get(
    "/optimization-runs/{run_id}",
    auth=django_auth,
    response=with_problem_responses(OptimizationRunView),
)
def optimization_detail(
    request: HttpRequest,
    response: HttpResponse,
    run_id: UUID,
) -> dict[str, Any]:
    try:
        return _view_with_etag(response, get_optimization_run(request.auth, run_id))
    except OptimizationRunError as error:
        _error(error)


@router.post(
    "/optimization-runs/{run_id}/cancel",
    auth=django_auth,
    response=with_problem_responses(OptimizationRunView),
)
def optimization_cancel(
    request: HttpRequest,
    response: HttpResponse,
    run_id: UUID,
) -> dict[str, Any]:
    try:
        return _view_with_etag(response, cancel_optimization_run(request.auth, run_id))
    except OptimizationRunError as error:
        _error(error)
