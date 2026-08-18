from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
from typing import Any
from uuid import UUID

from django.db import close_old_connections
from django.utils import timezone

from domain.audit import audit_degree
from domain.audit.engine import AuditInputError
from domain.enums import MembershipRole, RequirementPurpose
from domain.optimization import (
    SOLVER_VERSION,
    UNKNOWN_OFFERING_ALLOW,
    UNKNOWN_OFFERING_REQUIRE,
    CandidateFact,
    CourseFact,
    GroupFact,
    GroupMembershipFact,
    LockedChoice,
    OptimizationInput,
    OptimizationPreferences,
    TermFact,
    solve_optimization,
)
from domain.rules import parse_rule
from domain.rules.ast import Unknown
from domain.rules.errors import RuleSchemaError
from modules.audit.application.overview import (
    ACCEPTED_ATTEMPT_STATUSES,
    IN_PROGRESS_ATTEMPT_STATUSES,
)
from modules.audit.application.services import build_audit_input
from modules.curriculum.models import Course, CourseVersion, PlanMembership
from modules.identity.application.authorization import can_view_enrollment
from modules.observability.metrics import measure_job_timing
from modules.offerings.models import AcademicTerm, CourseOffering
from modules.optimization.models import OptimizationRun
from modules.planning.application.scenarios import (
    _get_scenario,
    _meeting_windows,
    _source_offering_state,
)
from modules.planning.models import PlannedCourse, PlanningPreference, PlanScenario
from modules.rules.models import Requirement

MAX_TIME_LIMIT_SECONDS = 300
MAX_CONCURRENT_OPTIMIZATION_JOBS = 2
MAX_IN_FLIGHT_OPTIMIZATION_JOBS = 20
_executor = ThreadPoolExecutor(
    max_workers=MAX_CONCURRENT_OPTIMIZATION_JOBS,
    thread_name_prefix="curriculum-optimizer",
)
_jobs: dict[str, Event] = {}
_jobs_lock = Lock()


