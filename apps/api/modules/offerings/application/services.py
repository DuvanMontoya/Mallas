from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any
from uuid import UUID

from django.db.models import Prefetch, QuerySet

from domain.offerings.freshness import assess_freshness
from domain.offerings.schedule import MeetingWindow, evaluate_schedule
from modules.audit.application.overview import AcademicOverviewError, build_academic_overview
from modules.offerings.models import AcademicTerm, CourseOffering, Meeting, Section

OFFERING_MAX_AGE = timedelta(hours=24)


class OfferingsError(RuntimeError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _source_view(snapshot: Any | None) -> dict[str, Any]:
    if snapshot is None:
        freshness = assess_freshness(None, max_age=OFFERING_MAX_AGE)
        return {
            "sha256": None,
            "retrieved_at": None,
            "freshness": freshness.state,
            "age_seconds": freshness.age_seconds,
            "max_age_seconds": freshness.max_age_seconds,
            "source_name": None,
            "source_url": None,
            "capacity_realtime": False,
        }
    freshness = assess_freshness(snapshot.captured_at, max_age=OFFERING_MAX_AGE)
    metadata = snapshot.metadata if isinstance(snapshot.metadata, Mapping) else {}
    document = snapshot.document
    return {
        "sha256": snapshot.sha256,
        "retrieved_at": snapshot.captured_at,
        "freshness": freshness.state,
        "age_seconds": freshness.age_seconds,
        "max_age_seconds": freshness.max_age_seconds,
        "source_name": document.title,
        "source_url": snapshot.source_url or document.canonical_url or None,
        "capacity_realtime": bool(metadata.get("capacity_realtime", False)),
    }


def _term_view(term: AcademicTerm) -> dict[str, Any]:
    return {
        "id": term.pk,
        "code": term.code,
        "institution_id": term.institution_id,
        "campus_code": term.campus.code if term.campus else None,
        "campus_name": term.campus.name if term.campus else None,
        "starts_at": term.starts_at,
        "ends_at": term.ends_at,
        "status": term.status,
        "source": _source_view(term.source_snapshot),
    }


def _capacity_view(section: Section, source: Mapping[str, Any]) -> dict[str, Any]:
    if section.capacity is None and section.enrolled_count is None:
        state = "UNKNOWN"
    elif bool(source.get("capacity_realtime", False)):
        state = "REAL_TIME"
    else:
        state = "REPORTED_NOT_REAL_TIME"
    return {
        "capacity": section.capacity,
        "enrolled_count": section.enrolled_count,
        "state": state,
        "note": (
            "No se afirma cupo disponible en tiempo real."
            if state != "REAL_TIME"
            else "La fuente declaró un dato de cupo en tiempo real."
        ),
    }


def _meeting_view(meeting: Meeting) -> dict[str, Any]:
    return {
        "id": meeting.pk,
        "day_of_week": meeting.day_of_week,
        "starts_at": meeting.starts_at,
        "ends_at": meeting.ends_at,
        "starts_on": meeting.starts_on,
        "ends_on": meeting.ends_on,
        "session_code": meeting.session_code,
        "is_alternate": meeting.is_alternate,
        "location": meeting.location,
        "timezone": meeting.timezone,
    }


def _eligibility_map(actor: Any, enrollment_id: UUID | None) -> dict[str, dict[str, Any]]:
    if enrollment_id is None:
        return {}
    try:
        overview = build_academic_overview(actor, enrollment_id=enrollment_id)
    except AcademicOverviewError as exc:
        raise OfferingsError(str(exc), code=exc.code) from exc
    result: dict[str, dict[str, Any]] = {}
    for item in overview.get("course_options", []):
        if not isinstance(item, Mapping):
            continue
        code = item.get("code")
        if isinstance(code, str) and code:
            result[code] = {str(key): value for key, value in item.items()}
    return result


def _offering_query(*, term_code: str | None, course_code: str | None) -> QuerySet[CourseOffering]:
    query = CourseOffering.objects.select_related(
        "course_version__course",
        "term__campus",
        "term__source_snapshot__document",
        "source_snapshot__document",
    ).prefetch_related(
        Prefetch(
            "sections", queryset=Section.objects.prefetch_related("meetings").order_by("group_code")
        )
    )
    if term_code:
        query = query.filter(term__code=term_code)
    if course_code:
        query = query.filter(course_version__course__code=course_code)
    return query.order_by("term__starts_at", "course_version__course__code")


def build_offerings(
    actor: Any,
    *,
    term_code: str | None = None,
    course_code: str | None = None,
    status: str | None = None,
    enrollment_id: UUID | None = None,
) -> dict[str, Any]:
    terms_query = AcademicTerm.objects.select_related(
        "campus", "source_snapshot__document"
    ).order_by("-starts_at", "code")
    if term_code:
        terms_query = terms_query.filter(code=term_code)
        if not terms_query.exists():
            raise OfferingsError("The academic term was not found.", code="term_not_found")
    terms = list(terms_query[:50])
    query = _offering_query(term_code=term_code, course_code=course_code)
    if status:
        query = query.filter(status=status.upper())
    eligibility = _eligibility_map(actor, enrollment_id)
    offering_views: list[dict[str, Any]] = []
    for offering in query:
        source = _source_view(offering.source_snapshot or offering.term.source_snapshot)
        code = offering.course_version.course.code
        academic = eligibility.get(code)
        sections = []
        for section in offering.sections.all():
            sections.append(
                {
                    "id": section.pk,
                    "group_code": section.group_code,
                    "modality": section.modality,
                    "capacity": _capacity_view(section, source),
                    "meetings": [_meeting_view(meeting) for meeting in section.meetings.all()],
                    "schedulable_state": "NOT_EVALUATED",
                }
            )
        offering_views.append(
            {
                "id": offering.pk,
                "course_version_id": offering.course_version_id,
                "course_code": code,
                "course_name": offering.course_version.name,
                "credits": offering.course_version.credits,
                "term": _term_view(offering.term),
                "status": offering.status,
                "offered_state": "NOT_OFFERED" if offering.status == "CANCELLED" else "OFFERED",
                "eligibility_state": str(academic.get("eligibility", "NOT_ASSESSED"))
                if academic
                else "NOT_ASSESSED",
                "eligibility_reasons": list(academic.get("reasons", [])) if academic else [],
                "schedulable_state": "NOT_EVALUATED",
                "sections": sections,
                "source": source,
                "href": f"/offerings?term={offering.term.code}&course={code}",
            }
        )
    return {
        "terms": [_term_view(term) for term in terms],
        "offerings": offering_views,
        "selected_term_code": term_code,
        "enrollment_id": enrollment_id,
        "warnings": [
            "ELIGIBILITY_NOT_ASSESSED"
            if enrollment_id is None
            else "ELIGIBILITY_FROM_ACADEMIC_OVERVIEW",
            "CAPACITY_NOT_REAL_TIME",
        ],
    }


def build_schedule_evaluation(
    *,
    term_code: str,
    section_ids: list[UUID],
) -> dict[str, Any]:
    term = AcademicTerm.objects.select_related("campus").filter(code=term_code).first()
    if term is None:
        raise OfferingsError("The academic term was not found.", code="term_not_found")
    sections = list(
        Section.objects.filter(id__in=section_ids, offering__term=term)
        .prefetch_related("meetings")
        .select_related("offering")
        .order_by("offering__course_version__course__code", "group_code")
    )
    if len(sections) != len(set(section_ids)):
        raise OfferingsError(
            "Every selected section must belong to the selected academic term.",
            code="section_term_mismatch",
        )
    windows = [
        MeetingWindow(
            meeting_id=str(meeting.pk),
            section_id=str(section.pk),
            day_of_week=meeting.day_of_week,
            starts_at=meeting.starts_at,
            ends_at=meeting.ends_at,
            timezone=meeting.timezone,
            starts_on=meeting.starts_on,
            ends_on=meeting.ends_on,
            session_code=meeting.session_code,
            is_alternate=meeting.is_alternate,
        )
        for section in sections
        for meeting in section.meetings.all()
    ]
    evaluation = evaluate_schedule(
        windows,
        term_start=term.starts_at.date(),
        term_end=term.ends_at.date(),
    )
    return {
        "term_code": term.code,
        "section_ids": [section.pk for section in sections],
        "state": evaluation.state,
        "unknown_reasons": list(evaluation.unknown_reasons),
        "conflicts": [
            {
                "left_section_id": conflict.left_section_id,
                "right_section_id": conflict.right_section_id,
                "left_meeting_id": conflict.left_meeting_id,
                "right_meeting_id": conflict.right_meeting_id,
                "occurrence_date": conflict.occurrence_date,
                "starts_at_utc": conflict.starts_at_utc,
                "ends_at_utc": conflict.ends_at_utc,
                "reason": conflict.reason,
            }
            for conflict in evaluation.conflicts
        ],
    }
