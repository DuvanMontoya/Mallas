from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time
from typing import Any
from uuid import UUID

from django.db.models import ProtectedError, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.security import django_auth

from domain.enums import TermStatus, UserRole
from modules.common.api import raise_problem, with_problem_responses
from modules.governance.models import SourceSnapshot
from modules.identity.application.authorization import has_role
from modules.institutions.models import Campus, Institution
from modules.offerings.application.services import (
    OfferingsError,
    build_offerings,
    build_schedule_evaluation,
)
from modules.offerings.models import AcademicTerm, CourseOffering, Meeting, Section
from modules.student_records.application.history import (
    HistoryMutationError,
    get_enrollment_for_view,
)


class OfferingSourceView(Schema):
    sha256: str | None
    retrieved_at: datetime | None
    freshness: str
    age_seconds: int | None
    max_age_seconds: int | None
    source_name: str | None
    source_url: str | None
    capacity_realtime: bool


class AcademicTermView(Schema):
    id: UUID
    code: str
    institution_id: UUID
    campus_code: str | None
    campus_name: str | None
    starts_at: datetime
    ends_at: datetime
    status: str
    source: OfferingSourceView


class AcademicTermCollectionView(Schema):
    items: list[AcademicTermView]


class AcademicTermCreate(Schema):
    institution_id: UUID
    campus_id: UUID | None = None
    code: str
    starts_at: datetime
    ends_at: datetime
    status: str = TermStatus.PLANNED.value
    source_snapshot_id: UUID | None = None


class AcademicTermPatch(Schema):
    campus_id: UUID | None = None
    code: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str | None = None
    source_snapshot_id: UUID | None = None


class CapacityView(Schema):
    capacity: int | None
    enrolled_count: int | None
    state: str
    note: str


class MeetingView(Schema):
    id: UUID
    day_of_week: int
    starts_at: time
    ends_at: time
    starts_on: date | None
    ends_on: date | None
    session_code: str
    is_alternate: bool
    location: str
    timezone: str


class SectionView(Schema):
    id: UUID
    group_code: str
    modality: str
    capacity: CapacityView
    meetings: list[MeetingView]
    schedulable_state: str


class OfferingView(Schema):
    id: UUID
    course_version_id: UUID
    course_code: str
    course_name: str
    credits: int | None
    term: AcademicTermView
    status: str
    offered_state: str
    eligibility_state: str
    eligibility_reasons: list[dict[str, Any]]
    schedulable_state: str
    sections: list[SectionView]
    source: OfferingSourceView
    href: str


class OfferingsView(Schema):
    terms: list[AcademicTermView]
    offerings: list[OfferingView]
    selected_term_code: str | None
    enrollment_id: UUID | None
    warnings: list[str]


class ScheduleConflictView(Schema):
    left_section_id: str
    right_section_id: str
    left_meeting_id: str
    right_meeting_id: str
    occurrence_date: date
    starts_at_utc: datetime
    ends_at_utc: datetime
    reason: str


class ScheduleEvaluationView(Schema):
    term_code: str
    section_ids: list[UUID]
    state: str
    unknown_reasons: list[str]
    conflicts: list[ScheduleConflictView]


class MessageView(Schema):
    detail: str


router = Router(tags=["Offerings"])


def _term_dict(term: AcademicTerm) -> dict[str, Any]:
    from modules.offerings.application.services import _term_view

    return _term_view(term)


def _manage_offerings(request: HttpRequest, institution_id: UUID) -> Any:
    actor = getattr(request, "auth", None) or getattr(request, "user", None)
    if any(
        has_role(actor, role, institution_id=institution_id)
        for role in (UserRole.ADMIN, UserRole.EDITOR, UserRole.REVIEWER)
    ):
        return actor
    raise_problem(
        status=403,
        code="OFFERINGS_FORBIDDEN",
        title="Offerings administration forbidden",
        detail="You are not allowed to administer offerings for this institution.",
    )


