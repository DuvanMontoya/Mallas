from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from .ast import (
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
    canonical_rule_json,
)
from .errors import RuleEvaluationError


class EvaluationStatus(StrEnum):
    SATISFIED = "SATISFIED"
    UNSATISFIED = "UNSATISFIED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class RevisionFacts:
    total_credits: int | None = None
    group_required_credits: Mapping[str, int] = field(default_factory=dict)
    component_required_credits: Mapping[str, int] = field(default_factory=dict)
    mandatory_courses_by_group: Mapping[str, frozenset[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.total_credits is not None and (
            isinstance(self.total_credits, bool) or self.total_credits < 0
        ):
            raise RuleEvaluationError("revision.total_credits must be a non-negative integer")
        _validate_nonnegative_mapping(self.group_required_credits, "group_required_credits")
        _validate_nonnegative_mapping(self.component_required_credits, "component_required_credits")


@dataclass(frozen=True, slots=True)
class AuditContext:
    """Immutable facts supplied by an application layer; the evaluator never queries."""

    revision: RevisionFacts | None = None
    passed_courses: frozenset[str] = field(default_factory=frozenset)
    in_progress_courses: frozenset[str] = field(default_factory=frozenset)
    unknown_courses: frozenset[str] = field(default_factory=frozenset)
    earned_credits: int = 0
    allocated_credits: int | None = None
    group_credits: Mapping[str, int | None] = field(default_factory=dict)
    component_credits: Mapping[str, int | None] = field(default_factory=dict)
    group_facts: Mapping[str, int | None] | None = None
    component_facts: Mapping[str, int | None] | None = None
    external_requirements: Mapping[str, EvaluationStatus | bool | None] = field(
        default_factory=dict
    )
    recognitions: Mapping[str, frozenset[str]] = field(default_factory=dict)
    grades: Mapping[str, Decimal | str | int] = field(default_factory=dict)
    not_applicable_keys: frozenset[str] = field(default_factory=frozenset)
    evidence_refs: tuple[str, ...] = ()
    exceptions: Mapping[str, EvaluationStatus | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("earned_credits", "allocated_credits"):
            value = getattr(self, field_name)
            if value is not None and (isinstance(value, bool) or value < 0):
                raise RuleEvaluationError(f"{field_name} must be a non-negative integer")
        _validate_optional_nonnegative_mapping(self.group_credits, "group_credits")
        _validate_optional_nonnegative_mapping(self.component_credits, "component_credits")
        if self.group_facts is not None:
            _validate_optional_nonnegative_mapping(self.group_facts, "group_facts")
            if not self.group_credits:
                object.__setattr__(self, "group_credits", dict(self.group_facts))
        if self.component_facts is not None:
            _validate_optional_nonnegative_mapping(self.component_facts, "component_facts")
            if not self.component_credits:
                object.__setattr__(self, "component_credits", dict(self.component_facts))
        object.__setattr__(self, "passed_courses", frozenset(self.passed_courses))
        object.__setattr__(self, "in_progress_courses", frozenset(self.in_progress_courses))
        object.__setattr__(self, "unknown_courses", frozenset(self.unknown_courses))
        object.__setattr__(self, "not_applicable_keys", frozenset(self.not_applicable_keys))
        object.__setattr__(self, "evidence_refs", tuple(dict.fromkeys(self.evidence_refs)))


@dataclass(frozen=True, slots=True)
class Progress:
    current: int
    required: int
    unit: str

    def to_dict(self) -> dict[str, Any]:
        return {"current": self.current, "required": self.required, "unit": self.unit}


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    status: EvaluationStatus
    progress: Progress
    children: tuple[EvaluationResult, ...] = ()
    evidence: tuple[str, ...] = ()
    explanation_key: str = "rule.unknown"
    facts_used: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "children", tuple(self.children))
        object.__setattr__(self, "evidence", tuple(dict.fromkeys(self.evidence)))
        object.__setattr__(self, "facts_used", tuple(dict.fromkeys(self.facts_used)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "progress": self.progress.to_dict(),
            "children": [child.to_dict() for child in self.children],
            "evidence": list(self.evidence),
            "explanation_key": self.explanation_key,
            "facts_used": list(self.facts_used),
        }


def _validate_nonnegative_mapping(values: Mapping[str, int], field_name: str) -> None:
    for key, value in values.items():
        if not isinstance(key, str) or not key:
            raise RuleEvaluationError(f"{field_name} keys must be non-empty strings")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise RuleEvaluationError(f"{field_name}[{key!r}] must be a non-negative integer")


def _validate_optional_nonnegative_mapping(
    values: Mapping[str, int | None], field_name: str
) -> None:
    for key, value in values.items():
        if not isinstance(key, str) or not key:
            raise RuleEvaluationError(f"{field_name} keys must be non-empty strings")
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise RuleEvaluationError(f"{field_name}[{key!r}] must be an integer or None")


def _facts(*values: str) -> tuple[str, ...]:
    return tuple(values)


def _compare(current: int, operator: str, required: int) -> bool:
    return {
        ">=": current >= required,
        ">": current > required,
        "=": current == required,
        "<=": current <= required,
        "<": current < required,
    }[operator]


def _unknown(message_key: str, facts: tuple[str, ...] = ()) -> EvaluationResult:
    return EvaluationResult(
        status=EvaluationStatus.UNKNOWN,
        progress=Progress(0, 1, "boolean"),
        explanation_key=message_key,
        facts_used=facts,
    )


def _boolean(
    status: EvaluationStatus,
    *,
    key: str,
    facts: tuple[str, ...] = (),
) -> EvaluationResult:
    return EvaluationResult(
        status=status,
        progress=Progress(
            1 if status == EvaluationStatus.SATISFIED else 0,
            1,
            "boolean",
        ),
        explanation_key=key,
        facts_used=facts,
    )


def _combine_all(children: tuple[EvaluationResult, ...]) -> EvaluationStatus:
    statuses = {child.status for child in children}
    if EvaluationStatus.UNSATISFIED in statuses:
        return EvaluationStatus.UNSATISFIED
    if EvaluationStatus.UNKNOWN in statuses:
        return EvaluationStatus.UNKNOWN
    if statuses == {EvaluationStatus.NOT_APPLICABLE}:
        return EvaluationStatus.NOT_APPLICABLE
    return EvaluationStatus.SATISFIED


def _combine_any(children: tuple[EvaluationResult, ...]) -> EvaluationStatus:
    statuses = {child.status for child in children}
    if EvaluationStatus.SATISFIED in statuses:
        return EvaluationStatus.SATISFIED
    if EvaluationStatus.UNKNOWN in statuses:
        return EvaluationStatus.UNKNOWN
    if statuses == {EvaluationStatus.NOT_APPLICABLE}:
        return EvaluationStatus.NOT_APPLICABLE
    return EvaluationStatus.UNSATISFIED


def _aggregate(
    status: EvaluationStatus,
    children: tuple[EvaluationResult, ...],
    *,
    key: str,
) -> EvaluationResult:
    facts = tuple(fact for child in children for fact in child.facts_used)
    evidence = tuple(ref for child in children for ref in child.evidence)
    if key == "rule.all":
        current = sum(child.status == EvaluationStatus.SATISFIED for child in children)
        required = len(children)
    else:
        current = int(any(child.status == EvaluationStatus.SATISFIED for child in children))
        required = 1
    return EvaluationResult(
        status=status,
        progress=Progress(current, required, "boolean"),
        children=children,
        evidence=evidence,
        explanation_key=key,
        facts_used=facts,
    )


def _effective_credits(context: AuditContext) -> int:
    return (
        context.allocated_credits
        if context.allocated_credits is not None
        else context.earned_credits
    )


def _parse_context_grade(value: Decimal | str | int) -> Decimal | None:
    try:
        grade = value if isinstance(value, Decimal) else Decimal(str(value))
    except InvalidOperation, ValueError:
        return None
    return grade if grade.is_finite() else None


def _evaluate(rule: AuditRule, context: AuditContext) -> EvaluationResult:
    if canonical_rule_json(rule) in context.not_applicable_keys:
        return EvaluationResult(
            status=EvaluationStatus.NOT_APPLICABLE,
            progress=Progress(0, 0, "boolean"),
            explanation_key="rule.not_applicable",
        )

    if isinstance(rule, All):
        children = tuple(_evaluate(child, context) for child in rule.children)
        return _aggregate(_combine_all(children), children, key="rule.all")
    if isinstance(rule, AnyOf):
        children = tuple(_evaluate(child, context) for child in rule.children)
        return _aggregate(_combine_any(children), children, key="rule.any")
    if isinstance(rule, Not):
        child = _evaluate(rule.child, context)
        status = {
            EvaluationStatus.SATISFIED: EvaluationStatus.UNSATISFIED,
            EvaluationStatus.UNSATISFIED: EvaluationStatus.SATISFIED,
            EvaluationStatus.UNKNOWN: EvaluationStatus.UNKNOWN,
            EvaluationStatus.NOT_APPLICABLE: EvaluationStatus.NOT_APPLICABLE,
        }[child.status]
        return EvaluationResult(
            status=status,
            progress=Progress(1 if status == EvaluationStatus.SATISFIED else 0, 1, "boolean"),
            children=(child,),
            evidence=child.evidence,
            explanation_key="rule.not",
            facts_used=child.facts_used,
        )
    if isinstance(rule, CoursePassed):
        code = rule.course_code
        if code in context.unknown_courses:
            return _unknown("rule.course_passed.unknown", _facts(f"course:{code}:unknown"))
        status = (
            EvaluationStatus.SATISFIED
            if code in context.passed_courses
            else EvaluationStatus.UNSATISFIED
        )
        return _boolean(status, key="rule.course_passed", facts=_facts(f"passed_courses:{code}"))
    if isinstance(rule, CourseInProgress):
        code = rule.course_code
        if code in context.unknown_courses:
            return _unknown("rule.course_in_progress.unknown", _facts(f"course:{code}:unknown"))
        status = (
            EvaluationStatus.SATISFIED
            if code in context.in_progress_courses
            else EvaluationStatus.UNSATISFIED
        )
        return _boolean(status, key="rule.course_in_progress", facts=_facts(f"in_progress:{code}"))
    if isinstance(rule, CoursePassedOrInProgress):
        code = rule.course_code
        if code in context.unknown_courses:
            return _unknown(
                "rule.course_passed_or_in_progress.unknown", _facts(f"course:{code}:unknown")
            )
        status = (
            EvaluationStatus.SATISFIED
            if code in context.passed_courses or code in context.in_progress_courses
            else EvaluationStatus.UNSATISFIED
        )
        return _boolean(
            status,
            key="rule.course_passed_or_in_progress",
            facts=_facts(f"passed_or_in_progress:{code}"),
        )
    if isinstance(rule, Corequisite):
        code = rule.course_code
        if code in context.unknown_courses:
            return _unknown("rule.corequisite.unknown", _facts(f"course:{code}:unknown"))
        status = (
            EvaluationStatus.SATISFIED
            if code in context.passed_courses or code in context.in_progress_courses
            else EvaluationStatus.UNSATISFIED
        )
        return _boolean(status, key="rule.corequisite", facts=_facts(f"corequisite:{code}"))
    if isinstance(rule, CreditsInGroup):
        current = context.group_credits.get(rule.group)
        if current is None:
            return _unknown("rule.credits_in_group.unknown", _facts(f"group:{rule.group}:unknown"))
        status = (
            EvaluationStatus.SATISFIED
            if _compare(current, rule.operator, rule.value)
            else EvaluationStatus.UNSATISFIED
        )
        return EvaluationResult(
            status=status,
            progress=Progress(current, rule.value, "credits"),
            explanation_key="rule.credits_in_group",
            facts_used=_facts(f"group_credits:{rule.group}={current}"),
        )
    if isinstance(rule, CreditsInComponent):
        current = context.component_credits.get(rule.component)
        if current is None:
            return _unknown(
                "rule.credits_in_component.unknown",
                _facts(f"component:{rule.component}:unknown"),
            )
        status = (
            EvaluationStatus.SATISFIED
            if _compare(current, rule.operator, rule.value)
            else EvaluationStatus.UNSATISFIED
        )
        return EvaluationResult(
            status=status,
            progress=Progress(current, rule.value, "credits"),
            explanation_key="rule.credits_in_component",
            facts_used=_facts(f"component_credits:{rule.component}={current}"),
        )
    if isinstance(rule, TotalCredits):
        current = _effective_credits(context)
        status = (
            EvaluationStatus.SATISFIED
            if _compare(current, rule.operator, rule.value)
            else EvaluationStatus.UNSATISFIED
        )
        return EvaluationResult(
            status=status,
            progress=Progress(current, rule.value, "credits"),
            explanation_key="rule.total_credits",
            facts_used=_facts(f"total_credits:{current}"),
        )
    if isinstance(rule, PercentageOfPlan):
        total = context.revision.total_credits if context.revision else None
        if total is None:
            return _unknown("rule.percentage_of_plan.unknown", _facts("plan_total:unknown"))
        current = _effective_credits(context)
        threshold = (total * rule.numerator + rule.denominator - 1) // rule.denominator
        status = (
            EvaluationStatus.SATISFIED
            if current * rule.denominator >= total * rule.numerator
            else EvaluationStatus.UNSATISFIED
        )
        return EvaluationResult(
            status=status,
            progress=Progress(current, threshold, "ratio"),
            explanation_key="rule.percentage_of_plan",
            facts_used=_facts(
                f"percentage:{current}*{rule.denominator}>={total}*{rule.numerator}",
                f"minimum_credits:{threshold}",
            ),
        )
    if isinstance(rule, GroupCompleted):
        current = context.group_credits.get(rule.group)
        required = (
            context.revision.group_required_credits.get(rule.group) if context.revision else None
        )
        if current is None or required is None:
            return _unknown("rule.group_completed.unknown", _facts(f"group:{rule.group}:unknown"))
        status = EvaluationStatus.SATISFIED if current >= required else EvaluationStatus.UNSATISFIED
        return EvaluationResult(
            status=status,
            progress=Progress(current, required, "credits"),
            explanation_key="rule.group_completed",
            facts_used=_facts(
                f"group_credits:{rule.group}={current}", f"group_required:{rule.group}={required}"
            ),
        )
    if isinstance(rule, MandatoryCoursesCompleted):
        unknown = sorted(set(rule.course_codes) & context.unknown_courses)
        if unknown:
            return _unknown(
                "rule.mandatory_courses_completed.unknown",
                tuple(f"course:{code}:unknown" for code in unknown),
            )
        passed = len(set(rule.course_codes) & context.passed_courses)
        status = (
            EvaluationStatus.SATISFIED
            if passed == len(rule.course_codes)
            else EvaluationStatus.UNSATISFIED
        )
        return EvaluationResult(
            status=status,
            progress=Progress(passed, len(rule.course_codes), "courses"),
            explanation_key="rule.mandatory_courses_completed",
            facts_used=_facts(*[f"passed_courses:{code}" for code in sorted(rule.course_codes)]),
        )
    if isinstance(rule, MinimumGrade):
        if rule.course_code in context.unknown_courses:
            return _unknown(
                "rule.minimum_grade.unknown", _facts(f"grade:{rule.course_code}:unknown")
            )
        raw_grade = context.grades.get(rule.course_code)
        if raw_grade is None:
            return _unknown(
                "rule.minimum_grade.missing", _facts(f"grade:{rule.course_code}:missing")
            )
        grade = _parse_context_grade(raw_grade)
        if grade is None:
            return _unknown(
                "rule.minimum_grade.invalid", _facts(f"grade:{rule.course_code}:invalid")
            )
        status = (
            EvaluationStatus.SATISFIED
            if grade >= rule.minimum_grade
            else EvaluationStatus.UNSATISFIED
        )
        return EvaluationResult(
            status=status,
            progress=Progress(1 if status == EvaluationStatus.SATISFIED else 0, 1, "boolean"),
            explanation_key="rule.minimum_grade",
            facts_used=_facts(
                f"grade:{rule.course_code}={grade}", f"minimum_grade:{rule.minimum_grade}"
            ),
        )
    if isinstance(rule, ExternalRequirement):
        value = context.external_requirements.get(rule.key)
        if value is None:
            return _unknown(
                "rule.external_requirement.unknown", _facts(f"external:{rule.key}:unknown")
            )
        if isinstance(value, EvaluationStatus):
            status = value
        elif isinstance(value, str):
            try:
                status = EvaluationStatus(value)
            except ValueError:
                return _unknown(
                    "rule.external_requirement.invalid", _facts(f"external:{rule.key}:invalid")
                )
        elif isinstance(value, bool):
            status = EvaluationStatus.SATISFIED if value else EvaluationStatus.UNSATISFIED
        else:
            return _unknown(
                "rule.external_requirement.invalid", _facts(f"external:{rule.key}:invalid")
            )
        return _boolean(
            status, key="rule.external_requirement", facts=_facts(f"external:{rule.key}")
        )
    if isinstance(rule, EquivalentCoursePassed):
        recognized = context.recognitions.get(rule.equivalence_key)
        if recognized is None:
            return _unknown(
                "rule.equivalent_course_passed.unknown",
                _facts(f"recognition:{rule.equivalence_key}:unknown"),
            )
        candidates = set(rule.course_codes) | set(recognized)
        if candidates & context.unknown_courses:
            return _unknown(
                "rule.equivalent_course_passed.unknown",
                _facts(f"recognition:{rule.equivalence_key}:partial"),
            )
        status = (
            EvaluationStatus.SATISFIED
            if candidates & context.passed_courses
            else EvaluationStatus.UNSATISFIED
        )
        return _boolean(
            status,
            key="rule.equivalent_course_passed",
            facts=_facts(f"recognition:{rule.equivalence_key}"),
        )
    if isinstance(rule, Unknown):
        return _unknown("rule.unknown", _facts(f"unknown:{rule.reason}"))
    raise RuleEvaluationError(f"unsupported rule object {type(rule)!r}")


def evaluate_rule(
    rule: AuditRule,
    context: AuditContext,
    *,
    evidence_refs: tuple[str, ...] | None = None,
) -> EvaluationResult:
    result = _evaluate(rule, context)
    evidence = evidence_refs if evidence_refs is not None else context.evidence_refs
    if not evidence:
        return result
    return EvaluationResult(
        status=result.status,
        progress=result.progress,
        children=result.children,
        evidence=tuple(dict.fromkeys((*result.evidence, *evidence))),
        explanation_key=result.explanation_key,
        facts_used=result.facts_used,
    )
