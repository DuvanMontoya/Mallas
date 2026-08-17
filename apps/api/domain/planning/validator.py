from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from domain.offerings.schedule import MeetingWindow, evaluate_schedule
from domain.rules.ast import (
    All,
    AnyOf,
    AuditRule,
    Corequisite,
    CourseInProgress,
    CoursePassed,
    CoursePassedOrInProgress,
    CreditsInComponent,
    CreditsInGroup,
    EquivalentCoursePassed,
    ExternalRequirement,
    GroupCompleted,
    MandatoryCoursesCompleted,
    MinimumGrade,
    Not,
    PercentageOfPlan,
    TotalCredits,
    Unknown,
)

SATISFIED = "SATISFIED"
UNSATISFIED = "UNSATISFIED"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class PlannedCourseFact:
    id: str
    course_code: str
    term_code: str
    term_order: int
    credits: int | None
    offering_state: str
    section_id: str | None = None
    modality: str | None = None
    meetings: tuple[MeetingWindow, ...] = ()


@dataclass(frozen=True, slots=True)
class RequirementFact:
    code: str
    course_code: str
    rule: AuditRule | None
    epistemic_status: str = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ValidationWarning:
    code: str
    detail: str
    severity: str = "WARNING"
    course_code: str | None = None
    term_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "detail": self.detail,
            "severity": self.severity,
            "course_code": self.course_code,
            "term_code": self.term_code,
        }


@dataclass(frozen=True, slots=True)
class CourseValidation:
    planned_course_id: str
    course_code: str
    term_code: str
    prerequisite_state: str
    offering_state: str
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "planned_course_id": self.planned_course_id,
            "course_code": self.course_code,
            "term_code": self.term_code,
            "prerequisite_state": self.prerequisite_state,
            "offering_state": self.offering_state,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class ScenarioValidation:
    state: str
    courses: tuple[CourseValidation, ...]
    warnings: tuple[ValidationWarning, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "courses": [course.to_dict() for course in self.courses],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }


@dataclass(frozen=True, slots=True)
class _Outcome:
    status: str
    reasons: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _Facts:
    passed: frozenset[str]
    in_progress: frozenset[str]
    planned_terms: Mapping[str, tuple[int, ...]]
    projected_credits: Mapping[int, int]
    plan_total_credits: int | None


def _combine_all(outcomes: Sequence[_Outcome]) -> _Outcome:
    if any(item.status == UNSATISFIED for item in outcomes):
        status = UNSATISFIED
    elif any(item.status == UNKNOWN for item in outcomes):
        status = UNKNOWN
    elif all(item.status == NOT_APPLICABLE for item in outcomes):
        status = NOT_APPLICABLE
    else:
        status = SATISFIED
    return _Outcome(
        status,
        tuple(reason for item in outcomes for reason in item.reasons),
        tuple(reason for item in outcomes for reason in item.unknowns),
    )


def _combine_any(outcomes: Sequence[_Outcome]) -> _Outcome:
    if any(item.status == SATISFIED for item in outcomes):
        status = SATISFIED
    elif any(item.status == UNKNOWN for item in outcomes):
        status = UNKNOWN
    elif all(item.status == NOT_APPLICABLE for item in outcomes):
        status = NOT_APPLICABLE
    else:
        status = UNSATISFIED
    return _Outcome(
        status,
        tuple(reason for item in outcomes for reason in item.reasons),
        tuple(reason for item in outcomes for reason in item.unknowns),
    )


def _planned_at_or_before(facts: _Facts, code: str, term_order: int) -> bool:
    return any(order <= term_order for order in facts.planned_terms.get(code, ()))


def _planned_before(facts: _Facts, code: str, term_order: int) -> bool:
    return any(order < term_order for order in facts.planned_terms.get(code, ()))


def _course_outcome(
    code: str,
    *,
    term_order: int,
    facts: _Facts,
    mode: str,
) -> _Outcome:
    if code in facts.passed or code in facts.in_progress:
        return _Outcome(SATISFIED)
    if mode == "passed":
        if _planned_before(facts, code, term_order):
            return _Outcome(SATISFIED)
        if _planned_at_or_before(facts, code, term_order):
            return _Outcome(UNSATISFIED, (f"PREREQUISITE_ORDERING:{code}",))
        return _Outcome(UNSATISFIED, (f"PREREQUISITE_MISSING:{code}",))
    if mode in {"in_progress", "passed_or_in_progress", "corequisite"}:
        if _planned_at_or_before(facts, code, term_order):
            return _Outcome(SATISFIED)
        if mode == "corequisite" and facts.planned_terms.get(code):
            return _Outcome(UNSATISFIED, (f"COREQUISITE_ORDERING:{code}",))
        prefix = "COREQUISITE_MISSING" if mode == "corequisite" else "PREREQUISITE_MISSING"
        return _Outcome(UNSATISFIED, (f"{prefix}:{code}",))
    return _Outcome(UNKNOWN, unknowns=(f"COURSE_RULE_UNKNOWN:{code}",))