def _etag(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, default=str, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@router.get(
    "/academic-terms",
    response=with_problem_responses(AcademicTermCollectionView),
)
def academic_terms(
    request: HttpRequest,
    response: HttpResponse,
    institution_id: UUID | None = None,
    campus_code: str | None = None,
    enrollment_id: UUID | None = None,
) -> dict[str, Any]:
    query = AcademicTerm.objects.select_related("campus", "source_snapshot__document").order_by(
        "-starts_at", "code"
    )
    if enrollment_id is not None:
        actor = getattr(request, "auth", None) or getattr(request, "user", None)
        try:
            enrollment = get_enrollment_for_view(actor, enrollment_id)
        except HistoryMutationError as error:
            raise_problem(
                status=403 if error.code == "history_forbidden" else 404,
                code=error.code.upper(),
                title="Academic terms unavailable",
                detail=str(error),
            )
        scoped_institution_id = enrollment.student.institution_id
        scoped_campus = enrollment.program.faculty.campus
        if institution_id is not None and institution_id != scoped_institution_id:
            raise_problem(
                status=400,
                code="TERM_SCOPE_MISMATCH",
                title="Academic term scope mismatch",
                detail="institution_id must match the authorized enrollment institution.",
            )
        if campus_code and campus_code != scoped_campus.code:
            raise_problem(
                status=400,
                code="TERM_SCOPE_MISMATCH",
                title="Academic term scope mismatch",
                detail="campus_code must match the authorized enrollment campus.",
            )
        query = query.filter(institution_id=scoped_institution_id).filter(
            Q(campus_id=scoped_campus.pk) | Q(campus__isnull=True)
        )
        response["Cache-Control"] = "private, no-store"
        institution_id = None
        campus_code = None
    if institution_id is not None:
        query = query.filter(institution_id=institution_id)
    if campus_code:
        query = query.filter(campus__code=campus_code)
    items = [_term_dict(term) for term in query[:100]]
    response["ETag"] = f'"{_etag(items)}"'
    return {"items": items}


@router.get(
    "/academic-terms/{term_id}",
    response=with_problem_responses(AcademicTermView),
)
def academic_term_detail(
    request: HttpRequest,
    response: HttpResponse,
    term_id: UUID,
) -> dict[str, Any]:
    del request
    term = get_object_or_404(
        AcademicTerm.objects.select_related("campus", "source_snapshot__document"), pk=term_id
    )
    payload = _term_dict(term)
    response["ETag"] = f'"{_etag(payload)}"'
    return payload


@router.post(
    "/academic-terms",
    auth=django_auth,
    response=with_problem_responses({201: AcademicTermView}),
)
def academic_term_create(
    request: HttpRequest,
    payload: AcademicTermCreate,
    response: HttpResponse,
) -> Status[dict[str, Any]]:
    _manage_offerings(request, payload.institution_id)
    institution = get_object_or_404(Institution, pk=payload.institution_id)
    campus = None
    if payload.campus_id is not None:
        campus = get_object_or_404(Campus, pk=payload.campus_id)
        if campus.institution_id != institution.pk:
            raise_problem(
                status=422,
                code="CAMPUS_INSTITUTION_MISMATCH",
                title="Invalid campus",
                detail="Campus must belong to the selected institution.",
            )
    source_snapshot = None
    if payload.source_snapshot_id is not None:
        source_snapshot = get_object_or_404(SourceSnapshot, pk=payload.source_snapshot_id)
    term = AcademicTerm(
        institution=institution,
        campus=campus,
        code=payload.code.strip(),
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        status=payload.status.upper(),
        source_snapshot=source_snapshot,
    )
    term.full_clean()
    term.save()
    return Status(201, _term_dict(term))


@router.patch(
    "/academic-terms/{term_id}",
    auth=django_auth,
    response=with_problem_responses(AcademicTermView),
)
def academic_term_patch(
    request: HttpRequest,
    response: HttpResponse,
    term_id: UUID,
    payload: AcademicTermPatch,
) -> dict[str, Any]:
    term = get_object_or_404(AcademicTerm, pk=term_id)
    _manage_offerings(request, term.institution_id)
    changes = payload.model_dump(exclude_unset=True)
    if "campus_id" in changes:
        campus_id = changes.pop("campus_id")
        term.campus = get_object_or_404(Campus, pk=campus_id) if campus_id else None
        if term.campus and term.campus.institution_id != term.institution_id:
            raise_problem(
                status=422,
                code="CAMPUS_INSTITUTION_MISMATCH",
                title="Invalid campus",
                detail="Campus must belong to the term institution.",
            )
    if "source_snapshot_id" in changes:
        snapshot_id = changes.pop("source_snapshot_id")
        term.source_snapshot = (
            get_object_or_404(SourceSnapshot, pk=snapshot_id) if snapshot_id else None
        )
    for field, value in changes.items():
        if value is not None or field in {"code", "status"}:
            setattr(term, field, value.upper() if field == "status" else value)
    term.full_clean()
    term.save()
    payload_view = _term_dict(
        AcademicTerm.objects.select_related("campus", "source_snapshot__document").get(pk=term.pk)
    )
    response["ETag"] = f'"{_etag(payload_view)}"'
    return payload_view


@router.delete(
    "/academic-terms/{term_id}",
    auth=django_auth,
    response=with_problem_responses(MessageView),
)
def academic_term_delete(request: HttpRequest, term_id: UUID) -> dict[str, str]:
    term = get_object_or_404(AcademicTerm, pk=term_id)
    actor = _manage_offerings(request, term.institution_id)
    if not has_role(actor, UserRole.ADMIN, institution_id=term.institution_id):
        raise_problem(
            status=403,
            code="TERM_DELETE_FORBIDDEN",
            title="Term deletion forbidden",
            detail="Only an administrator may delete an academic term.",
        )
    try:
        term.delete()
    except ProtectedError:
        raise_problem(
            status=409,
            code="TERM_IN_USE",
            title="Academic term is in use",
            detail="An academic term with offerings or records cannot be deleted.",
        )
    return {"detail": "Academic term deleted."}


@router.get(
    "/offerings",
    response=with_problem_responses(OfferingsView),
)
def offerings(
    request: HttpRequest,
    response: HttpResponse,
    term_code: str | None = None,
    course_code: str | None = None,
    status: str | None = None,
    enrollment_id: UUID | None = None,
) -> dict[str, Any]:
    actor = getattr(request, "auth", None) or getattr(request, "user", None)
    try:
        payload = build_offerings(
            actor,
            term_code=term_code,
            course_code=course_code,
            status=status,
            enrollment_id=enrollment_id,
        )
    except OfferingsError as error:
        status_code = (
            403
            if error.code.endswith("forbidden")
            else 404
            if error.code == "term_not_found"
            else 400
        )
        raise_problem(
            status=status_code,
            code=error.code.upper(),
            title="Offerings unavailable",
            detail=str(error),
        )
    response["ETag"] = f'"{_etag(payload)}"'
    return payload


@router.get(
    "/offerings/schedule",
    response=with_problem_responses(ScheduleEvaluationView),
)
def offering_schedule(
    request: HttpRequest,
    response: HttpResponse,
    term_code: str,
    section_ids: str,
) -> dict[str, Any]:
    del request
    try:
        ids = [UUID(value.strip()) for value in section_ids.split(",") if value.strip()]
    except ValueError:
        raise_problem(
            status=400,
            code="SECTION_IDS_INVALID",
            title="Invalid section ids",
            detail="section_ids must be a comma-separated list of UUIDs.",
        )
    try:
        payload = build_schedule_evaluation(term_code=term_code, section_ids=ids)
    except OfferingsError as error:
        raise_problem(
            status=409 if error.code == "section_term_mismatch" else 404,
            code=error.code.upper(),
            title="Schedule unavailable",
            detail=str(error),
        )
    response["ETag"] = f'"{_etag(payload)}"'
    return payload


@router.get(
    "/offerings/{offering_id}",
    response=with_problem_responses(OfferingView),
)
def offering_detail(
    request: HttpRequest,
    response: HttpResponse,
    offering_id: UUID,
) -> dict[str, Any]:
    actor = getattr(request, "auth", None) or getattr(request, "user", None)
    offering = get_object_or_404(CourseOffering, pk=offering_id)
    payload = build_offerings(
        actor, term_code=offering.term.code, course_code=offering.course_version.course.code
    )
    item = next((item for item in payload["offerings"] if item["id"] == offering.pk), None)
    if item is None:
        raise_problem(
            status=404,
            code="OFFERING_NOT_FOUND",
            title="Offering not found",
            detail="The requested offering does not exist.",
        )
    response["ETag"] = f'"{_etag(item)}"'
    return item


@router.get(
    "/sections/{section_id}",
    response=with_problem_responses(SectionView),
)
def section_detail(request: HttpRequest, section_id: UUID) -> dict[str, Any]:
    del request
    section = get_object_or_404(Section.objects.prefetch_related("meetings"), pk=section_id)
    source = {
        "capacity_realtime": bool(
            section.offering.metadata.get("capacity_realtime", False)
            if isinstance(section.offering.metadata, dict)
            else False
        )
    }
    from modules.offerings.application.services import _capacity_view, _meeting_view

    return {
        "id": section.pk,
        "group_code": section.group_code,
        "modality": section.modality,
        "capacity": _capacity_view(section, source),
        "meetings": [_meeting_view(meeting) for meeting in section.meetings.all()],
        "schedulable_state": "NOT_EVALUATED",
    }


@router.get(
    "/meetings/{meeting_id}",
    response=with_problem_responses(MeetingView),
)
def meeting_detail(request: HttpRequest, meeting_id: UUID) -> dict[str, Any]:
    del request
    meeting = get_object_or_404(Meeting, pk=meeting_id)
    from modules.offerings.application.services import _meeting_view

    return _meeting_view(meeting)
