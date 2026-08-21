from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from django.db import transaction
from django.db.models import Q

from domain.enums import OfferingStatus, SectionModality, SourceStatus, TermStatus
from modules.curriculum.models import CourseVersion
from modules.governance.models import NormativeDocument, SourceSnapshot
from modules.institutions.models import Campus, Institution
from modules.offerings.models import AcademicTerm, CourseOffering, Meeting, Section

OFFICIAL_SIA_COURSE_SEARCH_URL = "https://siabog.unal.edu.co/academia/apoyo-administrativo/"
OFFICIAL_SIA_FAQ_URL = "https://siabog.unal.edu.co/academia/libre-acceso/faq.do"


class OfferingImportError(ValueError):
    """A normalized offering source cannot be safely applied."""


class OfferingSourceUnavailable(OfferingImportError):
    """A source requires an explicit, authorized retrieval step."""


@dataclass(frozen=True)
class SourceDescriptor:
    key: str
    name: str
    url: str
    retrieval_method: str = "PUBLIC_ARCHIVED_PAYLOAD"
    capacity_realtime: bool = False


class OfferingSourceAdapter(Protocol):
    descriptor: SourceDescriptor

    def fetch(self, term_code: str) -> dict[str, Any]:
        """Return a normalized ``offerings/1.0.0`` payload."""


