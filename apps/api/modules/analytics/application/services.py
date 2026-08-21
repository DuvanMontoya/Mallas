from __future__ import annotations

import csv
import hashlib
import hmac
import io
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any
from uuid import UUID

from django.conf import settings
from django.http import HttpResponse

from domain.enums import RevisionStatus
from modules.audit.models import DegreeAuditResult, DegreeAuditRun
from modules.identity.application.audit import record_audit_event
from modules.identity.application.authorization import (
    active_role_assignments,
    can_view_audit_for_enrollment,
)
from modules.institutions.models import Institution, Program
from modules.offerings.models import AcademicTerm
from modules.planning.models import PlannedCourse, PlanScenario, ScenarioAuditProjection
from modules.student_records.models import CourseAttempt, ProgramEnrollment

ANALYTICS_SCHEMA_VERSION = "1.0"
DEFAULT_MIN_CELL_SIZE = 5
_SATISFIED_STATUSES = frozenset({"SATISFIED", "NOT_APPLICABLE"})
_BLOCKING_STATUSES = frozenset({"UNSATISFIED", "UNKNOWN"})
_PASSED_ATTEMPT_STATUSES = frozenset({"PASSED", "VALIDATED", "HOMOLOGATED", "TRANSFERRED"})


class AnalyticsError(RuntimeError):
    """An intentional, explainable analytics failure."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


_DEFINITIONS: tuple[dict[str, str], ...] = (
    {
        "key": "credits.applied",
        "label": "Créditos aplicados",
        "description": "Créditos asignados por el motor a requisitos de la revisión.",
        "source": "DegreeAuditResult.payload.overall.applied_credits",
        "epistemic_status": "DERIVED",
        "privacy": "PRIVATE_OR_AGGREGATED",
    },
    {
        "key": "credits.progress_percent",
        "label": "Avance crediticio",
        "description": "Créditos aplicados divididos por créditos requeridos, truncado a entero.",
        "source": "DegreeAuditResult.payload.overall",
        "epistemic_status": "DERIVED",
        "privacy": "PRIVATE_OR_AGGREGATED",
    },
    {
        "key": "requirements.remaining",
        "label": "Requisitos pendientes",
        "description": "Requisitos de curso o grado cuyo resultado no es SATISFIED ni NOT_APPLICABLE.",
        "source": "DegreeAuditResult.payload.requirements + graduation_requirements",
        "epistemic_status": "DERIVED",
        "privacy": "PRIVATE_OR_AGGREGATED",
    },
    {
        "key": "advancement.trend",
        "label": "Evolución del avance",
        "description": "Serie temporal de resultados de auditoría persistidos, sin recalcular snapshots históricos.",
        "source": "DegreeAuditRun + DegreeAuditResult",
        "epistemic_status": "DERIVED",
        "privacy": "PRIVATE",
    },
    {
        "key": "courses.bottleneck",
        "label": "Cursos cuello de botella",
        "description": "Cursos con requisitos publicados UNSATISFIED o UNKNOWN en auditorías seleccionadas.",
        "source": "DegreeAuditResult.payload.requirements",
        "epistemic_status": "DERIVED",
        "privacy": "AGGREGATED_ONLY",
    },
    {
        "key": "demand.potential",
        "label": "Demanda potencial",
        "description": "Estudiantes distintos con un curso planeado o elegible según el último snapshot; no es una predicción de matrícula ni confirma oferta.",
        "source": "PlannedCourse + DegreeAuditResult.payload.requirements",
        "epistemic_status": "DERIVED",
        "privacy": "AGGREGATED_ONLY",
    },
    {
        "key": "time_to_degree.observed",
        "label": "Duración observada",
        "description": "Términos entre admisión y el último término con intento para matrículas COMPLETED; no sustituye una fecha oficial de grado.",
        "source": "ProgramEnrollment + CourseAttempt + AcademicTerm",
        "epistemic_status": "DERIVED",
        "privacy": "AGGREGATED_ONLY",
    },
)


def analytics_definitions() -> list[dict[str, str]]:
    """Return a defensive copy so callers cannot mutate the catalogue."""

    return [dict(item) for item in _DEFINITIONS]


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _items(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if not isinstance(value, (str, bytes, bytearray, int, float)):
        return default
    try:
        return int(value)
    except TypeError, ValueError:
        return default


def _progress_percent(applied: int, required: int) -> int:
    if required <= 0:
        return 0
    return min(100, max(0, applied * 100 // required))


def _audit_payload(run: DegreeAuditRun) -> Mapping[str, Any] | None:
    try:
        result = run.result
    except DegreeAuditResult.DoesNotExist:
        return None
    if not isinstance(result.payload, dict):
        return None
    return result.payload


def _published_runs_for_enrollment(enrollment: ProgramEnrollment) -> list[DegreeAuditRun]:
    return list(
        DegreeAuditRun.objects.filter(
            enrollment=enrollment,
            revision__status=RevisionStatus.PUBLISHED.value,
        )
        .select_related("result")
        .order_by("-generated_at", "-created_at", "-id")[:12]
    )


def _resolve_enrollment(actor: Any, enrollment_id: UUID | str | None) -> ProgramEnrollment:
    query = ProgramEnrollment.objects.select_related(
        "student__user", "program", "plan", "revision_basis"
    )
    if enrollment_id is not None:
        try:
            enrollment = query.get(pk=enrollment_id)
        except ProgramEnrollment.DoesNotExist as exc:
            raise AnalyticsError("Enrollment was not found.", code="enrollment_not_found") from exc
        if not can_view_audit_for_enrollment(actor, enrollment):
            raise AnalyticsError(
                "You cannot view analytics for this enrollment.", code="analytics_forbidden"
            )
        return enrollment

    for status in (
        "ACTIVE",
        "NEEDS_REVIEW",
        "COMPLETED",
        "SUSPENDED",
        "WITHDRAWN",
        "TRANSITIONED",
    ):
        enrollment = query.filter(
            student__user_id=getattr(actor, "pk", None), status=status
        ).first()
        if enrollment is not None:
            return enrollment
    raise AnalyticsError("No student enrollment is available.", code="enrollment_not_found")


def _snapshot_view(run: DegreeAuditRun, payload: Mapping[str, Any]) -> dict[str, Any]:
    overall = _mapping(payload.get("overall"))
    result = run.result
    required = _int(overall.get("required_credits"))
    applied = _int(overall.get("applied_credits"))
    return {
        "captured_at": run.generated_at,
        "status": str(overall.get("status", result.status)),
        "required_credits": required,
        "earned_credits": _int(overall.get("earned_credits")),
        "applied_credits": applied,
        "unapplied_credits": _int(overall.get("unapplied_credits")),
        "progress_percent": _progress_percent(applied, required),
        "unknown_count": result.unknown_count,
        "engine_version": run.engine_version,
        "result_hash": run.result_hash,
        "revision_hash": str(payload.get("revision_hash", "")),
    }


def _requirement_rows(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _items(payload.get("requirements")) + _items(payload.get("graduation_requirements"))


def _requirement_metrics(payload: Mapping[str, Any]) -> dict[str, Any]:
    remaining: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    lagging: dict[str, dict[str, Any]] = {}
    for item in _requirement_rows(payload):
        result = _mapping(item.get("result"))
        status = str(result.get("status", "UNKNOWN"))
        code = str(item.get("code", "UNKNOWN_REQUIREMENT"))
        purpose = str(item.get("purpose", "UNKNOWN"))
        if status not in _SATISFIED_STATUSES:
            row = {
                "code": code,
                "purpose": purpose,
                "status": status,
                "owner_course_code": item.get("owner_course_code"),
            }
            remaining.append(row)
            if status == "UNKNOWN":
                unknown.append(row)
            current = lagging.setdefault(
                code,
                {
                    "code": code,
                    "purpose": purpose,
                    "owner_course_code": item.get("owner_course_code"),
                    "statuses": set(),
                },
            )
            statuses = current["statuses"]
            if isinstance(statuses, set):
                statuses.add(status)

    for row in lagging.values():
        row["statuses"] = sorted(str(status) for status in row["statuses"])
    return {
        "remaining_count": len(remaining),
        "unknown_count": len(unknown),
        "remaining": remaining,
        "lagging": sorted(lagging.values(), key=lambda item: str(item["code"])),
    }


def _course_requirement_index(payload: Mapping[str, Any]) -> dict[str, list[Mapping[str, Any]]]:
    index: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in _items(payload.get("requirements")):
        owner = item.get("owner_course_code")
        if owner:
            index[str(owner)].append(item)
    return index


def _critical_courses(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    index = _course_requirement_index(payload)
    rows: list[dict[str, Any]] = []
    for code, requirements in index.items():
        blocking = []
        statuses: set[str] = set()
        for item in requirements:
            status = str(_mapping(item.get("result")).get("status", "UNKNOWN"))
            statuses.add(status)
            if status in _BLOCKING_STATUSES:
                blocking.append(str(item.get("code", "UNKNOWN_REQUIREMENT")))
        if blocking:
            state = "UNKNOWN" if "UNKNOWN" in statuses else "BLOCKED"
            rows.append(
                {
                    "course_code": code,
                    "state": state,
                    "requirement_codes": sorted(blocking),
                }
            )
    return sorted(rows, key=lambda item: (str(item["state"]), str(item["course_code"])))


def _eligible_courses(payload: Mapping[str, Any], passed_codes: set[str]) -> set[str]:
    eligible: set[str] = set()
    for code, requirements in _course_requirement_index(payload).items():
        if code in passed_codes or not requirements:
            continue
        statuses = {
            str(_mapping(item.get("result")).get("status", "UNKNOWN")) for item in requirements
        }
        if statuses and statuses <= _SATISFIED_STATUSES:
            eligible.add(code)
    return eligible


def _passed_course_codes(enrollment_id: UUID) -> set[str]:
    attempts = CourseAttempt.objects.filter(
        enrollment_id=enrollment_id,
        status__in=_PASSED_ATTEMPT_STATUSES,
    ).values_list("course_version__course__code", flat=True)
    return {str(code) for code in attempts}


def _trend(runs: Iterable[DegreeAuditRun]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in reversed(list(runs)):
        payload = _audit_payload(run)
        if payload is not None:
            rows.append(_snapshot_view(run, payload))
    return rows


def _scenario_metrics(enrollment_id: UUID) -> list[dict[str, Any]]:
    projections = (
        ScenarioAuditProjection.objects.filter(
            scenario__enrollment_id=enrollment_id,
            scenario__enrollment__revision_basis__status=RevisionStatus.PUBLISHED.value,
        )
        .select_related("scenario")
        .order_by("-generated_at", "scenario__name", "-id")
    )
    rows: list[dict[str, Any]] = []
    for projection in projections:
        payload = _mapping(projection.payload)
        overall = _mapping(payload.get("overall"))
        required = _int(overall.get("required_credits"))
        applied = _int(overall.get("applied_credits"))
        rows.append(
            {
                "name": projection.scenario.name,
                "status": projection.scenario.status,
                "generated_at": projection.generated_at,
                "planned_course_count": len(_sequence(payload.get("planned_course_codes"))),
                "planned_course_codes": [
                    str(code) for code in _sequence(payload.get("planned_course_codes"))
                ],
                "required_credits": required,
                "applied_credits": applied,
                "remaining_credits": max(0, required - applied),
                "progress_percent": _progress_percent(applied, required),
                "unknown_count": projection.unknown_count,
                "result_hash": projection.result_hash,
            }
        )
    return rows


def _sequence(value: object) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def build_student_analytics(actor: Any, enrollment_id: UUID | str | None = None) -> dict[str, Any]:
    enrollment = _resolve_enrollment(actor, enrollment_id)
    if enrollment.status == "NEEDS_REVIEW":
        return {
            "schema_version": ANALYTICS_SCHEMA_VERSION,
            "scope": "STUDENT",
            "data_state": "ENROLLMENT_NEEDS_REVIEW",
            "as_of": None,
            "enrollment_id": enrollment.pk,
            "program_code": enrollment.program.code,
            "program_name": enrollment.program.name,
            "plan_code": enrollment.plan.code if enrollment.plan_id else None,
            "revision_code": (
                enrollment.revision_basis.revision_code if enrollment.revision_basis_id else None
            ),
            "snapshot": None,
            "metrics": {
                "credits": None,
                "requirements": None,
                "critical_courses": [],
                "trend": [],
                "scenarios": [],
            },
            "definitions": analytics_definitions(),
            "warnings": [
                "La revisión curricular de esta matrícula debe ser confirmada por administración antes de calcular analítica personal."
            ],
        }
    runs = _published_runs_for_enrollment(enrollment)
    latest = next(((run, _audit_payload(run)) for run in runs), (None, None))
    if latest[0] is None or latest[1] is None:
        return {
            "schema_version": ANALYTICS_SCHEMA_VERSION,
            "scope": "STUDENT",
            "data_state": "NO_PERSISTED_PUBLISHED_AUDIT",
            "as_of": None,
            "enrollment_id": enrollment.pk,
            "program_code": enrollment.program.code,
            "program_name": enrollment.program.name,
            "plan_code": enrollment.plan.code,
            "revision_code": enrollment.revision_basis.revision_code,
            "snapshot": None,
            "metrics": {
                "credits": None,
                "requirements": None,
                "critical_courses": [],
                "trend": [],
                "scenarios": [],
            },
            "definitions": analytics_definitions(),
            "warnings": [
                "No hay una auditoría persistida sobre una revisión publicada para este contexto."
            ],
        }

    run, payload = latest
    assert run is not None
    assert payload is not None
    snapshot = _snapshot_view(run, payload)
    requirements = _requirement_metrics(payload)
    overall = _mapping(payload.get("overall"))
    required = _int(overall.get("required_credits"))
    applied = _int(overall.get("applied_credits"))
    return {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "scope": "STUDENT",
        "data_state": "PERSISTED_PUBLISHED_AUDIT",
        "as_of": run.generated_at,
        "enrollment_id": enrollment.pk,
        "program_code": enrollment.program.code,
        "program_name": enrollment.program.name,
        "plan_code": enrollment.plan.code,
        "revision_code": enrollment.revision_basis.revision_code,
        "snapshot": snapshot,
        "metrics": {
            "credits": {
                "required": required,
                "earned": _int(overall.get("earned_credits")),
                "applied": applied,
                "unapplied": _int(overall.get("unapplied_credits")),
                "remaining": max(0, required - applied),
                "progress_percent": snapshot["progress_percent"],
            },
            "requirements": requirements,
            "critical_courses": _critical_courses(payload),
            "trend": _trend(runs),
            "scenarios": _scenario_metrics(enrollment.pk),
        },
        "definitions": analytics_definitions(),
        "warnings": [],
    }


def _min_cell_size(requested: int | None) -> int:
    configured = max(
        2,
        int(getattr(settings, "ANALYTICS_MIN_CELL_SIZE", DEFAULT_MIN_CELL_SIZE)),
    )
    return max(configured, requested or configured)


def _cell(count: int, *, minimum: int) -> dict[str, Any]:
    if count < minimum:
        return {"count": None, "cell_status": "SUPPRESSED"}
    return {"count": count, "cell_status": "REPORTED"}


def _institution_scope_allowed(actor: Any, institution_id: UUID, program_id: UUID | None) -> bool:
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "is_active", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True
    for assignment in active_role_assignments(actor):
        if assignment.role not in {"ANALYST", "ADMIN"}:
            continue
        if assignment.institution_id not in (None, institution_id):
            continue
        if assignment.program_id is not None and assignment.program_id != program_id:
            continue
        if program_id is None and assignment.program_id is not None:
            continue
        return True
    return False


def _institutional_enrollments(
    institution_id: UUID, program_id: UUID | None
) -> list[ProgramEnrollment]:
    query = ProgramEnrollment.objects.filter(
        student__institution_id=institution_id,
        program__faculty__campus__institution_id=institution_id,
        revision_basis__status=RevisionStatus.PUBLISHED.value,
    ).select_related("program", "revision_basis", "admission_term")
    if program_id is not None:
        query = query.filter(program_id=program_id)
    return list(query.order_by("id"))


def _latest_snapshots(
    enrollments: Sequence[ProgramEnrollment],
) -> list[tuple[ProgramEnrollment, DegreeAuditRun, Mapping[str, Any]]]:
    enrollment_by_id = {enrollment.pk: enrollment for enrollment in enrollments}
    if not enrollment_by_id:
        return []
    runs = (
        DegreeAuditRun.objects.filter(
            enrollment_id__in=enrollment_by_id,
            revision__status=RevisionStatus.PUBLISHED.value,
        )
        .select_related("result")
        .order_by("enrollment_id", "-generated_at", "-created_at", "-id")
    )
    latest: dict[UUID, tuple[DegreeAuditRun, Mapping[str, Any]]] = {}
    for run in runs:
        if run.enrollment_id in latest:
            continue
        payload = _audit_payload(run)
        if payload is not None:
            latest[run.enrollment_id] = (run, payload)
    return [
        (enrollment_by_id[enrollment_id], run, payload)
        for enrollment_id, (run, payload) in latest.items()
    ]


def _progress_distribution(
    snapshots: Sequence[tuple[ProgramEnrollment, DegreeAuditRun, Mapping[str, Any]]],
    minimum: int,
) -> list[dict[str, Any]]:
    buckets = (
        ("0-24%", 0, 24),
        ("25-49%", 25, 49),
        ("50-74%", 50, 74),
        ("75-99%", 75, 99),
        ("100%", 100, 100),
    )
    counts = {label: 0 for label, _, _ in buckets}
    for _, run, payload in snapshots:
        progress = _snapshot_view(run, payload)["progress_percent"]
        for label, low, high in buckets:
            if low <= progress <= high:
                counts[label] += 1
                break
    return [{"bucket": label, **_cell(counts[label], minimum=minimum)} for label, _, _ in buckets]


def _course_aggregate(
    snapshots: Sequence[tuple[ProgramEnrollment, DegreeAuditRun, Mapping[str, Any]]],
    minimum: int,
) -> list[dict[str, Any]]:
    students: dict[str, set[UUID]] = defaultdict(set)
    states: dict[str, set[str]] = defaultdict(set)
    for enrollment, _, payload in snapshots:
        for row in _critical_courses(payload):
            code = str(row["course_code"])
            students[code].add(enrollment.pk)
            states[code].add(str(row["state"]))
    rows = []
    for code in sorted(students):
        count = len(students[code])
        rows.append(
            {
                "course_code": code,
                "states": sorted(states[code]),
                **_cell(count, minimum=minimum),
            }
        )
    return sorted(rows, key=lambda row: (-(row["count"] or -1), row["course_code"]))


def _requirement_aggregate(
    snapshots: Sequence[tuple[ProgramEnrollment, DegreeAuditRun, Mapping[str, Any]]],
    minimum: int,
) -> list[dict[str, Any]]:
    students: dict[str, set[UUID]] = defaultdict(set)
    statuses: dict[str, set[str]] = defaultdict(set)
    purposes: dict[str, set[str]] = defaultdict(set)
    for enrollment, _, payload in snapshots:
        for row in _requirement_metrics(payload)["lagging"]:
            code = str(row["code"])
            students[code].add(enrollment.pk)
            statuses[code].update(str(status) for status in row["statuses"])
            purposes[code].add(str(row["purpose"]))
    rows = []
    for code in sorted(students):
        rows.append(
            {
                "requirement_code": code,
                "purposes": sorted(purposes[code]),
                "statuses": sorted(statuses[code]),
                **_cell(len(students[code]), minimum=minimum),
            }
        )
    return sorted(rows, key=lambda row: (-(row["count"] or -1), row["requirement_code"]))


def _demand_aggregate(
    snapshots: Sequence[tuple[ProgramEnrollment, DegreeAuditRun, Mapping[str, Any]]],
    enrollment_ids: set[UUID],
    term_code: str | None,
    minimum: int,
) -> list[dict[str, Any]]:
    planned: dict[tuple[str, str], set[UUID]] = defaultdict(set)
    eligible: dict[tuple[str, str], set[UUID]] = defaultdict(set)
    planned_query = (
        PlannedCourse.objects.filter(
            scenario__enrollment_id__in=enrollment_ids,
            scenario__status="ACTIVE",
        )
        .select_related("scenario", "course_version__course", "term")
        .order_by("term__starts_at", "course_version__course__code", "id")
    )
    for item in planned_query:
        key_term = item.term.code
        if term_code is not None and key_term != term_code:
            continue
        planned[(key_term, item.course_version.course.code)].add(item.scenario.enrollment_id)

    for enrollment, _, payload in snapshots:
        for code in _eligible_courses(payload, _passed_course_codes(enrollment.pk)):
            eligible[(term_code or "NO_TERM_ASSIGNED", code)].add(enrollment.pk)

    keys = sorted(set(planned) | set(eligible))
    rows: list[dict[str, Any]] = []
    for key_term, course_code in keys:
        planned_students = planned.get((key_term, course_code), set())
        eligible_students = eligible.get((key_term, course_code), set())
        potential_students = planned_students | eligible_students
        rows.append(
            {
                "term_code": key_term,
                "course_code": course_code,
                "basis": "PLANNED_AND_ELIGIBLE",
                **{"planned": _cell(len(planned_students), minimum=minimum)},
                **{"eligible": _cell(len(eligible_students), minimum=minimum)},
                **{"potential": _cell(len(potential_students), minimum=minimum)},
            }
        )
    return sorted(rows, key=lambda row: (str(row["term_code"]), str(row["course_code"])))


def _route_key(route: list[dict[str, Any]]) -> str:
    canonical = "|".join(f"{row['term_code']}:{','.join(row['course_codes'])}" for row in route)
    return hmac.new(
        str(getattr(settings, "ANALYTICS_PSEUDONYMIZATION_KEY", settings.SECRET_KEY)).encode(),
        canonical.encode(),
        hashlib.sha256,
    ).hexdigest()[:24]


def _frequent_routes(enrollment_ids: set[UUID], minimum: int) -> list[dict[str, Any]]:
    scenarios = (
        PlanScenario.objects.filter(
            enrollment_id__in=enrollment_ids,
            status="ACTIVE",
            enrollment__revision_basis__status=RevisionStatus.PUBLISHED.value,
        )
        .prefetch_related("planned_courses__course_version__course", "planned_courses__term")
        .order_by("id")
    )
    route_students: dict[str, set[UUID]] = defaultdict(set)
    route_payload: dict[str, list[dict[str, Any]]] = {}
    for scenario in scenarios:
        grouped: dict[str, list[str]] = defaultdict(list)
        for item in scenario.planned_courses.all():
            grouped[item.term.code].append(item.course_version.course.code)
        route = [
            {"term_code": term, "course_codes": sorted(set(codes))}
            for term, codes in sorted(grouped.items())
        ]
        if not route:
            continue
        key = _route_key(route)
        route_students[key].add(scenario.enrollment_id)
        route_payload[key] = route
    rows = []
    for key, students in route_students.items():
        visible = _cell(len(students), minimum=minimum)
        row = {"route_key": key, **visible}
        if visible["cell_status"] == "REPORTED":
            row["route"] = route_payload[key]
        else:
            row["route"] = None
        rows.append(row)
    return sorted(rows, key=lambda row: (-(row["count"] or -1), row["route_key"]))


def _time_to_degree(enrollments: Sequence[ProgramEnrollment], minimum: int) -> dict[str, Any]:
    completed = [enrollment for enrollment in enrollments if enrollment.status == "COMPLETED"]
    if not completed:
        return {
            "official_state": "UNKNOWN",
            "observed_state": "NO_COMPLETED_ENROLLMENTS",
            "distribution": [],
            "note": "No existe una matrícula COMPLETED con datos suficientes.",
        }
    term_ids = {enrollment.admission_term_id for enrollment in completed}
    attempts = CourseAttempt.objects.filter(
        enrollment_id__in=[item.pk for item in completed]
    ).select_related("term")
    term_ids.update(attempt.term_id for attempt in attempts)
    terms = list(
        AcademicTerm.objects.filter(
            institution_id=completed[0].student.institution_id, pk__in=term_ids
        ).order_by("starts_at", "code")
    )
    indexes = {term.pk: index for index, term in enumerate(terms)}
    latest_by_enrollment: dict[UUID, int] = {}
    for attempt in attempts:
        if attempt.term_id in indexes:
            latest_by_enrollment[attempt.enrollment_id] = max(
                latest_by_enrollment.get(attempt.enrollment_id, -1), indexes[attempt.term_id]
            )
    buckets = {"1-4": 0, "5-8": 0, "9-12": 0, "13+": 0}
    observed = 0
    for enrollment in completed:
        start = indexes.get(enrollment.admission_term_id)
        end = latest_by_enrollment.get(enrollment.pk)
        if start is None or end is None or end < start:
            continue
        terms_elapsed = end - start + 1
        observed += 1
        bucket = (
            "1-4"
            if terms_elapsed <= 4
            else "5-8"
            if terms_elapsed <= 8
            else "9-12"
            if terms_elapsed <= 12
            else "13+"
        )
        buckets[bucket] += 1
    return {
        "official_state": "UNKNOWN",
        "observed_state": "CALCULATED_OBSERVED",
        "observed_completed_count": _cell(observed, minimum=minimum),
        "distribution": [
            {"terms": bucket, **_cell(count, minimum=minimum)} for bucket, count in buckets.items()
        ],
        "note": "La duración observada usa el último término con intento; no es una fecha oficial de grado.",
    }


def build_institutional_analytics(
    actor: Any,
    *,
    institution_id: UUID,
    program_id: UUID | None = None,
    term_code: str | None = None,
    requested_min_cell_size: int | None = None,
) -> dict[str, Any]:
    if not _institution_scope_allowed(actor, institution_id, program_id):
        raise AnalyticsError(
            "You do not have an analytics role for this institutional scope.",
            code="analytics_forbidden",
        )
    if not Institution.objects.filter(pk=institution_id).exists():
        raise AnalyticsError("Institution was not found.", code="institution_not_found")
    if (
        program_id is not None
        and not Program.objects.filter(
            pk=program_id, faculty__campus__institution_id=institution_id
        ).exists()
    ):
        raise AnalyticsError("Program is outside the requested institution.", code="scope_invalid")
    if (
        term_code is not None
        and not AcademicTerm.objects.filter(institution_id=institution_id, code=term_code).exists()
    ):
        raise AnalyticsError(
            "Term is outside the requested institution or does not exist.", code="term_not_found"
        )

    minimum = _min_cell_size(requested_min_cell_size)
    enrollments = _institutional_enrollments(institution_id, program_id)
    snapshots = _latest_snapshots(enrollments)
    enrollment_ids = {enrollment.pk for enrollment in enrollments}
    population_count = len(enrollments)
    if population_count < minimum:
        return {
            "schema_version": ANALYTICS_SCHEMA_VERSION,
            "scope": "INSTITUTIONAL",
            "data_state": "SUPPRESSED_SMALL_CELL" if population_count else "NO_DATA",
            "institution_id": institution_id,
            "program_id": program_id,
            "term_code": term_code,
            "min_cell_size": minimum,
            "privacy": {
                "contains_student_identifiers": False,
                "pseudonymization": "No student identifier is returned; route keys are keyed digests.",
                "small_cell_policy": f"Counts below {minimum} are suppressed.",
            },
            "population": {
                "enrollment_count": None if population_count else 0,
                "audited_enrollment_count": None,
                "cell_status": "SUPPRESSED" if population_count else "NO_DATA",
            },
            "metrics": {},
            "definitions": analytics_definitions(),
            "warnings": [
                f"La población está por debajo del mínimo de celda ({minimum}); no se muestran desgloses."
                if population_count
                else "No hay matrículas con una revisión publicada en este alcance."
            ],
        }

    return {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "scope": "INSTITUTIONAL",
        "data_state": "AGGREGATED",
        "institution_id": institution_id,
        "program_id": program_id,
        "term_code": term_code,
        "min_cell_size": minimum,
        "privacy": {
            "contains_student_identifiers": False,
            "pseudonymization": "No student identifier is returned; route keys are keyed digests.",
            "small_cell_policy": f"Counts below {minimum} are suppressed.",
        },
        "population": {
            "enrollment_count": population_count,
            "audited_enrollment_count": len(snapshots),
            "cell_status": "REPORTED",
        },
        "metrics": {
            "advancement_distribution": _progress_distribution(snapshots, minimum),
            "bottleneck_courses": _course_aggregate(snapshots, minimum),
            "lagging_requirements": _requirement_aggregate(snapshots, minimum),
            "demand_potential": _demand_aggregate(snapshots, enrollment_ids, term_code, minimum),
            "frequent_routes": _frequent_routes(enrollment_ids, minimum),
            "time_to_degree": _time_to_degree(enrollments, minimum),
        },
        "definitions": analytics_definitions(),
        "warnings": [
            "Los conteos de elegibilidad no confirman oferta, matrícula ni probabilidad de inscripción.",
            "No se produce puntuación individual de riesgo ni predicción opaca.",
        ],
    }


def institutional_csv(payload: Mapping[str, Any]) -> str:
    """Flatten an aggregate response into a deterministic, PII-free CSV."""

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["metric", "dimension", "value", "cell_status"])
    population = _mapping(payload.get("population"))
    writer.writerow(
        [
            "population",
            "enrollment_count",
            population.get("enrollment_count", ""),
            population.get("cell_status", ""),
        ]
    )
    writer.writerow(
        [
            "population",
            "audited_enrollment_count",
            population.get("audited_enrollment_count", ""),
            population.get("cell_status", ""),
        ]
    )
    metrics = _mapping(payload.get("metrics"))
    for metric_name in sorted(metrics):
        metric = metrics[metric_name]
        if isinstance(metric, Sequence) and not isinstance(metric, (str, bytes, bytearray)):
            for row in metric:
                if not isinstance(row, Mapping):
                    continue
                dimension = next(
                    (
                        str(row[key])
                        for key in (
                            "bucket",
                            "course_code",
                            "requirement_code",
                            "term_code",
                            "route_key",
                            "terms",
                        )
                        if row.get(key) is not None
                    ),
                    "row",
                )
                for key, value in sorted(row.items()):
                    if key in {
                        "bucket",
                        "course_code",
                        "requirement_code",
                        "term_code",
                        "route_key",
                        "terms",
                        "cell_status",
                        "route",
                    }:
                        continue
                    if isinstance(value, Mapping):
                        cell_status = value.get("cell_status", "")
                        cell_value = value.get("count", "")
                    else:
                        cell_status = row.get("cell_status", "")
                        cell_value = value
                    writer.writerow([metric_name, f"{dimension}:{key}", cell_value, cell_status])
        elif isinstance(metric, Mapping):
            for key, value in sorted(metric.items()):
                if isinstance(value, Mapping):
                    writer.writerow(
                        [metric_name, key, value.get("count", ""), value.get("cell_status", "")]
                    )
                elif isinstance(value, (str, int, float, bool)) or value is None:
                    writer.writerow([metric_name, key, "" if value is None else value, "REPORTED"])
    return output.getvalue()


def export_institutional_analytics(
    request: Any,
    actor: Any,
    *,
    institution_id: UUID,
    program_id: UUID | None = None,
    term_code: str | None = None,
    requested_min_cell_size: int | None = None,
    export_format: str = "json",
) -> dict[str, Any] | HttpResponse:
    normalized_format = export_format.lower().strip()
    if normalized_format not in {"json", "csv"}:
        raise AnalyticsError("Export format must be json or csv.", code="export_format_invalid")
    payload = build_institutional_analytics(
        actor,
        institution_id=institution_id,
        program_id=program_id,
        term_code=term_code,
        requested_min_cell_size=requested_min_cell_size,
    )
    record_audit_event(
        request,
        actor=actor,
        action="ANALYTICS_EXPORT",
        object_type="institutional_analytics",
        object_id=institution_id,
        institution_id=institution_id,
        metadata={
            "format": normalized_format,
            "program_id": str(program_id) if program_id else None,
            "term_code": term_code,
            "min_cell_size": payload.get("min_cell_size"),
        },
    )
    if normalized_format == "csv":
        response = HttpResponse(institutional_csv(payload), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="curriculum-analytics-{institution_id}.csv"'
        )
        response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
    return payload