class OptimizationRunError(RuntimeError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _validate_time_limit(value: int) -> int:
    if isinstance(value, bool) or value < 1 or value > MAX_TIME_LIMIT_SECONDS:
        raise OptimizationRunError(
            f"El límite debe estar entre 1 y {MAX_TIME_LIMIT_SECONDS} segundos.",
            code="optimization_time_limit_invalid",
        )
    return value


def _passed_and_in_progress(enrollment: Any) -> tuple[frozenset[str], frozenset[str]]:
    attempts = enrollment.course_attempts.select_related("course_version__course")
    passed = frozenset(
        attempt.course_version.course.code
        for attempt in attempts
        if attempt.status in ACCEPTED_ATTEMPT_STATUSES
    )
    in_progress = frozenset(
        attempt.course_version.course.code
        for attempt in attempts
        if attempt.status in IN_PROGRESS_ATTEMPT_STATUSES
    )
    return passed, in_progress


def _remaining_group_credits(enrollment: Any) -> dict[str, int]:
    groups = {
        group.code: group.required_credits
        for group in enrollment.revision_basis.requirement_groups.all()
    }
    try:
        audit_result = audit_degree(build_audit_input(enrollment))
    except AuditInputError:
        return groups
    return {
        group.code: group.remaining_credits
        for group in audit_result.groups
        if group.remaining_credits > 0
    } | {code: 0 for code in groups if code not in {item.code for item in audit_result.groups}}


def _requirements_by_course(revision_id: UUID) -> dict[str, tuple[Any, ...]]:
    requirements = Requirement.objects.filter(
        revision_id=revision_id,
        owner_type="COURSE",
        purpose__in={
            RequirementPurpose.ENROLLMENT_PREREQUISITE.value,
            RequirementPurpose.COREQUISITE.value,
        },
    ).order_by("code")
    course_codes = {
        str(course.pk): course.code
        for course in Course.objects.filter(pk__in={str(item.owner_id) for item in requirements})
    }
    result: dict[str, list[Any]] = defaultdict(list)
    for requirement in requirements:
        course_code = course_codes.get(str(requirement.owner_id))
        if course_code is None:
            continue
        try:
            rule = parse_rule(requirement.ast)
        except (RuleSchemaError, ValueError) as error:
            rule = Unknown(f"Malformed requirement {requirement.code}: {error}")
        result[course_code].append(rule)
    return {code: tuple(rules) for code, rules in result.items()}


def _course_versions_for_revision(
    enrollment: Any, terms: list[AcademicTerm]
) -> dict[str, CourseVersion]:
    memberships = (
        PlanMembership.objects.filter(revision_id=enrollment.revision_basis_id)
        .select_related("course_version__course", "group")
        .order_by(
            "course_version__course__code", "-course_version__valid_from", "course_version_id"
        )
    )
    versions: dict[str, CourseVersion] = {}
    reference_date = min((term.starts_at.date() for term in terms), default=None)
    for membership in memberships:
        version = membership.course_version
        code = version.course.code
        if code not in versions or (
            reference_date is not None
            and version.valid_from <= reference_date
            and versions[code].valid_from > reference_date
        ):
            versions[code] = version
    planned = PlannedCourse.objects.filter(scenario__enrollment=enrollment).select_related(
        "course_version__course"
    )
    for item in planned:
        versions.setdefault(item.course_version.course.code, item.course_version)
    return versions


def build_optimization_input(
    scenario: PlanScenario,
    *,
    time_limit_seconds: int,
    unknown_offering_policy: str = UNKNOWN_OFFERING_ALLOW,
    credit_target: int | None = None,
    preferred_credits_per_term: int | None = None,
    random_seed: int = 0,
) -> OptimizationInput:
    time_limit_seconds = _validate_time_limit(time_limit_seconds)
    if unknown_offering_policy not in {UNKNOWN_OFFERING_ALLOW, UNKNOWN_OFFERING_REQUIRE}:
        raise OptimizationRunError(
            "La política de oferta desconocida no es válida.",
            code="optimization_request_invalid",
        )
    enrollment = scenario.enrollment
    if enrollment.status == "NEEDS_REVIEW":
        raise OptimizationRunError(
            "La revisión curricular de la matrícula debe confirmarse antes de optimizar una ruta.",
            code="enrollment_needs_review",
        )
    terms = list(
        AcademicTerm.objects.filter(institution_id=enrollment.student.institution_id).order_by(
            "starts_at", "code"
        )
    )
    if not terms:
        raise OptimizationRunError(
            "No hay períodos académicos verificables para optimizar.",
            code="optimization_terms_unknown",
        )
    term_facts = tuple(
        TermFact(
            code=term.code,
            order=index,
            starts_on=term.starts_at.date(),
            ends_on=term.ends_at.date(),
        )
        for index, term in enumerate(terms)
    )
    versions = _course_versions_for_revision(enrollment, terms)
    memberships = (
        PlanMembership.objects.filter(revision_id=enrollment.revision_basis_id)
        .select_related("course_version__course", "group")
        .order_by("course_version__course__code", "group__code")
    )
    memberships_by_code: dict[str, list[GroupMembershipFact]] = defaultdict(list)
    mandatory_by_code: set[str] = set()
    for membership in memberships:
        code = membership.course_version.course.code
        memberships_by_code[code].append(
            GroupMembershipFact(
                group_code=membership.group.code,
                role=membership.role,
                count_policy=membership.count_policy,
            )
        )
        if membership.role == MembershipRole.MANDATORY.value:
            mandatory_by_code.add(code)
    requirements = _requirements_by_course(enrollment.revision_basis_id)
    courses = tuple(
        CourseFact(
            id=str(version.pk),
            code=code,
            credits=version.credits,
            mandatory=code in mandatory_by_code,
            memberships=tuple(memberships_by_code.get(code, [])),
            prerequisite_rules=requirements.get(code, ()),
            preference_penalty=int(version.metadata.get("optimization_penalty", 0))
            if isinstance(version.metadata, dict)
            else 0,
            area_code=str(version.metadata.get("area_code"))
            if isinstance(version.metadata, dict) and version.metadata.get("area_code")
            else None,
        )
        for code, version in sorted(versions.items())
    )
    groups = tuple(
        GroupFact(code=code, required_credits=credits, label=code)
        for code, credits in sorted(_remaining_group_credits(enrollment).items())
    )
    version_ids = [version.pk for version in versions.values()]
    term_ids = [term.pk for term in terms]
    offerings = {
        (offering.course_version_id, offering.term_id): offering
        for offering in CourseOffering.objects.filter(
            course_version_id__in=version_ids, term_id__in=term_ids
        ).select_related("term")
    }
    planned = list(
        scenario.planned_courses.select_related(
            "course_version__course", "term", "section"
        ).prefetch_related("section__meetings")
    )
    planned_by_key = {(item.course_version.course.code, item.term_id): item for item in planned}
    candidates: list[CandidateFact] = []
    for course in courses:
        version = versions[course.code]
        for term in terms:
            existing = planned_by_key.get((course.code, term.pk))
            offering = offerings.get((version.pk, term.pk))
            selected_section = existing.section if existing is not None else None
            candidates.append(
                CandidateFact(
                    course_id=str(version.pk),
                    course_code=course.code,
                    term_code=term.code,
                    offering_state=_source_offering_state(offering),
                    selected_section_id=str(selected_section.pk) if selected_section else None,
                    meetings=_meeting_windows(selected_section),
                )
            )
    locked_choices = tuple(
        LockedChoice(
            course_code=item.course_version.course.code,
            term_code=item.term.code,
            selected_section_id=str(item.section_id) if item.section_id else None,
        )
        for item in planned
        if item.is_locked
    )
    preference = PlanningPreference.objects.get_or_create(scenario=scenario)[0]
    passed, in_progress = _passed_and_in_progress(enrollment)
    try:
        optimization_preferences = OptimizationPreferences(
            min_credits_per_term=preference.min_credits_per_term,
            max_credits_per_term=preference.max_credits_per_term,
            unknown_offering_policy=unknown_offering_policy,
            credit_target=credit_target,
            preferred_credits_per_term=preferred_credits_per_term,
            random_seed=random_seed,
            time_limit_seconds=time_limit_seconds,
        )
    except ValueError as error:
        raise OptimizationRunError(str(error), code="optimization_request_invalid") from error
    return OptimizationInput(
        revision_id=str(enrollment.revision_basis_id),
        revision_hash=enrollment.revision_basis.content_hash or str(enrollment.revision_basis_id),
        terms=term_facts,
        courses=courses,
        groups=groups,
        candidates=tuple(candidates),
        passed_courses=passed,
        in_progress_courses=in_progress,
        locked_choices=locked_choices,
        preferences=optimization_preferences,
    )


def _assert_owner(actor: Any, run: OptimizationRun) -> None:
    if not can_view_enrollment(actor, run.scenario.enrollment):
        raise OptimizationRunError(
            "No puedes ver esta optimización.", code="optimization_forbidden"
        )


def _run_view(run: OptimizationRun) -> dict[str, Any]:
    return {
        "id": run.pk,
        "scenario_id": run.scenario_id,
        "input_hash": run.input_hash,
        "output_hash": run.output_hash,
        "solver_version": run.solver_version,
        "status": run.status,
        "objective_values": run.objective_values if isinstance(run.objective_values, list) else [],
        "solution": run.solution,
        "explanation": run.explanation,
        "time_limit_seconds": run.time_limit_seconds,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "cancel_requested_at": run.cancel_requested_at,
        "completed_at": run.completed_at,
    }


def create_optimization_run(
    actor: Any,
    scenario_id: UUID,
    *,
    time_limit_seconds: int = 30,
    unknown_offering_policy: str = UNKNOWN_OFFERING_ALLOW,
    credit_target: int | None = None,
    preferred_credits_per_term: int | None = None,
    random_seed: int = 0,
) -> OptimizationRun:
    scenario = _get_scenario(actor, scenario_id, write=True)
    input_data = build_optimization_input(
        scenario,
        time_limit_seconds=time_limit_seconds,
        unknown_offering_policy=unknown_offering_policy,
        credit_target=credit_target,
        preferred_credits_per_term=preferred_credits_per_term,
        random_seed=random_seed,
    )
    run = OptimizationRun.objects.create(
        scenario=scenario,
        input_hash=input_data.input_hash,
        input_snapshot=input_data.to_dict(),
        solver_version=SOLVER_VERSION,
        status="QUEUED",
        time_limit_seconds=input_data.preferences.time_limit_seconds,
    )
    try:
        submit_optimization_run(run.pk)
    except OptimizationRunError as error:
        run.status = "REJECTED"
        run.explanation = {
            "conflicts": [],
            "assumptions": [],
            "termination_reason": error.code,
            "detail": str(error),
        }
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "explanation", "completed_at", "updated_at"])
        raise
    return run


