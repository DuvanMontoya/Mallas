from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import replace
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from domain.audit import AcademicRecord, audit_degree
from domain.audit.engine import ENGINE_VERSION, AuditInputError
from domain.offerings.schedule import MeetingWindow
from domain.planning import PlannedCourseFact, RequirementFact, validate_scenario
from domain.rules import parse_rule
from domain.rules.errors import RuleSchemaError
from modules.audit.application.overview import (
    ACCEPTED_ATTEMPT_STATUSES,
    IN_PROGRESS_ATTEMPT_STATUSES,
)
from modules.audit.application.services import build_audit_input
from modules.curriculum.models import Course, CourseVersion
from modules.identity.application.authorization import can_view_enrollment, has_role
from modules.offerings.models import AcademicTerm, CourseOffering, Section
from modules.planning.models import (
    PlannedCourse,
    PlanningPreference,
    PlanScenario,
    ScenarioAuditProjection,
)
from modules.rules.models import Requirement
from modules.student_records.models import ProgramEnrollment


class ScenarioError(RuntimeError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _scenario_queryset() -> QuerySet[PlanScenario]:
    return PlanScenario.objects.select_related(
        "enrollment__student__user",
        "enrollment__program",
        "enrollment__revision_basis",
        "target_term",
        "planning_preferences",
        "audit_projection",
    ).prefetch_related(
        "planned_courses__course_version__course",
        "planned_courses__term",
        "planned_courses__section__offering__course_version__course",
        "planned_courses__section__meetings",
    )


def _get_scenario(actor: Any, scenario_id: UUID | str, *, write: bool = False) -> PlanScenario:
    try:
        scenario = _scenario_queryset().get(pk=scenario_id)
    except PlanScenario.DoesNotExist as exc:
        raise ScenarioError("Scenario was not found.", code="scenario_not_found") from exc
    if not can_view_enrollment(actor, scenario.enrollment):
        raise ScenarioError("You cannot view this private scenario.", code="scenario_forbidden")
    if write and not _can_edit(actor, scenario.enrollment):
        raise ScenarioError("You cannot edit this scenario.", code="scenario_forbidden")
    return scenario


def _can_edit(actor: Any, enrollment: ProgramEnrollment) -> bool:
    if getattr(actor, "pk", None) == enrollment.student.user_id:
        return True
    institution_id = enrollment.student.institution_id
    return has_role(actor, "ADMIN", institution_id=institution_id) or has_role(
        actor, "ADVISOR", institution_id=institution_id
    )


def _enrollment_for_create(actor: Any, enrollment_id: UUID | None) -> ProgramEnrollment:
    query = ProgramEnrollment.objects.select_related(
        "student", "student__user", "program", "plan", "revision_basis"
    )
    if enrollment_id is not None:
        query = query.filter(pk=enrollment_id)
    else:
        query = query.filter(student__user_id=getattr(actor, "pk", None)).exclude(
            status__in={"WITHDRAWN"}
        )
    enrollment = query.order_by("-created_at").first()
    if enrollment is None or not can_view_enrollment(actor, enrollment):
        raise ScenarioError(
            "Enrollment was not found or is not accessible.", code="enrollment_forbidden"
        )
    if not _can_edit(actor, enrollment):
        raise ScenarioError(
            "You cannot create a scenario for this enrollment.", code="scenario_forbidden"
        )
    if enrollment.status == "NEEDS_REVIEW" or enrollment.revision_basis_id is None:
        raise ScenarioError(
            "A curriculum assignment must be resolved before creating a planning scenario.",
            code="enrollment_needs_review",
        )
    return enrollment


def _term_for_enrollment(
    enrollment: ProgramEnrollment, term_id: UUID | None
) -> AcademicTerm | None:
    if term_id is None:
        return None
    term = AcademicTerm.objects.filter(
        pk=term_id, institution_id=enrollment.student.institution_id
    ).first()
    if term is None:
        raise ScenarioError(
            "Target term does not belong to the enrollment institution.", code="term_forbidden"
        )
    return term


def _course_version_for_enrollment(
    enrollment: ProgramEnrollment, course_version_id: UUID
) -> CourseVersion:
    course_version = (
        CourseVersion.objects.select_related("course")
        .filter(pk=course_version_id, course__institution_id=enrollment.student.institution_id)
        .first()
    )
    if course_version is None:
        raise ScenarioError(
            "Course does not belong to the enrollment institution.", code="course_forbidden"
        )
    return course_version


def _section_for_course(
    enrollment: ProgramEnrollment,
    *,
    section_id: UUID | None,
    course_version: CourseVersion,
    term: AcademicTerm,
) -> Section | None:
    if section_id is None:
        return None
    section = (
        Section.objects.select_related("offering__term", "offering__course_version__course")
        .prefetch_related("meetings")
        .filter(pk=section_id)
        .first()
    )
    if section is None:
        raise ScenarioError("Section was not found.", code="section_not_found")
    if (
        section.offering.term_id != term.pk
        or section.offering.course_version_id != course_version.pk
    ):
        raise ScenarioError(
            "Section must belong to the selected course and term.", code="section_mismatch"
        )
    if section.offering.term.institution_id != enrollment.student.institution_id:
        raise ScenarioError(
            "Section does not belong to the enrollment institution.", code="section_forbidden"
        )
    return section


def _version_check(scenario: PlanScenario, expected_version: str | None) -> None:
    if expected_version is not None and expected_version.strip('"') != str(scenario.version):
        raise ScenarioError(
            "The scenario changed since it was read; reload it before editing.",
            code="stale_resource",
        )


def _touch(scenario: PlanScenario) -> None:
    scenario.version += 1
    scenario.save(update_fields=["version", "updated_at"])


def _source_offering_state(offering: CourseOffering | None) -> str:
    if offering is None:
        return "UNKNOWN"
    if offering.status == "CANCELLED":
        return "NOT_OFFERED"
    if offering.source_snapshot_id is None and offering.term.source_snapshot_id is None:
        return "UNKNOWN"
    return "OFFERED"


def _meeting_windows(section: Section | None) -> tuple[MeetingWindow, ...]:
    if section is None:
        return ()
    return tuple(
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
        for meeting in section.meetings.all()
    )


def _requirements_by_course(revision_id: UUID) -> dict[str, list[RequirementFact]]:
    requirements = Requirement.objects.filter(
        revision_id=revision_id, owner_type="COURSE"
    ).order_by("code")
    owner_ids = {str(requirement.owner_id) for requirement in requirements}
    courses = {str(course.pk): course.code for course in Course.objects.filter(pk__in=owner_ids)}
    result: dict[str, list[RequirementFact]] = {}
    for requirement in requirements:
        course_code = courses.get(str(requirement.owner_id))
        if course_code is None:
            continue
        try:
            rule = parse_rule(requirement.ast)
        except RuleSchemaError:
            rule = None
        result.setdefault(course_code, []).append(
            RequirementFact(
                code=requirement.code,
                course_code=course_code,
                rule=rule,
                epistemic_status=requirement.epistemic_status,
            )
        )
    return result


def _validation(scenario: PlanScenario) -> dict[str, Any]:
    if scenario.enrollment.status == "NEEDS_REVIEW":
        return {
            "state": "UNKNOWN",
            "courses": [],
            "warnings": [
                {
                    "code": "ENROLLMENT_NEEDS_REVIEW",
                    "detail": "La revisión curricular de la matrícula debe confirmarse antes de validar esta ruta.",
                    "severity": "WARNING",
                    "course_code": None,
                    "term_code": None,
                }
            ],
        }
    planned = list(
        scenario.planned_courses.select_related("course_version__course", "term", "section")
        .prefetch_related("section__meetings")
        .order_by("term__starts_at", "term__code", "priority", "course_version__course__code")
    )
    terms = list(
        AcademicTerm.objects.filter(
            institution_id=scenario.enrollment.student.institution_id
        ).order_by("starts_at", "code")
    )
    term_order = {term.pk: index for index, term in enumerate(terms)}
    if not term_order:
        term_order = {item.term_id: index for index, item in enumerate(planned)}
    version_ids = {item.course_version_id for item in planned}
    term_ids = {item.term_id for item in planned}
    offerings = CourseOffering.objects.select_related("term").filter(
        course_version_id__in=version_ids, term_id__in=term_ids
    )
    offering_map = {
        (offering.course_version_id, offering.term_id): offering for offering in offerings
    }
    history = scenario.enrollment.course_attempts.select_related("course_version__course")
    passed = frozenset(
        attempt.course_version.course.code
        for attempt in history
        if attempt.status in ACCEPTED_ATTEMPT_STATUSES
    )
    in_progress = frozenset(
        attempt.course_version.course.code
        for attempt in history
        if attempt.status in IN_PROGRESS_ATTEMPT_STATUSES
    )
    facts: list[PlannedCourseFact] = []
    ranges = {term.code: (term.starts_at.date(), term.ends_at.date()) for term in terms}
    for item in planned:
        offering = offering_map.get((item.course_version_id, item.term_id))
        facts.append(
            PlannedCourseFact(
                id=str(item.pk),
                course_code=item.course_version.course.code,
                term_code=item.term.code,
                term_order=term_order.get(item.term_id, 0),
                credits=item.course_version.credits,
                offering_state=_source_offering_state(offering),
                section_id=str(item.section_id) if item.section_id else None,
                modality=item.section.modality if item.section else None,
                meetings=_meeting_windows(item.section),
            )
        )
    preference, _ = PlanningPreference.objects.get_or_create(scenario=scenario)
    validation = validate_scenario(
        facts,
        requirements_by_course=_requirements_by_course(scenario.enrollment.revision_basis_id),
        passed_courses=passed,
        in_progress_courses=in_progress,
        unavailable_weekdays=frozenset(preference.unavailable_weekdays or []),
        min_credits_per_term=preference.min_credits_per_term,
        max_credits_per_term=preference.max_credits_per_term,
        plan_total_credits=scenario.enrollment.revision_basis.total_required_credits,
        term_ranges=ranges,
    )
    return validation.to_dict()


@transaction.atomic  # type: ignore[untyped-decorator]
def recompute_scenario_projection(scenario: PlanScenario) -> ScenarioAuditProjection:
    enrollment = ProgramEnrollment.objects.select_related("revision_basis").get(
        pk=scenario.enrollment_id
    )
    planned = list(
        scenario.planned_courses.select_related("course_version__course").order_by(
            "term__starts_at", "id"
        )
    )
    try:
        audit_input = build_audit_input(enrollment)
        projected_history = tuple(audit_input.history) + tuple(
            AcademicRecord(
                course_code=item.course_version.course.code,
                status="PASSED",
                attempt_id=f"scenario:{scenario.pk}:{item.pk}",
                credits_earned=item.course_version.credits,
            )
            for item in planned
        )
        projected_input = replace(audit_input, history=projected_history)
        result = audit_degree(projected_input)
        payload = result.to_dict()
        payload["projection"] = True
        payload["scenario_id"] = str(scenario.pk)
        payload["planned_course_codes"] = [item.course_version.course.code for item in planned]
        input_fingerprint = projected_input.input_fingerprint
        revision_hash = result.revision_hash
        engine_version = result.engine_version
        result_hash = result.result_hash
        unknown_count = len(result.unknowns)
    except AuditInputError as error:
        # A malformed or incomplete draft revision must make the projection UNKNOWN,
        # never turn a private planning read into a 500 or mutate official history.
        fingerprint_material = {
            "scenario_id": str(scenario.pk),
            "enrollment_id": str(enrollment.pk),
            "revision_id": str(enrollment.revision_basis_id),
            "revision_content_hash": (
                enrollment.revision_basis.content_hash if enrollment.revision_basis_id else None
            ),
            "planned": [
                {
                    "id": str(item.pk),
                    "course_code": item.course_version.course.code,
                    "term_id": str(item.term_id),
                }
                for item in planned
            ],
        }
        input_fingerprint = hashlib.sha256(
            json.dumps(fingerprint_material, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        payload = {
            "projection": True,
            "scenario_id": str(scenario.pk),
            "status": "UNKNOWN",
            "unknowns": [
                {
                    "code": "PROJECTION_INPUT_INVALID",
                    "detail": "La revisión curricular no permite ejecutar la auditoría proyectada.",
                    "technical_detail": str(error),
                }
            ],
            "planned_course_codes": [item.course_version.course.code for item in planned],
        }
        revision_hash = (
            enrollment.revision_basis.content_hash or str(enrollment.revision_basis_id)
            if enrollment.revision_basis_id
            else "UNRESOLVED"
        )
        engine_version = ENGINE_VERSION
        result_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        unknown_count = 1
    projection, _ = ScenarioAuditProjection.objects.update_or_create(
        scenario=scenario,
        defaults={
            "input_fingerprint": input_fingerprint,
            "revision_hash": revision_hash,
            "engine_version": engine_version,
            "result_hash": result_hash,
            "generated_at": timezone.now(),
            "payload": payload,
            "unknown_count": unknown_count,
        },
    )
    return projection


def _projection_dict(projection: ScenarioAuditProjection | None) -> dict[str, Any] | None:
    if projection is None:
        return None
    return {
        "id": projection.pk,
        "input_fingerprint": projection.input_fingerprint,
        "revision_hash": projection.revision_hash,
        "engine_version": projection.engine_version,
        "result_hash": projection.result_hash,
        "generated_at": projection.generated_at,
        "unknown_count": projection.unknown_count,
        "payload": projection.payload,
    }


def _preferences_dict(preference: PlanningPreference) -> dict[str, Any]:
    return {
        "id": preference.pk,
        "max_credits_per_term": preference.max_credits_per_term,
        "min_credits_per_term": preference.min_credits_per_term,
        "unavailable_weekdays": preference.unavailable_weekdays,
        "preferred_modalities": preference.preferred_modalities,
        "preferred_area_codes": preference.preferred_area_codes,
        "objective_weights": preference.objective_weights,
    }


def scenario_view(
    scenario: PlanScenario, *, validation: dict[str, Any] | None = None
) -> dict[str, Any]:
    preference, _ = PlanningPreference.objects.get_or_create(scenario=scenario)
    projection = ScenarioAuditProjection.objects.filter(scenario=scenario).first()
    if projection is None:
        projection = recompute_scenario_projection(scenario)
    if validation is None:
        validation = _validation(scenario)
    rows = []
    for item in scenario.planned_courses.select_related(
        "course_version__course", "term", "section"
    ):
        rows.append(
            {
                "id": item.pk,
                "course_version_id": item.course_version_id,
                "course_code": item.course_version.course.code,
                "course_name": item.course_version.name,
                "credits": item.course_version.credits,
                "term_id": item.term_id,
                "term_code": item.term.code,
                "section_id": item.section_id,
                "section_group_code": item.section.group_code if item.section else None,
                "priority": item.priority,
                "source": item.source,
                "notes": item.notes,
                "is_locked": item.is_locked,
            }
        )
    return {
        "id": scenario.pk,
        "enrollment_id": scenario.enrollment_id,
        "name": scenario.name,
        "status": scenario.status,
        "version": scenario.version,
        "target_term_id": scenario.target_term_id,
        "target_term_code": scenario.target_term.code if scenario.target_term else None,
        "sharing_enabled": scenario.sharing_enabled,
        "share_token": scenario.share_token if scenario.sharing_enabled else None,
        "created_at": scenario.created_at,
        "updated_at": scenario.updated_at,
        "preferences": _preferences_dict(preference),
        "planned_courses": rows,
        "validation": validation,
        "audit_projection": _projection_dict(projection),
    }


def list_scenarios(
    actor: Any, *, enrollment_id: UUID | None = None, include_archived: bool = False
) -> list[dict[str, Any]]:
    if enrollment_id is not None:
        enrollment = _enrollment_for_create(actor, enrollment_id)
        query = _scenario_queryset().filter(enrollment=enrollment)
    else:
        query = _scenario_queryset().filter(enrollment__student__user_id=getattr(actor, "pk", None))
        if not query.exists():
            raise ScenarioError(
                "Enrollment is required for this private scenario list.", code="enrollment_required"
            )
    if not include_archived:
        query = query.filter(status="ACTIVE")
    return [scenario_view(scenario) for scenario in query.order_by("name", "id")]


@transaction.atomic  # type: ignore[untyped-decorator]
def create_scenario(
    actor: Any,
    *,
    name: str,
    enrollment_id: UUID | None = None,
    target_term_id: UUID | None = None,
    preferences: Mapping[str, Any] | None = None,
) -> PlanScenario:
    enrollment = _enrollment_for_create(actor, enrollment_id)
    normalized_name = name.strip()[:160]
    if not normalized_name:
        raise ScenarioError("Scenario name is required.", code="scenario_name_required")
    if PlanScenario.objects.filter(enrollment=enrollment, name=normalized_name).exists():
        raise ScenarioError(
            "A scenario with this name already exists.", code="scenario_name_duplicate"
        )
    target_term = _term_for_enrollment(enrollment, target_term_id)
    scenario = PlanScenario(
        enrollment=enrollment,
        created_by=actor,
        name=normalized_name,
        target_term=target_term,
    )
    scenario.full_clean()
    scenario.save()
    _save_preferences(scenario, preferences or {})
    recompute_scenario_projection(scenario)
    return _get_scenario(actor, scenario.pk, write=True)


def _save_preferences(scenario: PlanScenario, values: Mapping[str, Any]) -> PlanningPreference:
    preference, _ = PlanningPreference.objects.get_or_create(scenario=scenario)
    allowed = {
        "max_credits_per_term",
        "min_credits_per_term",
        "unavailable_weekdays",
        "preferred_modalities",
        "preferred_area_codes",
        "objective_weights",
    }
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise ScenarioError("Unsupported preference fields.", code="preference_fields_invalid")
    for field, value in values.items():
        setattr(preference, field, value)
    preference.full_clean()
    preference.save()
    return preference


@transaction.atomic  # type: ignore[untyped-decorator]
def update_scenario(
    actor: Any,
    scenario_id: UUID,
    *,
    changes: Mapping[str, Any],
    expected_version: str | None,
) -> PlanScenario:
    scenario = _get_scenario(actor, scenario_id, write=True)
    scenario = PlanScenario.objects.select_for_update().get(pk=scenario.pk)
    _version_check(scenario, expected_version)
    allowed = {"name", "status", "target_term_id", "sharing_enabled", "preferences"}
    unknown = sorted(set(changes) - allowed)
    if unknown:
        raise ScenarioError("Unsupported scenario fields.", code="mass_assignment_blocked")
    if "name" in changes:
        name = str(changes["name"]).strip()[:160]
        if not name:
            raise ScenarioError("Scenario name is required.", code="scenario_name_required")
        if (
            PlanScenario.objects.filter(enrollment=scenario.enrollment, name=name)
            .exclude(pk=scenario.pk)
            .exists()
        ):
            raise ScenarioError(
                "A scenario with this name already exists.", code="scenario_name_duplicate"
            )
        scenario.name = name
    if "status" in changes:
        status = str(changes["status"]).upper()
        if status not in {"ACTIVE", "ARCHIVED"}:
            raise ScenarioError("Unsupported scenario status.", code="scenario_status_invalid")
        scenario.status = status
    if "target_term_id" in changes:
        scenario.target_term = _term_for_enrollment(scenario.enrollment, changes["target_term_id"])
    if "sharing_enabled" in changes:
        scenario.sharing_enabled = bool(changes["sharing_enabled"])
        if not scenario.sharing_enabled:
            scenario.share_token = None
    scenario.full_clean()
    scenario.save()
    if "preferences" in changes:
        values = changes["preferences"]
        if not isinstance(values, Mapping):
            raise ScenarioError("preferences must be an object.", code="preferences_invalid")
        _save_preferences(scenario, values)
    _touch(scenario)
    recompute_scenario_projection(scenario)
    return _get_scenario(actor, scenario.pk, write=True)


@transaction.atomic  # type: ignore[untyped-decorator]
def add_planned_course(
    actor: Any,
    scenario_id: UUID,
    *,
    course_version_id: UUID,
    term_id: UUID,
    section_id: UUID | None,
    priority: int,
    notes: str,
    expected_version: str | None,
) -> PlanScenario:
    scenario = _get_scenario(actor, scenario_id, write=True)
    scenario = PlanScenario.objects.select_for_update().get(pk=scenario.pk)
    _version_check(scenario, expected_version)
    term = _term_for_enrollment(scenario.enrollment, term_id)
    if term is None:
        raise ScenarioError("A planning term is required.", code="term_required")
    course_version = _course_version_for_enrollment(scenario.enrollment, course_version_id)
    section = _section_for_course(
        scenario.enrollment,
        section_id=section_id,
        course_version=course_version,
        term=term,
    )
    if PlannedCourse.objects.filter(
        scenario=scenario, course_version=course_version, term=term
    ).exists():
        raise ScenarioError(
            "This course is already planned for this term.", code="planned_course_duplicate"
        )
    item = PlannedCourse(
        scenario=scenario,
        course_version=course_version,
        term=term,
        section=section,
        priority=max(0, priority),
        notes=notes[:2_000],
    )
    item.full_clean()
    item.save()
    _touch(scenario)
    recompute_scenario_projection(scenario)
    return _get_scenario(actor, scenario.pk, write=True)


@transaction.atomic  # type: ignore[untyped-decorator]
def update_planned_course(
    actor: Any,
    scenario_id: UUID,
    planned_course_id: UUID,
    *,
    changes: Mapping[str, Any],
    expected_version: str | None,
) -> PlanScenario:
    scenario = _get_scenario(actor, scenario_id, write=True)
    scenario = PlanScenario.objects.select_for_update().get(pk=scenario.pk)
    _version_check(scenario, expected_version)
    try:
        item = PlannedCourse.objects.select_related("course_version__course", "term").get(
            pk=planned_course_id, scenario=scenario
        )
    except PlannedCourse.DoesNotExist as exc:
        raise ScenarioError(
            "Planned course was not found.", code="planned_course_not_found"
        ) from exc
    allowed = {"term_id", "section_id", "priority", "notes", "is_locked"}
    unknown = sorted(set(changes) - allowed)
    if unknown:
        raise ScenarioError("Unsupported planned course fields.", code="mass_assignment_blocked")
    new_term = item.term
    if "term_id" in changes:
        new_term = _term_for_enrollment(scenario.enrollment, changes["term_id"])
        if new_term is None:
            raise ScenarioError("A planning term is required.", code="term_required")
    new_section_id = changes.get("section_id", item.section_id)
    new_section = _section_for_course(
        scenario.enrollment,
        section_id=new_section_id,
        course_version=item.course_version,
        term=new_term,
    )
    moving = new_term.pk != item.term_id or new_section_id != item.section_id
    if moving and item.is_locked:
        raise ScenarioError(
            "Unlock this course before changing its term or group.", code="planned_course_locked"
        )
    if (
        moving
        and PlannedCourse.objects.filter(
            scenario=scenario, course_version=item.course_version, term=new_term
        )
        .exclude(pk=item.pk)
        .exists()
    ):
        raise ScenarioError(
            "This course is already planned for the target term.", code="planned_course_duplicate"
        )
    item.term = new_term
    item.section = new_section
    if "priority" in changes:
        item.priority = max(0, int(changes["priority"]))
    if "notes" in changes:
        item.notes = str(changes["notes"])[:2_000]
    if "is_locked" in changes:
        item.is_locked = bool(changes["is_locked"])
    item.full_clean()
    item.save()
    _touch(scenario)
    recompute_scenario_projection(scenario)
    return _get_scenario(actor, scenario.pk, write=True)


@transaction.atomic  # type: ignore[untyped-decorator]
def delete_planned_course(
    actor: Any,
    scenario_id: UUID,
    planned_course_id: UUID,
    *,
    expected_version: str | None,
) -> PlanScenario:
    scenario = _get_scenario(actor, scenario_id, write=True)
    scenario = PlanScenario.objects.select_for_update().get(pk=scenario.pk)
    _version_check(scenario, expected_version)
    item = PlannedCourse.objects.filter(pk=planned_course_id, scenario=scenario).first()
    if item is None:
        raise ScenarioError("Planned course was not found.", code="planned_course_not_found")
    if item.is_locked:
        raise ScenarioError("Unlock this course before removing it.", code="planned_course_locked")
    item.delete()
    _touch(scenario)
    recompute_scenario_projection(scenario)
    return _get_scenario(actor, scenario.pk, write=True)


@transaction.atomic  # type: ignore[untyped-decorator]
def duplicate_scenario(
    actor: Any,
    scenario_id: UUID,
    *,
    name: str,
) -> PlanScenario:
    source = _get_scenario(actor, scenario_id, write=False)
    normalized_name = name.strip()[:160]
    if not normalized_name:
        raise ScenarioError("Scenario name is required.", code="scenario_name_required")
    if PlanScenario.objects.filter(enrollment=source.enrollment, name=normalized_name).exists():
        raise ScenarioError(
            "A scenario with this name already exists.", code="scenario_name_duplicate"
        )
    duplicate = PlanScenario.objects.create(
        enrollment=source.enrollment,
        created_by=actor,
        name=normalized_name,
        target_term=source.target_term,
        status="ACTIVE",
    )
    original_preferences = PlanningPreference.objects.filter(scenario=source).first()
    if original_preferences:
        PlanningPreference.objects.create(
            scenario=duplicate,
            max_credits_per_term=original_preferences.max_credits_per_term,
            min_credits_per_term=original_preferences.min_credits_per_term,
            unavailable_weekdays=original_preferences.unavailable_weekdays,
            preferred_modalities=original_preferences.preferred_modalities,
            preferred_area_codes=original_preferences.preferred_area_codes,
            objective_weights=original_preferences.objective_weights,
        )
    else:
        PlanningPreference.objects.create(scenario=duplicate)
    for item in source.planned_courses.all():
        PlannedCourse.objects.create(
            scenario=duplicate,
            course_version=item.course_version,
            term=item.term,
            section=item.section,
            priority=item.priority,
            source=item.source,
            notes=item.notes,
            is_locked=False,
        )
    recompute_scenario_projection(duplicate)
    return _get_scenario(actor, duplicate.pk, write=True)


def compare_scenarios(actor: Any, left_id: UUID, right_id: UUID) -> dict[str, Any]:
    left = _get_scenario(actor, left_id)
    right = _get_scenario(actor, right_id)
    if left.enrollment_id != right.enrollment_id:
        raise ScenarioError(
            "Only scenarios for the same enrollment can be compared.",
            code="compare_enrollment_mismatch",
        )
    left_items = {
        item.course_version.course.code: item
        for item in left.planned_courses.select_related("course_version__course", "term")
    }
    right_items = {
        item.course_version.course.code: item
        for item in right.planned_courses.select_related("course_version__course", "term")
    }
    added = sorted(set(right_items) - set(left_items))
    removed = sorted(set(left_items) - set(right_items))
    moved = sorted(
        code
        for code in set(left_items) & set(right_items)
        if left_items[code].term_id != right_items[code].term_id
    )
    unchanged = sorted(set(left_items) & set(right_items) - set(moved))
    return {
        "left": {"id": left.pk, "name": left.name, "version": left.version},
        "right": {"id": right.pk, "name": right.name, "version": right.version},
        "added": [
            {"course_code": code, "term_code": right_items[code].term.code} for code in added
        ],
        "removed": [
            {"course_code": code, "term_code": left_items[code].term.code} for code in removed
        ],
        "moved": [
            {
                "course_code": code,
                "from_term": left_items[code].term.code,
                "to_term": right_items[code].term.code,
            }
            for code in moved
        ],
        "unchanged": unchanged,
    }


def shared_scenario_view(actor: Any, token: UUID) -> dict[str, Any]:
    scenario = (
        PlanScenario.objects.filter(share_token=token, sharing_enabled=True)
        .select_related("target_term")
        .prefetch_related("planned_courses__course_version__course", "planned_courses__term")
        .first()
    )
    if scenario is None:
        raise ScenarioError("Shared scenario was not found.", code="share_not_found")
    if not can_view_enrollment(actor, scenario.enrollment):
        raise ScenarioError("You cannot view this private scenario.", code="scenario_forbidden")
    return {
        "id": scenario.pk,
        "name": scenario.name,
        "status": scenario.status,
        "target_term_code": scenario.target_term.code if scenario.target_term else None,
        "planned_courses": [
            {
                "course_code": item.course_version.course.code,
                "course_name": item.course_version.name,
                "credits": item.course_version.credits,
                "term_code": item.term.code,
            }
            for item in scenario.planned_courses.all()
        ],
        "privacy": "No incluye enrollment, estudiante, historial ni auditoría personal.",
    }
