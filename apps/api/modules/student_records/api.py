from __future__ import annotations

from datetime import datetime
from typing import Any, NoReturn
from uuid import UUID

from django.core import signing
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from ninja import Header, Router, Schema
from ninja.security import django_auth

from domain.enums import AttemptStatus
from modules.common.api import raise_problem, require_if_match, with_problem_responses
from modules.student_records.application.history import (
    HistoryMutationError,
    annul_attempt,
    create_manual_attempt,
    get_attempt_for_view,
    get_enrollment_for_view,
    update_attempt,
)
from modules.student_records.models import CourseAttempt

router = Router(tags=["Student records"])


class ManualAttemptPayload(Schema):
    enrollment_id: UUID
    course_version_id: UUID | None = None
    course_code: str = ""
    term_id: UUID | None = None
    term_code: str = ""
    status: str
    grade: str | float | int | None = None
    credits_earned: int | None = None
    attempt_number: int | None = None
    notes: str = ""


class AttemptPatchPayload(Schema):
    status: str | None = None
    grade: str | float | int | None = None
    credits_earned: int | None = None
    notes: str | None = None
    course_version_id: UUID | None = None
    term_id: UUID | None = None


class AttemptView(Schema):
    id: UUID
    enrollment_id: UUID
    course_version_id: UUID
    course_code: str
    course_name: str
    term_id: UUID
    term_code: str
    attempt_number: int
    status: str
    grade: str | None
    credits_earned: int
    origin: str
    import_batch_id: UUID | None
    notes: str
    audit_run_id: UUID | None = None
    version: str


class AttemptPage(Schema):
    items: list[AttemptView]
    total: int
    limit: int
    offset: int
    next_offset: int | None
    previous_offset: int | None
    next_cursor: str | None = None


_HISTORY_CURSOR_SALT = "curriculum-navigator.history-attempts.v1"


def _cursor_values(attempt: CourseAttempt, sort: str) -> list[str | int]:
    common = {
        "term": [
            attempt.term.starts_at.isoformat(),
            attempt.course_version.course.code,
            attempt.attempt_number,
            str(attempt.pk),
        ],
        "course": [
            attempt.course_version.course.code,
            attempt.term.starts_at.isoformat(),
            attempt.attempt_number,
            str(attempt.pk),
        ],
        "status": [
            attempt.status,
            attempt.term.starts_at.isoformat(),
            attempt.course_version.course.code,
            str(attempt.pk),
        ],
    }
    return common[sort]


def _encode_attempt_cursor(
    attempt: CourseAttempt,
    *,
    enrollment_id: UUID,
    sort: str,
    status: str | None,
    snapshot_at: datetime,
) -> str:
    return signing.dumps(
        {
            "enrollment_id": str(enrollment_id),
            "sort": sort,
            "status": status,
            "snapshot_at": snapshot_at.isoformat(),
            "values": _cursor_values(attempt, sort),
        },
        salt=_HISTORY_CURSOR_SALT,
        compress=True,
    )


def _decode_attempt_cursor(
    cursor: str,
    *,
    enrollment_id: UUID,
    sort: str,
    status: str | None,
) -> tuple[datetime, list[str | int]]:
    try:
        payload = signing.loads(cursor, salt=_HISTORY_CURSOR_SALT)
        if (
            not isinstance(payload, dict)
            or payload.get("enrollment_id") != str(enrollment_id)
            or payload.get("sort") != sort
            or payload.get("status") != status
            or not isinstance(payload.get("values"), list)
        ):
            raise ValueError
        snapshot_at = datetime.fromisoformat(str(payload["snapshot_at"]))
        if timezone.is_naive(snapshot_at):
            raise ValueError
        values = payload["values"]
        if len(values) != 4:
            raise ValueError
        return snapshot_at, values
    except KeyError, TypeError, ValueError, signing.BadSignature:
        raise_problem(
            status=400,
            code="HISTORY_CURSOR_INVALID",
            title="Invalid history cursor",
            detail="The history cursor is invalid or does not match this query.",
            fields={"cursor": "Restart pagination without a cursor."},
        )