@dataclass(frozen=True)
class StaticJsonOfferingAdapter:
    """Adapter for an explicitly archived JSON export.

    This is intentionally the default integration boundary: it does not log in,
    bypass controls, or scrape an authenticated SIA session.
    """

    payload: dict[str, Any]
    descriptor: SourceDescriptor

    @classmethod
    def from_file(
        cls, path: str | Path, *, descriptor: SourceDescriptor
    ) -> StaticJsonOfferingAdapter:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise OfferingImportError("Offering source file is not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise OfferingImportError("Offering source payload must be an object.")
        return cls(payload=payload, descriptor=descriptor)

    def fetch(self, term_code: str) -> dict[str, Any]:
        payload = dict(self.payload)
        payload.setdefault("term", {})
        if isinstance(payload["term"], dict):
            payload["term"] = {**payload["term"], "code": term_code}
        return payload


@dataclass(frozen=True)
class OfficialSiaPublicAdapter:
    """Reference adapter for UNAL's public SIA course search.

    The public URL is recorded for a human or institutionally approved exporter.
    The product never automates an authenticated/private scrape. Callers must
    pass the resulting archived payload to ``StaticJsonOfferingAdapter``.
    """

    descriptor: SourceDescriptor = SourceDescriptor(
        key="unal.sia.bogota.public-course-search",
        name="UNAL SIA Bogotá — Buscador de cursos público",
        url=OFFICIAL_SIA_COURSE_SEARCH_URL,
    )

    def fetch(self, term_code: str) -> dict[str, Any]:
        raise OfferingSourceUnavailable(
            f"No se automatiza el acceso a SIA. Archive un export autorizado para {term_code}."
        )


@dataclass(frozen=True)
class OfferingImportResult:
    term_id: UUID
    source_snapshot_id: UUID
    source_sha256: str
    term_code: str
    offerings_created: int
    offerings_updated: int
    sections_created: int
    sections_updated: int
    meetings_created: int


def _as_datetime(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise OfferingImportError(f"{field} must be an ISO-8601 datetime.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OfferingImportError(f"{field} must be an ISO-8601 datetime.") from exc
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def _as_date(value: object, *, field: str) -> date | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise OfferingImportError(f"{field} must be an ISO date.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise OfferingImportError(f"{field} must be an ISO date.") from exc


def _as_time(value: object, *, field: str) -> time:
    if not isinstance(value, str):
        raise OfferingImportError(f"{field} must be an HH:MM time.")
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise OfferingImportError(f"{field} must be an HH:MM time.") from exc


def _canonical_payload(payload: dict[str, Any]) -> tuple[str, str]:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return serialized, hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _source_document(*, descriptor: SourceDescriptor, captured_at: datetime) -> NormativeDocument:
    document, _ = NormativeDocument.objects.get_or_create(
        issuer="Universidad Nacional de Colombia",
        document_type="ACADEMIC_OFFERING_SOURCE",
        number=descriptor.key[:80],
        year=captured_at.year,
        defaults={
            "title": descriptor.name,
            "canonical_url": descriptor.url,
            "status": SourceStatus.ACTIVE.value,
            "metadata": {
                "source_kind": "TEMPORAL_OFFERING",
                "retrieval_method": descriptor.retrieval_method,
            },
        },
    )
    return document


def _snapshot(
    *,
    descriptor: SourceDescriptor,
    payload: dict[str, Any],
    captured_at: datetime,
    term_code: str,
) -> SourceSnapshot:
    _, digest = _canonical_payload(payload)
    document = _source_document(descriptor=descriptor, captured_at=captured_at)
    snapshot, _ = SourceSnapshot.objects.get_or_create(
        document=document,
        sha256=digest,
        defaults={
            "captured_at": captured_at,
            "mime_type": "application/json",
            "storage_key": f"offerings/{term_code}/{digest}.json",
            "source_url": descriptor.url,
            "metadata": {
                "schema_version": payload.get("schema_version", "offerings/1.0.0"),
                "source_key": descriptor.key,
                "retrieval_method": descriptor.retrieval_method,
                "capacity_realtime": descriptor.capacity_realtime,
                "term_code": term_code,
            },
        },
    )
    return snapshot


def _course_version(
    *, institution: Institution, course_code: str, term_start: date
) -> CourseVersion:
    # Keep the temporal selection explicit; a version ending after the term is valid too.
    version = (
        CourseVersion.objects.filter(
            course__institution=institution,
            course__code=course_code,
            valid_from__lte=term_start,
        )
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=term_start))
        .select_related("course")
        .order_by("-valid_from", "-created_at")
        .first()
    )
    if version is None:
        raise OfferingImportError(f"Course {course_code} has no valid version for the term.")
    return version


def import_offering_payload(
    payload: dict[str, Any],
    *,
    institution: Institution,
    campus: Campus | None = None,
    descriptor: SourceDescriptor,
    captured_at: datetime | None = None,
) -> OfferingImportResult:
    """Apply a normalized offering snapshot transactionally and idempotently."""

    if payload.get("schema_version", "offerings/1.0.0") != "offerings/1.0.0":
        raise OfferingImportError("Unsupported offering payload schema version.")
    term_payload = payload.get("term")
    if not isinstance(term_payload, dict):
        raise OfferingImportError("Offering payload requires a term object.")
    term_code = str(term_payload.get("code", "")).strip()
    if not term_code:
        raise OfferingImportError("Offering term code is required.")
    starts_at = _as_datetime(term_payload.get("starts_at"), field="term.starts_at")
    ends_at = _as_datetime(term_payload.get("ends_at"), field="term.ends_at")
    if ends_at <= starts_at:
        raise OfferingImportError("Offering term must end after it starts.")
    captured = captured_at or datetime.now(UTC)
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=UTC)
    raw_offerings = payload.get("offerings", [])
    if not isinstance(raw_offerings, list):
        raise OfferingImportError("offerings must be a list.")
    _, digest = _canonical_payload(payload)

    with transaction.atomic():
        snapshot = _snapshot(
            descriptor=descriptor,
            payload=payload,
            captured_at=captured,
            term_code=term_code,
        )
        if campus is not None and campus.institution_id != institution.pk:
            raise OfferingImportError("Campus must belong to the import institution.")
        term, term_created = AcademicTerm.objects.select_for_update().get_or_create(
            institution=institution,
            code=term_code,
            defaults={
                "campus": campus,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "status": str(term_payload.get("status", TermStatus.PLANNED.value)),
                "source_snapshot": snapshot,
            },
        )
        if not term_created:
            next_campus_id = (campus or term.campus).pk if (campus or term.campus) else None
            term_is_referenced = (
                term.admissions.exists() or term.admission_facts.filter(status="VERIFIED").exists()
            )
            protected_changed = (
                term.campus_id != next_campus_id
                or term.starts_at != starts_at
                or term.ends_at != ends_at
            )
            if term_is_referenced and protected_changed:
                raise OfferingImportError(
                    "A referenced term cannot change campus or dates during an offering import."
                )
            term.campus = campus or term.campus
            term.starts_at = starts_at
            term.ends_at = ends_at
            term.status = str(term_payload.get("status", term.status))
            update_fields = ["campus", "starts_at", "ends_at", "status", "updated_at"]
            if not term_is_referenced:
                term.source_snapshot = snapshot
                update_fields.append("source_snapshot")
            term.save(update_fields=update_fields)

        offerings_created = offerings_updated = sections_created = sections_updated = 0
        meetings_created = 0
        for raw_offering in raw_offerings:
            if not isinstance(raw_offering, dict):
                raise OfferingImportError("Each offering must be an object.")
            course_code = str(raw_offering.get("course_code", "")).strip()
            if not course_code:
                raise OfferingImportError("Each offering requires course_code.")
            version = _course_version(
                institution=institution,
                course_code=course_code,
                term_start=starts_at.date(),
            )
            offering, created = CourseOffering.objects.select_for_update().get_or_create(
                course_version=version,
                term=term,
                defaults={
                    "status": str(raw_offering.get("status", OfferingStatus.PUBLISHED.value)),
                    "source_snapshot": snapshot,
                    "metadata": {
                        **(
                            dict(raw_offering.get("metadata", {}))
                            if isinstance(raw_offering.get("metadata", {}), Mapping)
                            else {}
                        ),
                        "capacity_realtime": descriptor.capacity_realtime,
                        "source_sha256": digest,
                    },
                },
            )
            if created:
                offerings_created += 1
            else:
                offerings_updated += 1
                offering.status = str(raw_offering.get("status", offering.status))
                offering.source_snapshot = snapshot
                offering.metadata = {
                    **(
                        dict(raw_offering.get("metadata", {}))
                        if isinstance(raw_offering.get("metadata", {}), Mapping)
                        else {}
                    ),
                    "capacity_realtime": descriptor.capacity_realtime,
                    "source_sha256": digest,
                }
                offering.save(update_fields=["status", "source_snapshot", "metadata", "updated_at"])

            raw_sections = raw_offering.get("sections", [])
            if not isinstance(raw_sections, list):
                raise OfferingImportError(f"sections for {course_code} must be a list.")
            for raw_section in raw_sections:
                if not isinstance(raw_section, dict):
                    raise OfferingImportError("Each section must be an object.")
                group_code = str(raw_section.get("group_code", "")).strip()
                if not group_code:
                    raise OfferingImportError(f"Section for {course_code} requires group_code.")
                section, section_created = Section.objects.select_for_update().get_or_create(
                    offering=offering,
                    group_code=group_code,
                    defaults={
                        "modality": str(raw_section.get("modality", SectionModality.UNKNOWN.value)),
                        "capacity": raw_section.get("capacity"),
                        "enrolled_count": raw_section.get("enrolled_count"),
                        "metadata": dict(raw_section.get("metadata", {}))
                        if isinstance(raw_section.get("metadata", {}), Mapping)
                        else {},
                    },
                )
                if section_created:
                    sections_created += 1
                else:
                    sections_updated += 1
                    section.modality = str(raw_section.get("modality", section.modality))
                    section.capacity = raw_section.get("capacity")
                    section.enrolled_count = raw_section.get("enrolled_count")
                    section.metadata = (
                        dict(raw_section.get("metadata", {}))
                        if isinstance(raw_section.get("metadata", {}), Mapping)
                        else {}
                    )
                    section.save(
                        update_fields=[
                            "modality",
                            "capacity",
                            "enrolled_count",
                            "metadata",
                            "updated_at",
                        ]
                    )
                Meeting.objects.filter(section=section).delete()
                raw_meetings = raw_section.get("meetings", [])
                if not isinstance(raw_meetings, list):
                    raise OfferingImportError(
                        f"meetings for {course_code}/{group_code} must be a list."
                    )
                for raw_meeting in raw_meetings:
                    if not isinstance(raw_meeting, dict):
                        raise OfferingImportError("Each meeting must be an object.")
                    day_of_week = raw_meeting.get("day_of_week")
                    if not isinstance(day_of_week, int):
                        raise OfferingImportError(
                            "meeting.day_of_week must be an integer from 0 to 6."
                        )
                    meeting = Meeting(
                        section=section,
                        day_of_week=day_of_week,
                        starts_at=_as_time(raw_meeting.get("starts_at"), field="meeting.starts_at"),
                        ends_at=_as_time(raw_meeting.get("ends_at"), field="meeting.ends_at"),
                        starts_on=_as_date(raw_meeting.get("starts_on"), field="meeting.starts_on"),
                        ends_on=_as_date(raw_meeting.get("ends_on"), field="meeting.ends_on"),
                        session_code=str(raw_meeting.get("session_code", "")),
                        is_alternate=bool(raw_meeting.get("is_alternate", False)),
                        location=str(raw_meeting.get("location", "")),
                        timezone=str(raw_meeting.get("timezone", "America/Bogota")),
                    )
                    meeting.full_clean()
                    meeting.save()
                    meetings_created += 1

    return OfferingImportResult(
        term_id=term.pk,
        source_snapshot_id=snapshot.pk,
        source_sha256=digest,
        term_code=term_code,
        offerings_created=offerings_created,
        offerings_updated=offerings_updated,
        sections_created=sections_created,
        sections_updated=sections_updated,
        meetings_created=meetings_created,
    )
