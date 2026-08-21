from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote
from uuid import UUID

from domain.audit.engine import AuditInputError, audit_degree
from modules.audit.application.services import build_audit_input
from modules.audit.models import DegreeAuditResult, DegreeAuditRun
from modules.curriculum.models import CourseVersion
from modules.governance.models import Evidence
from modules.identity.application.authorization import can_view_audit_for_enrollment
from modules.rules.models import Requirement
from modules.student_records.application.enrollment import preferred_enrollment_for_user
from modules.student_records.models import AcademicRecognition, CourseAttempt, ProgramEnrollment

ACCEPTED_ATTEMPT_STATUSES = frozenset({"PASSED", "VALIDATED", "HOMOLOGATED", "TRANSFERRED"})
IN_PROGRESS_ATTEMPT_STATUSES = frozenset({"ENROLLED", "PLANNED"})


class AcademicOverviewError(RuntimeError):
    """An explainable, authorization-aware failure while building the read model."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: object) -> list[Any]:
    return (
        list(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else []
    )


def _href(path: str, **query: object) -> str:
    values = [
        (key, str(value)) for key, value in query.items() if value is not None and value != ""
    ]
    if not values:
        return path
    return f"{path}?" + "&".join(f"{quote(key)}={quote(value)}" for key, value in values)


def _course_link(course: CourseVersion, *, selected: bool = True) -> dict[str, Any]:
    code = course.course.code
    return {
        "code": code,
        "name": course.name,
        "credits": course.credits,
        "href": _href("/curriculum", selected=code) if selected else _href("/curriculum"),
    }


def _evidence_view(evidence: Evidence) -> dict[str, Any]:
    snapshot = evidence.snapshot
    document = snapshot.document
    locator = (
        evidence.line_locator
        or evidence.section
        or (f"page:{evidence.page}" if evidence.page else "source")
    )
    return {
        "reference": f"{snapshot.sha256}#{locator}",
        "snapshot_sha256": snapshot.sha256,
        "locator": locator,
        "page": evidence.page,
        "section": evidence.section,
        "excerpt": evidence.excerpt,
        "annotation": evidence.annotation,
        "source_title": document.title,
        "source_url": snapshot.source_url or document.canonical_url or None,
    }


def _requirement_evidence(requirement: Requirement | None) -> list[dict[str, Any]]:
    if requirement is None:
        return []
    return [_evidence_view(item) for item in requirement.evidence.all()]


def _reason_view(
    *,
    requirement: Mapping[str, Any] | None,
    requirement_model: Requirement | None,
) -> dict[str, Any]:
    item = requirement or {}
    result = _mapping(item.get("result"))
    metadata = _mapping(requirement_model.metadata if requirement_model else {})
    evidence_refs = [str(value) for value in _list(item.get("evidence_refs"))]
    evidence = _requirement_evidence(requirement_model)
    if not evidence_refs:
        evidence_refs = [str(value["reference"]) for value in evidence]
    return {
        "code": str(item.get("code", "UNKNOWN_REQUIREMENT")),
        "purpose": str(item.get("purpose", "ENROLLMENT_PREREQUISITE")),
        "status": str(result.get("status", "UNKNOWN")),
        "progress": dict(_mapping(result.get("progress"))),
        "explanation_key": str(result.get("explanation_key", "rule.unknown")),
        "facts_used": [str(value) for value in _list(result.get("facts_used"))],
        "evidence_refs": evidence_refs,
        "evidence": evidence,
        "epistemic_status": str(
            requirement_model.epistemic_status if requirement_model else "UNKNOWN"
        ),
        "note": str(metadata.get("note", "")),
        "source_url": str(metadata.get("source_url", "")) or None,
    }


def _requirement_view(
    item: Mapping[str, Any],
    *,
    requirement_model: Requirement | None,
    enrollment_id: UUID,
) -> dict[str, Any]:
    result = _mapping(item.get("result"))
    model_metadata = _mapping(requirement_model.metadata if requirement_model else {})
    reason = _reason_view(requirement=item, requirement_model=requirement_model)
    return {
        "code": str(item.get("code", "UNKNOWN_REQUIREMENT")),
        "owner_course_code": item.get("owner_course_code"),
        "purpose": str(item.get("purpose", "ENROLLMENT_PREREQUISITE")),
        "status": str(result.get("status", "UNKNOWN")),
        "progress": dict(_mapping(result.get("progress"))),
        "explanation_key": str(result.get("explanation_key", "rule.unknown")),
        "facts_used": [str(value) for value in _list(result.get("facts_used"))],
        "evidence_refs": reason["evidence_refs"],
        "evidence": reason["evidence"],
        "epistemic_status": str(
            requirement_model.epistemic_status if requirement_model else "UNKNOWN"
        ),
        "note": str(model_metadata.get("note", "")),
        "source_url": str(model_metadata.get("source_url", "")) or None,
        "href": _href(
            "/audit",
            enrollment=enrollment_id,
            requirement=str(item.get("code", "")),
        ),
    }


def _select_course_states(
    attempts: Sequence[CourseAttempt],
) -> tuple[dict[str, CourseAttempt], set[str], set[str]]:
    selected: dict[str, CourseAttempt] = {}
    in_progress: set[str] = set()
    for attempt in attempts:
        code = attempt.course_version.course.code
        if attempt.status in ACCEPTED_ATTEMPT_STATUSES:
            current = selected.get(code)
            if current is None or (
                -attempt.credits_earned,
                attempt.status,
                str(attempt.pk),
            ) < (
                -current.credits_earned,
                current.status,
                str(current.pk),
            ):
                selected[code] = attempt
        elif attempt.status in IN_PROGRESS_ATTEMPT_STATUSES:
            in_progress.add(code)
    in_progress.difference_update(selected)
    return selected, set(selected), in_progress


def _course_eligibility(
    *,
    course_code: str,
    passed: set[str],
    in_progress: set[str],
    requirements: Sequence[Mapping[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    if course_code in passed:
        return "PASSED", []
    if course_code in in_progress:
        return "IN_PROGRESS", []
    if not requirements:
        # Absence of a published rule is not proof that a course is open.
        return "UNKNOWN", [
            {
                "code": f"COURSE_RULE_MISSING:{course_code}",
                "purpose": "ENROLLMENT_PREREQUISITE",
                "status": "UNKNOWN",
                "progress": {"current": 0, "required": 1, "unit": "boolean"},
                "explanation_key": "course.rule_not_published",
                "facts_used": [course_code],
                "evidence_refs": [],
                "evidence": [],
                "epistemic_status": "UNKNOWN",
                "note": "No se encontró una regla publicada para determinar la elegibilidad.",
                "source_url": None,
            }
        ]
    reasons = [_reason_view(requirement=item, requirement_model=None) for item in requirements]
    statuses = {str(reason["status"]) for reason in reasons}
    if "UNSATISFIED" in statuses:
        return "BLOCKED", reasons
    if "UNKNOWN" in statuses:
        return "UNKNOWN", reasons
    if statuses <= {"SATISFIED", "NOT_APPLICABLE"}:
        return "ELIGIBLE", reasons
    return "UNKNOWN", reasons


def _warning(code: str, detail: str, *, severity: str = "WARNING") -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "title": code.replace("_", " ").title(),
        "detail": detail,
    }


def _latest_audit_payload(
    enrollment: ProgramEnrollment,
) -> tuple[dict[str, Any], DegreeAuditRun | None, str]:
    run = (
        DegreeAuditRun.objects.filter(enrollment=enrollment)
        .select_related("result")
        .order_by("-generated_at", "-created_at")
        .first()
    )
    if run is not None:
        try:
            persisted = run.result
        except DegreeAuditResult.DoesNotExist:
            persisted = None
        if persisted is not None and isinstance(persisted.payload, dict):
            return persisted.payload, run, "PERSISTED"
    # A GET must still be useful for a newly created student, but it must not
    # create an audit run as a side effect. Mutations/imports persist the
    # reproducible run; this path is a read-only preview for the empty state.
    try:
        result = audit_degree(build_audit_input(enrollment))
    except AuditInputError as error:
        raise AcademicOverviewError(
            "La revisión curricular de esta matrícula tiene datos inconsistentes "
            "(por ejemplo, créditos de componentes que no suman el total); "
            "la administración debe corregirla antes de presentar el avance.",
            code="audit_input_inconsistent",
        ) from error
    return result.to_dict(), None, "READ_ONLY_PREVIEW"


def _enrollment_view(enrollment: ProgramEnrollment) -> dict[str, Any]:
    revision = enrollment.revision_basis
    revision_hash = revision.content_hash or str(revision.pk)
    return {
        "id": enrollment.pk,
        "student_name": enrollment.student.display_name or enrollment.student.user.email,
        "student_number": enrollment.student.student_number or None,
        "program_code": enrollment.program.code,
        "program_name": enrollment.program.name,
        "plan_code": enrollment.plan.code,
        "plan_title": enrollment.plan.title,
        "revision_code": revision.revision_code,
        "revision_hash": revision_hash,
        "status": enrollment.status,
    }


def build_academic_overview(
    actor: Any,
    *,
    enrollment_id: UUID | str | None = None,
) -> dict[str, Any]:
    """Build the dashboard read model from one reproducible audit result.

    The engine remains the only authority for audit conclusions. This service
    only joins labels, evidence, private enrollment context and deep links for
    the presentation contract; it never recomputes credits in the frontend.
    """

    if enrollment_id is not None:
        try:
            enrollment = ProgramEnrollment.objects.select_related(
                "student__user", "program", "plan", "revision_basis"
            ).get(pk=enrollment_id)
        except ProgramEnrollment.DoesNotExist as exc:
            raise AcademicOverviewError(
                "Enrollment was not found.", code="enrollment_not_found"
            ) from exc
        if not can_view_audit_for_enrollment(actor, enrollment):
            raise AcademicOverviewError(
                "You cannot view this academic overview.", code="overview_forbidden"
            )
    else:
        enrollment = None
        if getattr(actor, "pk", None):
            enrollment = preferred_enrollment_for_user(actor.pk)
        if enrollment is None:
            raise AcademicOverviewError(
                "No student enrollment is available.", code="enrollment_not_found"
            )
    if enrollment.status == "NEEDS_REVIEW":
        raise AcademicOverviewError(
            "La revisión curricular de esta matrícula necesita validación administrativa; no se calcularán conclusiones académicas hasta resolverla.",
            code="enrollment_needs_review",
        )

    payload, run, payload_source = _latest_audit_payload(enrollment)
    overall = dict(_mapping(payload.get("overall")))
    required = int(
        overall.get("required_credits", enrollment.revision_basis.total_required_credits) or 0
    )
    applied = int(overall.get("applied_credits", 0) or 0)
    overall["required_credits"] = required
    overall["earned_credits"] = int(overall.get("earned_credits", 0) or 0)
    overall["applied_credits"] = applied
    overall["unapplied_credits"] = int(overall.get("unapplied_credits", 0) or 0)
    overall["credit_progress_percent"] = (applied * 100 // required) if required else 0

    attempts = list(
        enrollment.course_attempts.select_related("course_version__course").order_by(
            "course_version__course__code", "attempt_number", "id"
        )
    )
    selected_attempts, passed, in_progress = _select_course_states(attempts)
    recognitions = list(
        AcademicRecognition.objects.filter(enrollment=enrollment).select_related(
            "target_course_version__course"
        )
    )
    has_history = bool(attempts or recognitions)

    groups_by_code = {
        group.code: group
        for group in enrollment.revision_basis.requirement_groups.select_related("parent").order_by(
            "sort_order", "code"
        )
    }
    component_groups_by_code = {
        str(
            group.metadata.get("source_component_id", group.code.removeprefix("COMPONENT::"))
        ): group
        for group in groups_by_code.values()
        if group.kind == "COMPONENT"
    }
    memberships = list(
        enrollment.revision_basis.memberships.select_related(
            "course_version__course", "group"
        ).order_by("course_version__course__code", "group__code")
    )
    courses_by_code: dict[str, CourseVersion] = {}
    course_groups: dict[str, list[str]] = defaultdict(list)
    for membership in memberships:
        code = membership.course_version.course.code
        courses_by_code.setdefault(code, membership.course_version)
        if membership.group.code not in course_groups[code]:
            course_groups[code].append(membership.group.code)

    requirement_models = {
        requirement.code: requirement
        for requirement in Requirement.objects.filter(revision=enrollment.revision_basis)
        .prefetch_related("evidence__snapshot__document")
        .order_by("code")
    }
    raw_requirements = [
        _mapping(item) for item in _list(payload.get("requirements")) if isinstance(item, Mapping)
    ]
    requirements_by_course: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in raw_requirements:
        owner = item.get("owner_course_code")
        if owner:
            requirements_by_course[str(owner)].append(item)

    course_options: list[dict[str, Any]] = []
    for code, course in sorted(courses_by_code.items()):
        eligibility, reasons = _course_eligibility(
            course_code=code,
            passed=passed,
            in_progress=in_progress,
            requirements=requirements_by_course.get(code, []),
        )
        if eligibility not in {"PASSED", "IN_PROGRESS"}:
            enriched_reasons = []
            for reason in reasons:
                model = requirement_models.get(str(reason.get("code", "")))
                if model is not None:
                    evidence = _requirement_evidence(model)
                    enriched_reason = dict(reason)
                    enriched_reason["evidence"] = evidence
                    enriched_reason["evidence_refs"] = [
                        str(value["reference"]) for value in evidence
                    ] or list(reason.get("evidence_refs", []))
                    enriched_reason["epistemic_status"] = model.epistemic_status
                    metadata = _mapping(model.metadata)
                    enriched_reason["note"] = str(metadata.get("note", ""))
                    enriched_reason["source_url"] = str(metadata.get("source_url", "")) or None
                    enriched_reasons.append(enriched_reason)
                else:
                    enriched_reasons.append(reason)
            reasons = enriched_reasons
        selected_attempt = selected_attempts.get(code)
        course_options.append(
            {
                **_course_link(course),
                "eligibility": eligibility,
                "group_codes": sorted(course_groups.get(code, [])),
                "reasons": reasons,
                "selected_attempt_id": selected_attempt.pk if selected_attempt else None,
            }
        )

    raw_groups = [
        _mapping(item) for item in _list(payload.get("groups")) if isinstance(item, Mapping)
    ]
    group_views: list[dict[str, Any]] = []
    for item in raw_groups:
        code = str(item.get("code", ""))
        group = groups_by_code.get(code)
        model_courses = {
            membership.course_version.course.code: membership.course_version
            for membership in memberships
            if membership.group.code == code
        }
        mandatory = [
            _course_link(model_courses[course_code])
            if course_code in model_courses
            else {
                "code": course_code,
                "name": course_code,
                "credits": None,
                "href": _href("/curriculum", selected=course_code),
            }
            for course_code in sorted(str(value) for value in _list(item.get("mandatory_missing")))
        ]
        options = [
            _course_link(model_courses[course_code])
            for course_code in sorted(str(value) for value in _list(item.get("options_available")))
            if course_code in model_courses
        ]
        group_views.append(
            {
                "code": code,
                "label": group.label if group else code,
                "component": str(
                    item.get("component", group.parent.code if group and group.parent else "")
                ),
                "required_credits": int(item.get("required", 0) or 0),
                "applied_credits": int(item.get("applied", 0) or 0),
                "remaining_credits": int(item.get("remaining", 0) or 0),
                "mandatory_missing": mandatory,
                "options_available": options,
                "status": str(item.get("status", "UNKNOWN")),
                "explanation_key": str(item.get("explanation_key", "audit.group_incomplete")),
                "waived": bool(item.get("waived", False)),
                "href": _href("/audit", enrollment=enrollment.pk, group=code),
            }
        )

    raw_components = [
        _mapping(item) for item in _list(payload.get("components")) if isinstance(item, Mapping)
    ]
    component_views = []
    for item in raw_components:
        code = str(item.get("code", ""))
        component = component_groups_by_code.get(code) or groups_by_code.get(code)
        component_views.append(
            {
                "code": code,
                "label": component.label if component else code,
                "required_credits": int(item.get("required", 0) or 0),
                "applied_credits": int(item.get("applied", 0) or 0),
                "remaining_credits": int(item.get("remaining", 0) or 0),
                "progress_percent": (
                    int(item.get("applied", 0) or 0) * 100 // int(item.get("required", 0) or 1)
                    if int(item.get("required", 0) or 0)
                    else 0
                ),
                "status": str(item.get("status", "UNKNOWN")),
                "explanation_key": str(item.get("explanation_key", "audit.component_incomplete")),
                "href": _href("/audit", enrollment=enrollment.pk, component=code),
            }
        )

    graduation_items = [
        item for item in _list(payload.get("graduation_requirements")) if isinstance(item, Mapping)
    ]
    graduation_views = [
        _requirement_view(
            _mapping(item),
            requirement_model=requirement_models.get(str(_mapping(item).get("code", ""))),
            enrollment_id=enrollment.pk,
        )
        for item in graduation_items
    ]
    requirement_views = [
        _requirement_view(
            _mapping(item),
            requirement_model=requirement_models.get(str(_mapping(item).get("code", ""))),
            enrollment_id=enrollment.pk,
        )
        for item in raw_requirements
    ]

    raw_unknowns = [
        _mapping(item) for item in _list(payload.get("unknowns")) if isinstance(item, Mapping)
    ]
    unknown_views = [
        {
            "kind": str(item.get("kind", "unknown")),
            "code": str(item.get("code", "UNKNOWN")),
            "detail": str(
                item.get(
                    "detail",
                    "La auditoría no puede resolver este dato con la información disponible.",
                )
            ),
            "material": bool(item.get("material", True)),
            "href": _href("/audit", enrollment=enrollment.pk, requirement=item.get("code")),
        }
        for item in raw_unknowns
    ]
    warning_views = [
        _warning(
            str(value),
            "La auditoría conserva esta advertencia para evitar una conclusión engañosa.",
        )
        for value in sorted(str(value) for value in _list(payload.get("warnings")))
    ]
    if not has_history:
        warning_views.insert(
            0,
            _warning(
                "HISTORY_NOT_LOADED",
                "No hay intentos ni reconocimientos registrados; el avance no representa todavía la historia completa.",
            ),
        )
    if unknown_views:
        warning_views.append(
            _warning(
                "MATERIAL_UNKNOWN_PRESENT",
                "Hay requisitos o hechos no verificables; el estado no se presenta como completo.",
            )
        )

    for warning in warning_views:
        warning["href"] = _href("/audit", enrollment=enrollment.pk, warning=warning["code"])

    next_unlocks: list[dict[str, Any]] = []
    for raw_unlock in _list(payload.get("next_unlocks")):
        item = _mapping(raw_unlock)
        code = str(item.get("course_code", ""))
        unlock_course = courses_by_code.get(code)
        if unlock_course is None:
            continue
        unlock_reason = _mapping(item.get("reason"))
        next_unlocks.append(
            {
                **_course_link(unlock_course),
                "status": str(item.get("status", "UNKNOWN")),
                "reason": _reason_view(requirement=None, requirement_model=None)
                if not unlock_reason
                else {
                    "code": code,
                    "purpose": "ENROLLMENT_PREREQUISITE",
                    "status": str(unlock_reason.get("status", item.get("status", "UNKNOWN"))),
                    "progress": dict(_mapping(unlock_reason.get("progress"))),
                    "explanation_key": str(unlock_reason.get("explanation_key", "rule.unknown")),
                    "facts_used": [str(value) for value in _list(unlock_reason.get("facts_used"))],
                    "evidence_refs": [str(value) for value in _list(unlock_reason.get("evidence"))],
                    "evidence": [],
                    "epistemic_status": "UNKNOWN",
                    "note": "",
                    "source_url": None,
                },
                "href": _href("/curriculum", selected=code),
            }
        )

    external_views = [item for item in graduation_views if item["purpose"] == "GRADUATION"]
    revision_hash = str(
        payload.get("revision_hash")
        or enrollment.revision_basis.content_hash
        or enrollment.revision_basis.pk
    )
    audit_metadata = {
        "run_id": run.pk if run else None,
        "generated_at": run.generated_at if run else None,
        "engine_version": str(payload.get("engine_version", "")) or None,
        "result_hash": str(payload.get("result_hash", "")) or None,
        "input_fingerprint": str(payload.get("input_fingerprint", "")) or None,
        "revision_hash": revision_hash,
        "source": payload_source,
    }
    state = "NO_HISTORY" if not has_history else "INCOMPLETE" if unknown_views else "READY"
    return {
        "state": state,
        "enrollment": _enrollment_view(enrollment),
        "audit": {
            "metadata": audit_metadata,
            "overall": overall,
            "ledger": dict(_mapping(payload.get("ledger"))),
        },
        "components": component_views,
        "groups": group_views,
        "graduation_requirements": graduation_views,
        "external_graduation_requirements": external_views,
        "requirements": requirement_views,
        "mandatory_missing": [
            course for group in group_views for course in group["mandatory_missing"]
        ],
        "unknowns": unknown_views,
        "warnings": warning_views,
        "eligible_courses": [item for item in course_options if item["eligibility"] == "ELIGIBLE"],
        "blocked_courses": [item for item in course_options if item["eligibility"] == "BLOCKED"],
        "unknown_courses": [item for item in course_options if item["eligibility"] == "UNKNOWN"],
        "course_options": course_options,
        "next_unlocks": next_unlocks,
        "history": {
            "has_records": has_history,
            "attempt_count": len(attempts),
            "passed_count": len(passed),
            "in_progress_count": len(in_progress),
            "recognition_count": len(recognitions),
        },
        "links": {
            "self": _href("/audit", enrollment=enrollment.pk),
            "history": _href("/history", enrollment=enrollment.pk),
            "curriculum": _href("/curriculum", revision=enrollment.revision_basis.pk),
        },
    }