def _after_attempt_cursor(
    attempts: QuerySet[CourseAttempt], sort: str, values: list[str | int]
) -> QuerySet[CourseAttempt]:
    if sort == "term":
        term_start, course_code, attempt_number, attempt_id = values
        return attempts.filter(
            Q(term__starts_at__gt=datetime.fromisoformat(str(term_start)))
            | Q(
                term__starts_at=datetime.fromisoformat(str(term_start)),
                course_version__course__code__gt=str(course_code),
            )
            | Q(
                term__starts_at=datetime.fromisoformat(str(term_start)),
                course_version__course__code=str(course_code),
                attempt_number__gt=int(attempt_number),
            )
            | Q(
                term__starts_at=datetime.fromisoformat(str(term_start)),
                course_version__course__code=str(course_code),
                attempt_number=int(attempt_number),
                id__gt=UUID(str(attempt_id)),
            )
        )
    if sort == "course":
        course_code, term_start, attempt_number, attempt_id = values
        return attempts.filter(
            Q(course_version__course__code__gt=str(course_code))
            | Q(
                course_version__course__code=str(course_code),
                term__starts_at__gt=datetime.fromisoformat(str(term_start)),
            )
            | Q(
                course_version__course__code=str(course_code),
                term__starts_at=datetime.fromisoformat(str(term_start)),
                attempt_number__gt=int(attempt_number),
            )
            | Q(
                course_version__course__code=str(course_code),
                term__starts_at=datetime.fromisoformat(str(term_start)),
                attempt_number=int(attempt_number),
                id__gt=UUID(str(attempt_id)),
            )
        )
    attempt_status, term_start, course_code, attempt_id = values
    return attempts.filter(
        Q(status__gt=str(attempt_status))
        | Q(status=str(attempt_status), term__starts_at__gt=datetime.fromisoformat(str(term_start)))
        | Q(
            status=str(attempt_status),
            term__starts_at=datetime.fromisoformat(str(term_start)),
            course_version__course__code__gt=str(course_code),
        )
        | Q(
            status=str(attempt_status),
            term__starts_at=datetime.fromisoformat(str(term_start)),
            course_version__course__code=str(course_code),
            id__gt=UUID(str(attempt_id)),
        )
    )


def _error(error: HistoryMutationError) -> NoReturn:
    status = (
        403
        if error.code == "history_forbidden"
        else 404
        if error.code.endswith("_not_found")
        else 409
        if error.code in {"attempt_duplicate", "stale_resource"}
        else 400
    )
    raise_problem(
        status=status,
        code=error.code.upper(),
        title="Request cannot be completed",
        detail=str(error),
    )


def _attempt_view(attempt: CourseAttempt, audit_run_id: UUID | None = None) -> dict[str, Any]:
    return {
        "id": attempt.pk,
        "enrollment_id": attempt.enrollment_id,
        "course_version_id": attempt.course_version_id,
        "course_code": attempt.course_version.course.code,
        "course_name": attempt.course_version.name,
        "term_id": attempt.term_id,
        "term_code": attempt.term.code,
        "attempt_number": attempt.attempt_number,
        "status": attempt.status,
        "grade": str(attempt.grade) if attempt.grade is not None else None,
        "credits_earned": attempt.credits_earned,
        "origin": attempt.origin,
        "import_batch_id": attempt.import_batch_id,
        "notes": attempt.notes,
        "audit_run_id": audit_run_id,
        "version": attempt.updated_at.isoformat(),
    }