def _evaluate_rule(rule: AuditRule, *, term_order: int, facts: _Facts) -> _Outcome:
    if isinstance(rule, All):
        return _combine_all(
            [_evaluate_rule(child, term_order=term_order, facts=facts) for child in rule.children]
        )
    if isinstance(rule, AnyOf):
        return _combine_any(
            [_evaluate_rule(child, term_order=term_order, facts=facts) for child in rule.children]
        )
    if isinstance(rule, Not):
        child = _evaluate_rule(rule.child, term_order=term_order, facts=facts)
        status = {
            SATISFIED: UNSATISFIED,
            UNSATISFIED: SATISFIED,
            UNKNOWN: UNKNOWN,
            NOT_APPLICABLE: NOT_APPLICABLE,
        }[child.status]
        return _Outcome(status, child.reasons, child.unknowns)
    if isinstance(rule, CoursePassed):
        return _course_outcome(rule.course_code, term_order=term_order, facts=facts, mode="passed")
    if isinstance(rule, CourseInProgress):
        return _course_outcome(
            rule.course_code, term_order=term_order, facts=facts, mode="in_progress"
        )
    if isinstance(rule, CoursePassedOrInProgress):
        return _course_outcome(
            rule.course_code, term_order=term_order, facts=facts, mode="passed_or_in_progress"
        )
    if isinstance(rule, Corequisite):
        return _course_outcome(
            rule.course_code, term_order=term_order, facts=facts, mode="corequisite"
        )
    if isinstance(rule, MandatoryCoursesCompleted):
        return _combine_all(
            [
                _course_outcome(code, term_order=term_order, facts=facts, mode="passed")
                for code in rule.course_codes
            ]
        )
    if isinstance(rule, EquivalentCoursePassed):
        return _combine_any(
            [
                _course_outcome(code, term_order=term_order, facts=facts, mode="passed")
                for code in rule.course_codes
            ]
        )
    if isinstance(rule, TotalCredits):
        current = sum(
            credits for order, credits in facts.projected_credits.items() if order <= term_order
        )
        satisfied = {
            ">=": current >= rule.value,
            ">": current > rule.value,
            "=": current == rule.value,
            "<=": current <= rule.value,
            "<": current < rule.value,
        }[rule.operator]
        return _Outcome(SATISFIED if satisfied else UNSATISFIED)
    if isinstance(rule, PercentageOfPlan):
        if facts.plan_total_credits is None:
            return _Outcome(UNKNOWN, unknowns=("PLAN_TOTAL_CREDITS_UNKNOWN",))
        current = sum(
            credits for order, credits in facts.projected_credits.items() if order <= term_order
        )
        return _Outcome(
            SATISFIED
            if current * rule.denominator >= facts.plan_total_credits * rule.numerator
            else UNSATISFIED
        )
    if isinstance(rule, (CreditsInGroup, CreditsInComponent, GroupCompleted, MinimumGrade)):
        return _Outcome(UNKNOWN, unknowns=(f"RULE_NOT_PROJECTED:{type(rule).__name__}",))
    if isinstance(rule, (ExternalRequirement, Unknown)):
        return _Outcome(UNKNOWN, unknowns=(f"RULE_UNKNOWN:{type(rule).__name__}",))
    return _Outcome(UNKNOWN, unknowns=(f"RULE_UNKNOWN:{type(rule).__name__}",))