@measure_job_timing("optimizer")
def execute_optimization_run(
    run_id: UUID | str, cancel_event: Event | None = None
) -> OptimizationRun:
    run = OptimizationRun.objects.select_related("scenario__enrollment__student").get(pk=run_id)
    if run.status == "QUEUED":
        run.status = "RUNNING"
        run.started_at = timezone.now()
        run.save(update_fields=["status", "started_at", "updated_at"])
    input_data = OptimizationInput.from_dict(run.input_snapshot)
    result = solve_optimization(input_data, cancel_event=cancel_event)
    run.status = result.status
    run.output_hash = result.output_hash
    run.objective_values = [item.to_dict() for item in result.objectives]
    run.solution = {
        "selected_courses": [item.to_dict() for item in result.selected_courses],
        "status": result.status,
    }
    run.explanation = {
        "explanations": [item.to_dict() for item in result.explanations],
        "conflicts": list(result.conflicts),
        "assumptions": list(result.assumptions),
        "termination_reason": result.termination_reason,
        "wall_time_seconds": result.wall_time_seconds,
    }
    run.completed_at = timezone.now()
    run.save(
        update_fields=[
            "status",
            "output_hash",
            "objective_values",
            "solution",
            "explanation",
            "completed_at",
            "updated_at",
        ]
    )
    return run