@router.get("/attempts", auth=django_auth, response=with_problem_responses(AttemptPage))
def list_history_attempts(
    request: HttpRequest,
    enrollment_id: UUID,
    limit: int = 50,
    offset: int = 0,
    cursor: str | None = None,
    status: str | None = None,
    sort: str = "term",
) -> dict[str, Any]:
    if limit < 1 or limit > 100:
        raise_problem(
            status=400,
            code="PAGINATION_LIMIT_INVALID",
            title="Invalid page size",
            detail="limit must be between 1 and 100.",
            fields={"limit": "Use a value between 1 and 100."},
        )
    if offset < 0:
        raise_problem(
            status=400,
            code="PAGINATION_OFFSET_INVALID",
            title="Invalid page offset",
            detail="offset must be zero or greater.",
            fields={"offset": "Use a non-negative integer."},
        )
    if cursor and offset:
        raise_problem(
            status=400,
            code="PAGINATION_MODE_INVALID",
            title="Invalid pagination mode",
            detail="Use cursor pagination or a legacy offset, not both.",
            fields={"offset": "Set offset to zero when cursor is present."},
        )
    ordering = {
        "term": ("term__starts_at", "course_version__course__code", "attempt_number", "id"),
        "course": ("course_version__course__code", "term__starts_at", "attempt_number", "id"),
        "status": ("status", "term__starts_at", "course_version__course__code", "id"),
    }.get(sort)
    if ordering is None:
        raise_problem(
            status=400,
            code="SORT_INVALID",
            title="Invalid sort",
            detail="sort must be one of term, course or status.",
            fields={"sort": ["term", "course", "status"]},
        )
    normalized_status = status.upper() if status else None
    if normalized_status is not None and normalized_status not in {
        member.value for member in AttemptStatus
    }:
        raise_problem(
            status=400,
            code="STATUS_FILTER_INVALID",
            title="Invalid status filter",
            detail="status is not a supported academic attempt status.",
            fields={"status": normalized_status},
        )
    try:
        enrollment = get_enrollment_for_view(request.auth, enrollment_id)
    except HistoryMutationError as error:
        _error(error)
    attempts = enrollment.course_attempts.select_related(
        "course_version__course", "term", "import_batch"
    )
    if normalized_status is not None:
        attempts = attempts.filter(status=normalized_status)
    if cursor:
        snapshot_at, cursor_values = _decode_attempt_cursor(
            cursor,
            enrollment_id=enrollment.pk,
            sort=sort,
            status=normalized_status,
        )
    else:
        snapshot_at = timezone.now()
        cursor_values = None
    snapshot_attempts = attempts.filter(created_at__lte=snapshot_at)
    total = snapshot_attempts.count()
    page_attempts = snapshot_attempts.order_by(*ordering)
    if cursor_values is not None:
        page_attempts = _after_attempt_cursor(page_attempts, sort, cursor_values)
    start = offset if not cursor else 0
    page_rows = list(page_attempts[start : start + limit + 1])
    has_more = len(page_rows) > limit
    rows = page_rows[:limit]
    next_cursor = (
        _encode_attempt_cursor(
            rows[-1],
            enrollment_id=enrollment.pk,
            sort=sort,
            status=normalized_status,
            snapshot_at=snapshot_at,
        )
        if has_more and rows
        else None
    )
    next_offset = offset + limit if not cursor and offset + limit < total else None
    previous_offset = max(0, offset - limit) if offset > 0 else None
    return {
        "items": [_attempt_view(attempt) for attempt in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "next_offset": next_offset,
        "previous_offset": previous_offset,
        "next_cursor": next_cursor,
    }


@router.post("/attempts", auth=django_auth, response=with_problem_responses(AttemptView))
def create_attempt(
    request: HttpRequest, response: HttpResponse, payload: ManualAttemptPayload
) -> dict[str, Any]:
    try:
        attempt, audit_run_id = create_manual_attempt(
            actor=request.auth,
            enrollment_id=payload.enrollment_id,
            course_version_id=payload.course_version_id,
            course_code=payload.course_code,
            term_id=payload.term_id,
            term_code=payload.term_code,
            status=payload.status,
            grade=payload.grade,
            credits_earned=payload.credits_earned,
            attempt_number=payload.attempt_number,
            notes=payload.notes,
            request=request,
        )
    except HistoryMutationError as error:
        _error(error)
    attempt = get_attempt_for_view(request.auth, attempt.pk)
    view = _attempt_view(attempt, UUID(audit_run_id))
    response["ETag"] = f'"{view["version"]}"'
    return view


@router.patch(
    "/attempts/{attempt_id}", auth=django_auth, response=with_problem_responses(AttemptView)
)
def patch_attempt(
    request: HttpRequest,
    response: HttpResponse,
    attempt_id: UUID,
    payload: AttemptPatchPayload,
    if_match: str | None = Header(  # type: ignore[type-arg]
        None,
        alias="If-Match",
        description="The attempt version returned by a previous read.",
    ),
) -> dict[str, Any]:
    changes = payload.model_dump(exclude_none=True)
    try:
        attempt, audit_run_id = update_attempt(
            actor=request.auth,
            attempt_id=attempt_id,
            changes=changes,
            expected_version=require_if_match(if_match),
            request=request,
        )
    except HistoryMutationError as error:
        _error(error)
    attempt = get_attempt_for_view(request.auth, attempt.pk)
    view = _attempt_view(attempt, UUID(audit_run_id))
    response["ETag"] = f'"{view["version"]}"'
    return view


@router.delete(
    "/attempts/{attempt_id}", auth=django_auth, response=with_problem_responses(AttemptView)
)
def delete_attempt(
    request: HttpRequest,
    response: HttpResponse,
    attempt_id: UUID,
    if_match: str | None = Header(  # type: ignore[type-arg]
        None,
        alias="If-Match",
        description="The attempt version returned by a previous read.",
    ),
) -> dict[str, Any]:
    try:
        attempt, audit_run_id = annul_attempt(
            actor=request.auth,
            attempt_id=attempt_id,
            expected_version=require_if_match(if_match),
            request=request,
        )
    except HistoryMutationError as error:
        _error(error)
    attempt = get_attempt_for_view(request.auth, attempt.pk)
    view = _attempt_view(attempt, UUID(audit_run_id))
    response["ETag"] = f'"{view["version"]}"'
    return view