def validate_scenario(
    planned_courses: Sequence[PlannedCourseFact],
    *,
    requirements_by_course: Mapping[str, Sequence[RequirementFact]],
    passed_courses: frozenset[str] = frozenset(),
    in_progress_courses: frozenset[str] = frozenset(),
    unavailable_weekdays: frozenset[int] = frozenset(),
    min_credits_per_term: int = 0,
    max_credits_per_term: int = 18,
    plan_total_credits: int | None = None,
    term_ranges: Mapping[str, tuple[date, date]] | None = None,
) -> ScenarioValidation:
    ordered = tuple(
        sorted(planned_courses, key=lambda item: (item.term_order, item.course_code, item.id))
    )
    planned_terms: dict[str, list[int]] = defaultdict(list)
    for item in ordered:
        planned_terms[item.course_code].append(item.term_order)
    term_credits: dict[int, int] = defaultdict(int)
    for item in ordered:
        term_credits[item.term_order] += item.credits or 0
    facts = _Facts(
        passed=passed_courses,
        in_progress=in_progress_courses,
        planned_terms={code: tuple(values) for code, values in planned_terms.items()},
        projected_credits={key: value for key, value in term_credits.items()},
        plan_total_credits=plan_total_credits,
    )
    warnings: list[ValidationWarning] = []
    courses: list[CourseValidation] = []
    seen_codes: set[str] = set()
    meetings_by_term: dict[str, list[MeetingWindow]] = defaultdict(list)
    for item in ordered:
        reasons: list[str] = []
        requirements = requirements_by_course.get(item.course_code, ())
        outcomes = [
            _evaluate_rule(requirement.rule, term_order=item.term_order, facts=facts)
            for requirement in requirements
            if requirement.rule is not None
            and requirement.epistemic_status not in {"UNKNOWN", "DISPUTED", "SUPERSEDED"}
        ]
        if not requirements:
            prerequisite = _Outcome(
                UNKNOWN, unknowns=(f"PREREQUISITE_RULE_UNKNOWN:{item.course_code}",)
            )
        elif not outcomes:
            prerequisite = _Outcome(
                UNKNOWN, unknowns=(f"PREREQUISITE_RULE_NOT_VERIFIED:{item.course_code}",)
            )
        else:
            prerequisite = _combine_all(outcomes)
        reasons.extend(prerequisite.reasons)
        reasons.extend(prerequisite.unknowns)
        if item.course_code in seen_codes:
            warnings.append(
                ValidationWarning(
                    "DUPLICATE_COURSE",
                    f"{item.course_code} está planificado más de una vez; confirma la política de repetición.",
                    course_code=item.course_code,
                    term_code=item.term_code,
                )
            )
        seen_codes.add(item.course_code)
        if prerequisite.status == UNSATISFIED:
            warnings.append(
                ValidationWarning(
                    "PREREQUISITE_BLOCKED",
                    f"{item.course_code} tiene prerrequisitos o correquisitos no satisfechos.",
                    course_code=item.course_code,
                    term_code=item.term_code,
                )
            )
        elif prerequisite.status == UNKNOWN:
            warnings.append(
                ValidationWarning(
                    "PREREQUISITE_UNKNOWN",
                    f"No se puede verificar completamente la regla de {item.course_code}.",
                    course_code=item.course_code,
                    term_code=item.term_code,
                )
            )
        if item.offering_state == "NOT_OFFERED":
            warnings.append(
                ValidationWarning(
                    "OFFERING_NOT_REPORTED",
                    f"No hay oferta reportada para {item.course_code} en {item.term_code}.",
                    course_code=item.course_code,
                    term_code=item.term_code,
                )
            )
        elif item.offering_state == "UNKNOWN":
            warnings.append(
                ValidationWarning(
                    "OFFERING_UNKNOWN",
                    f"La oferta de {item.course_code} en {item.term_code} no tiene evidencia suficiente.",
                    course_code=item.course_code,
                    term_code=item.term_code,
                )
            )
        if item.credits is None:
            warnings.append(
                ValidationWarning(
                    "CREDITS_UNKNOWN",
                    f"No se conocen los créditos proyectados de {item.course_code}.",
                    course_code=item.course_code,
                    term_code=item.term_code,
                )
            )
        for meeting in item.meetings:
            meetings_by_term[item.term_code].append(meeting)
            if meeting.day_of_week in unavailable_weekdays:
                warnings.append(
                    ValidationWarning(
                        "UNAVAILABLE_WEEKDAY",
                        f"El grupo seleccionado de {item.course_code} usa un día no disponible.",
                        course_code=item.course_code,
                        term_code=item.term_code,
                    )
                )
        courses.append(
            CourseValidation(
                planned_course_id=item.id,
                course_code=item.course_code,
                term_code=item.term_code,
                prerequisite_state=prerequisite.status,
                offering_state=item.offering_state,
                reasons=tuple(dict.fromkeys(reasons)),
            )
        )
    for order, credits in sorted(term_credits.items()):
        term_code = next((item.term_code for item in ordered if item.term_order == order), None)
        if credits > max_credits_per_term:
            warnings.append(
                ValidationWarning(
                    "CREDITS_ABOVE_MAX",
                    f"El término tiene {credits} créditos y el límite es {max_credits_per_term}.",
                    term_code=term_code,
                )
            )
        if credits < min_credits_per_term:
            warnings.append(
                ValidationWarning(
                    "CREDITS_BELOW_MIN",
                    f"El término tiene {credits} créditos y el mínimo es {min_credits_per_term}.",
                    term_code=term_code,
                )
            )
    ranges = term_ranges or {}
    for term_code, meetings in sorted(meetings_by_term.items()):
        start, end = ranges.get(term_code, (date.min, date.max))
        schedule = evaluate_schedule(meetings, term_start=start, term_end=end)
        if schedule.state == "CONFLICT":
            warnings.append(
                ValidationWarning(
                    "SCHEDULE_CONFLICT",
                    f"Hay {len(schedule.conflicts)} solapamientos de horario en {term_code}.",
                    term_code=term_code,
                )
            )
        elif schedule.state == "UNKNOWN":
            warnings.append(
                ValidationWarning(
                    "SCHEDULE_UNKNOWN",
                    "; ".join(schedule.unknown_reasons),
                    term_code=term_code,
                )
            )
    state = "VALID" if not warnings else "WARNINGS"
    return ScenarioValidation(
        state=state,
        courses=tuple(courses),
        warnings=tuple(warnings),
    )