def submit_optimization_run(run_id: UUID | str) -> None:
    key = str(run_id)
    event = Event()
    with _jobs_lock:
        if len(_jobs) >= MAX_IN_FLIGHT_OPTIMIZATION_JOBS:
            raise OptimizationRunError(
                "Se alcanzó la capacidad temporal de ejecuciones de optimización. "
                "Intenta de nuevo cuando finalice una ejecución.",
                code="optimization_capacity",
            )
        _jobs[key] = event
    try:
        _executor.submit(_execute_job, key, event)
    except Exception:
        with _jobs_lock:
            _jobs.pop(key, None)
        raise


def _execute_job(run_id: str, event: Event) -> None:
    close_old_connections()
    try:
        execute_optimization_run(run_id, event)
    finally:
        close_old_connections()
        with _jobs_lock:
            _jobs.pop(run_id, None)


def cancel_optimization_run(actor: Any, run_id: UUID) -> OptimizationRun:
    try:
        run = OptimizationRun.objects.select_related("scenario__enrollment__student").get(pk=run_id)
    except OptimizationRun.DoesNotExist as error:
        raise OptimizationRunError(
            "La ejecución no existe.", code="optimization_not_found"
        ) from error
    _assert_owner(actor, run)
    if run.status in {"QUEUED", "RUNNING"}:
        with _jobs_lock:
            event = _jobs.get(str(run.pk))
        if event is not None:
            event.set()
        run.cancel_requested_at = timezone.now()
        run.save(update_fields=["cancel_requested_at", "updated_at"])
    return run


def get_optimization_run(actor: Any, run_id: UUID) -> OptimizationRun:
    try:
        run = OptimizationRun.objects.select_related("scenario__enrollment__student").get(pk=run_id)
    except OptimizationRun.DoesNotExist as error:
        raise OptimizationRunError(
            "La ejecución no existe.", code="optimization_not_found"
        ) from error
    _assert_owner(actor, run)
    return run


def list_optimization_runs(actor: Any, scenario_id: UUID) -> list[dict[str, Any]]:
    scenario = _get_scenario(actor, scenario_id)
    return [
        _run_view(run)
        for run in OptimizationRun.objects.filter(scenario=scenario).order_by("-created_at")[:20]
    ]


def optimization_run_view(run: OptimizationRun) -> dict[str, Any]:
    return _run_view(run)
