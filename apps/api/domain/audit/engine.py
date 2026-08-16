from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from domain.revision import canonical_content_hash
from domain.rules import (
    AuditContext as RuleAuditContext,
)
from domain.rules import (
    EvaluationResult,
    EvaluationStatus,
    RevisionFacts,
    Unknown,
    evaluate_rule,
    parse_rule,
    serialize_rule,
)
from domain.rules.ast import AuditRule
from domain.rules.errors import RuleSchemaError

ENGINE_VERSION = "degree-audit/1.0.0"
ACCEPTED_ATTEMPT_STATUSES = frozenset(
    {
        "PASSED",
        "VALIDATED",
        "HOMOLOGATED",
        "TRANSFERRED",
    }
)
_IN_PROGRESS_STATUSES = frozenset({"ENROLLED", "PLANNED"})


class AuditInputError(ValueError):
    """Raised when prepared audit facts violate the pure engine contract."""


@dataclass(frozen=True, slots=True)
class CurriculumGroup:
    code: str
    component: str
    label: str
    required_credits: int
    open_elective: bool = False


@dataclass(frozen=True, slots=True)
class MembershipSnapshot:
    course_code: str
    group_code: str
    role: str
    count_policy: str = "CREDITS"


@dataclass(frozen=True, slots=True)
class RequirementSnapshot:
    code: str
    rule: AuditRule
    purpose: str
    epistemic_status: str
    owner_course_code: str | None = None
    evidence_refs: tuple[str, ...] = ()
    source_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RevisionSnapshot:
    revision_id: str
    content_hash: str
    total_required_credits: int
    components: Mapping[str, int]
    groups: Mapping[str, CurriculumGroup]
    course_credits: Mapping[str, int | None]
    memberships: tuple[MembershipSnapshot, ...]
    mandatory_courses_by_group: Mapping[str, frozenset[str]] = field(default_factory=dict)
    requirements: tuple[RequirementSnapshot, ...] = ()
    graduation_requirements: tuple[RequirementSnapshot, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.total_required_credits, bool) or self.total_required_credits < 0:
            raise AuditInputError("total_required_credits must be non-negative")
        if sum(self.components.values()) != self.total_required_credits:
            raise AuditInputError("component credits must equal the revision total")
        for code, group in self.groups.items():
            if code != group.code:
                raise AuditInputError(f"group key {code!r} does not match group code")
            if group.component not in self.components:
                raise AuditInputError(
                    f"group {code} references unknown component {group.component}"
                )
            if group.required_credits < 0:
                raise AuditInputError(f"group {code} credits must be non-negative")
        for membership in self.memberships:
            if membership.course_code not in self.course_credits:
                raise AuditInputError(
                    f"membership references unknown course {membership.course_code}"
                )
            if membership.group_code not in self.groups:
                raise AuditInputError(
                    f"membership references unknown group {membership.group_code}"
                )
        object.__setattr__(
            self,
            "mandatory_courses_by_group",
            {key: frozenset(value) for key, value in self.mandatory_courses_by_group.items()},
        )

    @property
    def open_elective_groups(self) -> frozenset[str]:
        return frozenset(code for code, group in self.groups.items() if group.open_elective)

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision_id": self.revision_id,
            "content_hash": self.content_hash,
            "total_required_credits": self.total_required_credits,
            "components": dict(sorted(self.components.items())),
            "groups": {
                code: {
                    "component": group.component,
                    "label": group.label,
                    "required_credits": group.required_credits,
                    "open_elective": group.open_elective,
                }
                for code, group in sorted(self.groups.items())
            },
            "course_credits": dict(sorted(self.course_credits.items())),
            "memberships": [
                {
                    "course_code": item.course_code,
                    "group_code": item.group_code,
                    "role": item.role,
                    "count_policy": item.count_policy,
                }
                for item in sorted(
                    self.memberships,
                    key=lambda item: (item.course_code, item.group_code, item.role),
                )
            ],
            "mandatory_courses_by_group": {
                key: sorted(value) for key, value in sorted(self.mandatory_courses_by_group.items())
            },
            "requirements": [_requirement_to_dict(item) for item in self.requirements],
            "graduation_requirements": [
                _requirement_to_dict(item) for item in self.graduation_requirements
            ],
        }


@dataclass(frozen=True, slots=True)
class AcademicRecord:
    course_code: str
    status: str
    attempt_id: str
    credits_earned: int | None = None
    grade: str | None = None

    def __post_init__(self) -> None:
        if not self.course_code or not self.attempt_id:
            raise AuditInputError("academic records require course_code and attempt_id")
        if self.credits_earned is not None and (
            isinstance(self.credits_earned, bool) or self.credits_earned < 0
        ):
            raise AuditInputError("credits_earned must be a non-negative integer or None")


@dataclass(frozen=True, slots=True)
class AcademicExceptionFact:
    exception_id: str
    status: str
    scope: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AuditInput:
    revision: RevisionSnapshot
    history: tuple[AcademicRecord, ...] = ()
    recognized_courses: frozenset[str] = frozenset()
    recognitions: Mapping[str, frozenset[str]] = field(default_factory=dict)
    recognized_credits: Mapping[str, int | None] = field(default_factory=dict)
    external_requirements: Mapping[str, EvaluationStatus | bool | None] = field(
        default_factory=dict
    )
    exceptions: tuple[AcademicExceptionFact, ...] = ()
    audit_date: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "history", tuple(self.history))
        object.__setattr__(self, "recognized_courses", frozenset(self.recognized_courses))
        object.__setattr__(
            self,
            "recognitions",
            {key: frozenset(value) for key, value in self.recognitions.items()},
        )
        for course_code, credits in self.recognized_credits.items():
            if not course_code:
                raise AuditInputError("recognized_credits keys must be non-empty strings")
            if credits is not None and (
                isinstance(credits, bool) or not isinstance(credits, int) or credits < 0
            ):
                raise AuditInputError(
                    "recognized_credits values must be non-negative integers or None"
                )
        object.__setattr__(self, "recognized_credits", dict(self.recognized_credits))
        object.__setattr__(self, "exceptions", tuple(self.exceptions))

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision": self.revision.to_dict(),
            "history": [
                {
                    "course_code": record.course_code,
                    "status": record.status,
                    "attempt_id": record.attempt_id,
                    "credits_earned": record.credits_earned,
                    "grade": record.grade,
                }
                for record in sorted(
                    self.history, key=lambda record: (record.course_code, record.attempt_id)
                )
            ],
            "recognized_courses": sorted(self.recognized_courses),
            "recognitions": {
                key: sorted(value) for key, value in sorted(self.recognitions.items())
            },
            "recognized_credits": dict(sorted(self.recognized_credits.items())),
            "external_requirements": {
                key: value.value if isinstance(value, EvaluationStatus) else value
                for key, value in sorted(self.external_requirements.items())
            },
            "exceptions": [
                {
                    "exception_id": item.exception_id,
                    "status": item.status,
                    "scope": item.scope,
                }
                for item in sorted(self.exceptions, key=lambda item: item.exception_id)
            ],
            "audit_date": self.audit_date,
        }

    @property
    def history_fingerprint(self) -> str:
        return canonical_content_hash(self.to_dict()["history"])

    @property
    def exception_fingerprint(self) -> str:
        return canonical_content_hash(self.to_dict()["exceptions"])

    @property
    def input_fingerprint(self) -> str:
        return canonical_content_hash(self.to_dict())


@dataclass(frozen=True, slots=True)
class AuditContext:
    """Normalized, immutable facts consumed by the audit engine.

    The application layer may prepare this context from an authoritative
    academic record.  The pure engine also exposes ``from_input`` so callers
    that only have a portable ``AuditInput`` get the same deterministic
    normalization and duplicate-attempt policy.
    """

    revision: RevisionSnapshot
    selected_records: Mapping[str, AcademicRecord] = field(default_factory=dict)
    passed_courses: frozenset[str] = frozenset()
    in_progress_courses: frozenset[str] = frozenset()
    recognized_courses: frozenset[str] = frozenset()
    recognitions: Mapping[str, frozenset[str]] = field(default_factory=dict)
    recognized_credits: Mapping[str, int | None] = field(default_factory=dict)
    external_requirements: Mapping[str, EvaluationStatus | bool | None] = field(
        default_factory=dict
    )
    exceptions: tuple[AcademicExceptionFact, ...] = ()
    audit_date: str | None = None
    selection_warnings: tuple[str, ...] = ()
    input_fingerprint: str = ""
    history_fingerprint: str = ""
    exception_fingerprint: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "selected_records", dict(self.selected_records))
        object.__setattr__(self, "passed_courses", frozenset(self.passed_courses))
        object.__setattr__(self, "in_progress_courses", frozenset(self.in_progress_courses))
        object.__setattr__(self, "recognized_courses", frozenset(self.recognized_courses))
        object.__setattr__(
            self,
            "recognitions",
            {key: frozenset(value) for key, value in self.recognitions.items()},
        )
        object.__setattr__(self, "recognized_credits", dict(self.recognized_credits))
        object.__setattr__(self, "exceptions", tuple(self.exceptions))
        object.__setattr__(self, "selection_warnings", tuple(self.selection_warnings))

    @classmethod
    def from_input(cls, audit_input: AuditInput) -> AuditContext:
        selected, passed, in_progress, selection_warnings = _best_records(
            audit_input.revision, audit_input.history
        )
        passed.update(audit_input.recognized_courses)
        return cls(
            revision=audit_input.revision,
            selected_records=selected,
            passed_courses=frozenset(passed),
            in_progress_courses=frozenset(in_progress),
            recognized_courses=audit_input.recognized_courses,
            recognitions=audit_input.recognitions,
            recognized_credits=audit_input.recognized_credits,
            external_requirements=audit_input.external_requirements,
            exceptions=audit_input.exceptions,
            audit_date=audit_input.audit_date,
            selection_warnings=tuple(selection_warnings),
            input_fingerprint=audit_input.input_fingerprint,
            history_fingerprint=audit_input.history_fingerprint,
            exception_fingerprint=audit_input.exception_fingerprint,
        )


@dataclass(frozen=True, slots=True)
class CreditAllocation:
    course_code: str
    attempt_id: str
    group_code: str | None
    earned_credits: int
    applied_credits: int
    unapplied_credits: int
    requirement_code: str
    explanation_key: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "course_code": self.course_code,
            "attempt_id": self.attempt_id,
            "group_code": self.group_code,
            "earned_credits": self.earned_credits,
            "applied_credits": self.applied_credits,
            "unapplied_credits": self.unapplied_credits,
            "requirement_code": self.requirement_code,
            "explanation_key": self.explanation_key,
        }


@dataclass(frozen=True, slots=True)
class CreditLedger:
    allocations: tuple[CreditAllocation, ...]
    total_earned_credits: int
    total_applied_credits: int
    total_unapplied_credits: int
    group_applied_credits: Mapping[str, int]
    unknowns: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.total_earned_credits < self.total_applied_credits:
            raise AuditInputError("ledger cannot apply more credits than earned")
        if self.total_earned_credits - self.total_applied_credits != self.total_unapplied_credits:
            raise AuditInputError("ledger totals do not reconcile")

    def to_dict(self) -> dict[str, Any]:
        return {
            "allocations": [item.to_dict() for item in self.allocations],
            "total_earned_credits": self.total_earned_credits,
            "total_applied_credits": self.total_applied_credits,
            "total_unapplied_credits": self.total_unapplied_credits,
            "group_applied_credits": dict(sorted(self.group_applied_credits.items())),
            "unknowns": list(self.unknowns),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class GroupAudit:
    code: str
    component: str
    required_credits: int
    applied_credits: int
    remaining_credits: int
    mandatory_missing: tuple[str, ...]
    options_available: tuple[str, ...]
    status: EvaluationStatus
    explanation_key: str
    waived: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "component": self.component,
            "required": self.required_credits,
            "applied": self.applied_credits,
            "remaining": self.remaining_credits,
            "mandatory_missing": list(self.mandatory_missing),
            "options_available": list(self.options_available),
            "status": self.status.value,
            "explanation_key": self.explanation_key,
            "waived": self.waived,
        }


@dataclass(frozen=True, slots=True)
class ComponentAudit:
    code: str
    required_credits: int
    applied_credits: int
    remaining_credits: int
    status: EvaluationStatus
    explanation_key: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "required": self.required_credits,
            "applied": self.applied_credits,
            "remaining": self.remaining_credits,
            "status": self.status.value,
            "explanation_key": self.explanation_key,
        }


@dataclass(frozen=True, slots=True)
class RequirementAudit:
    code: str
    owner_course_code: str | None
    purpose: str
    result: EvaluationResult
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "owner_course_code": self.owner_course_code,
            "purpose": self.purpose,
            "result": self.result.to_dict(),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class NextUnlock:
    course_code: str
    status: EvaluationStatus
    reason: EvaluationResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "course_code": self.course_code,
            "status": self.status.value,
            "reason": self.reason.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class AuditResult:
    status: EvaluationStatus
    required_credits: int
    earned_credits: int
    applied_credits: int
    unapplied_credits: int
    components: tuple[ComponentAudit, ...]
    groups: tuple[GroupAudit, ...]
    graduation_requirements: tuple[RequirementAudit, ...]
    requirement_results: tuple[RequirementAudit, ...]
    unknowns: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]
    remaining_requirements: tuple[dict[str, Any], ...]
    next_unlocks: tuple[NextUnlock, ...]
    ledger: CreditLedger
    input_fingerprint: str
    revision_hash: str
    engine_version: str = ENGINE_VERSION
    result_hash: str = ""

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "overall": {
                "status": self.status.value,
                "required_credits": self.required_credits,
                "earned_credits": self.earned_credits,
                "applied_credits": self.applied_credits,
                "unapplied_credits": self.unapplied_credits,
            },
            "components": [item.to_dict() for item in self.components],
            "groups": [item.to_dict() for item in self.groups],
            "graduation_requirements": [item.to_dict() for item in self.graduation_requirements],
            "requirements": [item.to_dict() for item in self.requirement_results],
            "unknowns": list(self.unknowns),
            "warnings": list(self.warnings),
            "remaining_requirements": list(self.remaining_requirements),
            "next_unlocks": [item.to_dict() for item in self.next_unlocks],
            "ledger": self.ledger.to_dict(),
            "input_fingerprint": self.input_fingerprint,
            "revision_hash": self.revision_hash,
            "engine_version": self.engine_version,
        }
        if include_hash:
            payload["result_hash"] = self.result_hash
        return payload


def _requirement_to_dict(requirement: RequirementSnapshot) -> dict[str, Any]:
    return {
        "code": requirement.code,
        "purpose": requirement.purpose,
        "owner_course_code": requirement.owner_course_code,
        "epistemic_status": requirement.epistemic_status,
        "rule": serialize_rule(requirement.rule),
        "evidence_refs": list(requirement.evidence_refs),
    }


def _approved_exceptions(
    exceptions: Sequence[AcademicExceptionFact],
) -> tuple[AcademicExceptionFact, ...]:
    return tuple(item for item in exceptions if item.status == "APPROVED")


def _waived_groups(exceptions: Sequence[AcademicExceptionFact]) -> frozenset[str]:
    result: set[str] = set()
    for item in _approved_exceptions(exceptions):
        values = item.scope.get("waive_groups", [])
        if isinstance(values, Sequence) and not isinstance(values, (str, bytes, bytearray)):
            result.update(str(value) for value in values)
    return frozenset(result)


def _waived_courses(exceptions: Sequence[AcademicExceptionFact]) -> frozenset[str]:
    result: set[str] = set()
    for item in _approved_exceptions(exceptions):
        values = item.scope.get("waive_courses", [])
        if isinstance(values, Sequence) and not isinstance(values, (str, bytes, bytearray)):
            result.update(str(value) for value in values)
    return frozenset(result)


def _best_records(
    revision: RevisionSnapshot,
    history: Sequence[AcademicRecord],
) -> tuple[dict[str, AcademicRecord], set[str], set[str], list[str]]:
    grouped: dict[str, list[AcademicRecord]] = defaultdict(list)
    warnings: list[str] = []
    for record in history:
        grouped[record.course_code].append(record)
    selected: dict[str, AcademicRecord] = {}
    passed: set[str] = set()
    in_progress: set[str] = set()
    for code, records in sorted(grouped.items()):
        accepted = [record for record in records if record.status in ACCEPTED_ATTEMPT_STATUSES]
        if accepted:
            chosen = sorted(
                accepted,
                key=lambda record: (
                    -(record.credits_earned or 0),
                    record.status,
                    record.attempt_id,
                ),
            )[0]
            selected[code] = chosen
            passed.add(code)
            if len(accepted) > 1:
                warnings.append(f"duplicate_passed_attempts:{code}:count={len(accepted)}")
        elif any(record.status in _IN_PROGRESS_STATUSES for record in records):
            in_progress.add(code)
    return selected, passed, in_progress, warnings


def build_credit_ledger(audit_input: AuditInput | AuditContext) -> CreditLedger:
    context = (
        audit_input
        if isinstance(audit_input, AuditContext)
        else AuditContext.from_input(audit_input)
    )
    revision = context.revision
    selected = dict(context.selected_records)
    warnings = list(context.selection_warnings)
    remaining = {code: group.required_credits for code, group in revision.groups.items()}
    group_applied: dict[str, int] = defaultdict(int)
    allocations: list[CreditAllocation] = []
    unknowns: list[str] = []
    membership_by_course: dict[str, list[MembershipSnapshot]] = defaultdict(list)
    for membership in revision.memberships:
        membership_by_course[membership.course_code].append(membership)

    course_codes = sorted(set(selected) | set(context.recognized_courses))
    for course_code in course_codes:
        record = selected.get(course_code)
        attempt_id = record.attempt_id if record else f"recognition:{course_code}"
        course_credits = (
            record.credits_earned
            if record and record.credits_earned is not None and record.credits_earned > 0
            else context.recognized_credits.get(course_code)
            if course_code in context.recognized_credits
            else revision.course_credits.get(course_code)
        )
        if course_credits is None:
            unknowns.append(f"credits_unknown:{course_code}")
            continue
        memberships = sorted(
            membership_by_course.get(course_code, []),
            key=lambda item: (item.group_code, item.role),
        )
        mandatory = [item for item in memberships if item.role == "MANDATORY"]
        candidates = mandatory or [
            item for item in memberships if remaining.get(item.group_code, 0) > 0
        ]
        # An open elective bucket is an explicit curriculum policy, not an
        # arbitrary reassignment of the excess from a partially filled group.
        # It may receive an elective course when all of that course's explicit
        # elective buckets are already full, or when the course has no bucket.
        if not candidates and not mandatory:
            open_groups = sorted(revision.open_elective_groups)
            candidates = [
                MembershipSnapshot(course_code, group_code, "OPEN_ELECTIVE_OPTION")
                for group_code in open_groups
                if remaining.get(group_code, 0) > 0
            ]
        if len(mandatory) > 1:
            warnings.append(f"conflicting_mandatory_memberships:{course_code}")
        group = candidates[0].group_code if candidates else None
        applied = min(course_credits, max(0, remaining.get(group, 0))) if group else 0
        if group:
            remaining[group] -= applied
            group_applied[group] += applied
        unapplied = course_credits - applied
        allocations.append(
            CreditAllocation(
                course_code=course_code,
                attempt_id=attempt_id,
                group_code=group,
                earned_credits=course_credits,
                applied_credits=applied,
                unapplied_credits=unapplied,
                requirement_code=f"GROUP:{group}" if group else "UNAPPLIED",
                explanation_key=(
                    "audit.credit_applied"
                    if applied
                    else "audit.credit_unapplied_no_eligible_bucket"
                ),
            )
        )
        if unapplied:
            warnings.append(f"excess_or_unapplied:{course_code}:{unapplied}")

    total_earned = sum(item.earned_credits for item in allocations)
    total_applied = sum(item.applied_credits for item in allocations)
    return CreditLedger(
        allocations=tuple(allocations),
        total_earned_credits=total_earned,
        total_applied_credits=total_applied,
        total_unapplied_credits=total_earned - total_applied,
        group_applied_credits=dict(sorted(group_applied.items())),
        unknowns=tuple(sorted(set(unknowns))),
        warnings=tuple(sorted(set(warnings))),
    )


def _requirement_result(
    requirement: RequirementSnapshot,
    context: RuleAuditContext,
) -> RequirementAudit:
    result = evaluate_rule(
        requirement.rule,
        context,
        evidence_refs=requirement.evidence_refs,
    )
    if requirement.epistemic_status in {"UNKNOWN", "DISPUTED", "SUPERSEDED"}:
        result = evaluate_rule(
            Unknown(f"requirement_not_verified:{requirement.code}"),
            context,
            evidence_refs=requirement.evidence_refs,
        )
    return RequirementAudit(
        code=requirement.code,
        owner_course_code=requirement.owner_course_code,
        purpose=requirement.purpose,
        result=result,
        evidence_refs=requirement.evidence_refs,
    )


def _group_status(
    group: CurriculumGroup,
    applied: int,
    mandatory_missing: tuple[str, ...],
    waived: bool,
) -> EvaluationStatus:
    if waived:
        return EvaluationStatus.SATISFIED
    if mandatory_missing:
        return EvaluationStatus.UNSATISFIED
    return (
        EvaluationStatus.SATISFIED
        if applied >= group.required_credits
        else EvaluationStatus.UNSATISFIED
    )


def audit_degree(audit_input: AuditInput) -> AuditResult:
    context = AuditContext.from_input(audit_input)
    revision = context.revision
    ledger = build_credit_ledger(context)
    passed = set(context.passed_courses)
    in_progress = set(context.in_progress_courses)
    waived_groups = _waived_groups(context.exceptions)
    waived_courses = _waived_courses(context.exceptions)
    membership_by_group: dict[str, list[MembershipSnapshot]] = defaultdict(list)
    membership_by_course: dict[str, list[MembershipSnapshot]] = defaultdict(list)
    for membership in revision.memberships:
        membership_by_group[membership.group_code].append(membership)
        membership_by_course[membership.course_code].append(membership)

    groups: list[GroupAudit] = []
    for code, group in sorted(revision.groups.items()):
        mandatory = revision.mandatory_courses_by_group.get(code, frozenset())
        missing = tuple(sorted((mandatory - passed - waived_courses) - waived_courses))
        options = tuple(
            sorted(
                membership.course_code
                for membership in membership_by_group.get(code, [])
                if membership.course_code not in passed and membership.role != "MANDATORY"
            )
        )
        applied = ledger.group_applied_credits.get(code, 0)
        groups.append(
            GroupAudit(
                code=code,
                component=group.component,
                required_credits=group.required_credits,
                applied_credits=applied,
                remaining_credits=0
                if code in waived_groups
                else max(0, group.required_credits - applied),
                mandatory_missing=missing,
                options_available=options,
                status=_group_status(group, applied, missing, code in waived_groups),
                explanation_key="audit.group_complete"
                if code in waived_groups or (applied >= group.required_credits and not missing)
                else "audit.group_incomplete",
                waived=code in waived_groups,
            )
        )

    components: list[ComponentAudit] = []
    for component_code, required in sorted(revision.components.items()):
        component_groups = [item for item in groups if item.component == component_code]
        applied = sum(item.applied_credits for item in component_groups)
        component_remaining = max(0, required - applied)
        statuses = {item.status for item in component_groups}
        status = (
            EvaluationStatus.SATISFIED
            if applied >= required
            and all(item.status == EvaluationStatus.SATISFIED for item in component_groups)
            else EvaluationStatus.UNSATISFIED
            if EvaluationStatus.UNSATISFIED in statuses
            else EvaluationStatus.UNKNOWN
        )
        components.append(
            ComponentAudit(
                code=component_code,
                required_credits=required,
                applied_credits=applied,
                remaining_credits=component_remaining,
                status=status,
                explanation_key="audit.component_complete"
                if status == EvaluationStatus.SATISFIED
                else "audit.component_incomplete",
            )
        )

    group_credits = {item.code: item.applied_credits for item in groups}
    component_credits = {item.code: item.applied_credits for item in components}
    rule_context = RuleAuditContext(
        revision=RevisionFacts(
            total_credits=revision.total_required_credits,
            group_required_credits={
                code: group.required_credits for code, group in revision.groups.items()
            },
            component_required_credits=revision.components,
            mandatory_courses_by_group=revision.mandatory_courses_by_group,
        ),
        passed_courses=frozenset(passed),
        in_progress_courses=frozenset(in_progress),
        earned_credits=ledger.total_earned_credits,
        group_credits=group_credits,
        component_credits=component_credits,
        external_requirements=context.external_requirements,
        recognitions=context.recognitions,
        unknown_courses=frozenset(
            value.removeprefix("credits_unknown:") for value in ledger.unknowns
        ),
    )
    requirement_results = tuple(
        _requirement_result(requirement, rule_context)
        for requirement in sorted(revision.requirements, key=lambda item: item.code)
    )
    graduation_results = tuple(
        _requirement_result(requirement, rule_context)
        for requirement in sorted(revision.graduation_requirements, key=lambda item: item.code)
    )
    unknowns: list[dict[str, Any]] = [
        {"kind": "ledger", "code": value, "material": True} for value in ledger.unknowns
    ]
    for item in (*requirement_results, *graduation_results):
        if item.result.status == EvaluationStatus.UNKNOWN:
            unknowns.append(
                {
                    "kind": "requirement",
                    "code": item.code,
                    "owner_course_code": item.owner_course_code,
                    "material": item in graduation_results
                    or item.owner_course_code
                    in {
                        code
                        for values in revision.mandatory_courses_by_group.values()
                        for code in values
                    },
                }
            )
    group_statuses = {item.status for item in groups}
    graduation_statuses = {item.result.status for item in graduation_results}
    material_unknown = any(item["material"] for item in unknowns)
    if (
        EvaluationStatus.UNSATISFIED in group_statuses
        or EvaluationStatus.UNSATISFIED in graduation_statuses
    ):
        overall = EvaluationStatus.UNSATISFIED
    elif EvaluationStatus.UNKNOWN in group_statuses or material_unknown:
        overall = EvaluationStatus.UNKNOWN
    else:
        overall = EvaluationStatus.SATISFIED

    remaining_requirements: list[dict[str, Any]] = []
    for group_audit in groups:
        if group_audit.remaining_credits or group_audit.mandatory_missing:
            remaining_requirements.append(
                {
                    "kind": "group",
                    "code": group_audit.code,
                    "remaining_credits": group_audit.remaining_credits,
                    "mandatory_missing": list(group_audit.mandatory_missing),
                    "status": group_audit.status.value,
                }
            )
    for req_audit in (*requirement_results, *graduation_results):
        if req_audit.result.status != EvaluationStatus.SATISFIED:
            remaining_requirements.append(
                {
                    "kind": "requirement",
                    "code": req_audit.code,
                    "owner_course_code": req_audit.owner_course_code,
                    "status": req_audit.result.status.value,
                }
            )

    next_unlocks: list[NextUnlock] = []
    for item in requirement_results:
        if item.owner_course_code and item.owner_course_code not in passed:
            next_unlocks.append(NextUnlock(item.owner_course_code, item.result.status, item.result))
    warnings = tuple(
        sorted(
            set(
                [*ledger.warnings, *context.selection_warnings]
                + (["material_unknowns_present"] if material_unknown else [])
                + (["unapplied_credits_present"] if ledger.total_unapplied_credits else [])
            )
        )
    )
    provisional = AuditResult(
        status=overall,
        required_credits=revision.total_required_credits,
        earned_credits=ledger.total_earned_credits,
        applied_credits=ledger.total_applied_credits,
        unapplied_credits=ledger.total_unapplied_credits,
        components=tuple(components),
        groups=tuple(groups),
        graduation_requirements=graduation_results,
        requirement_results=requirement_results,
        unknowns=tuple(
            sorted(unknowns, key=lambda item: (str(item.get("kind")), str(item.get("code"))))
        ),
        warnings=warnings
        + tuple(
            f"remaining:{item['kind']}:{item['code']}"
            for item in sorted(
                remaining_requirements, key=lambda value: (value["kind"], value["code"])
            )
        ),
        remaining_requirements=tuple(
            sorted(
                remaining_requirements,
                key=lambda item: (str(item["kind"]), str(item["code"])),
            )
        ),
        next_unlocks=tuple(sorted(next_unlocks, key=lambda item: item.course_code)),
        ledger=ledger,
        input_fingerprint=context.input_fingerprint,
        revision_hash=revision.content_hash,
    )
    result_hash = hashlib.sha256(
        json.dumps(
            provisional.to_dict(include_hash=False),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return replace(provisional, result_hash=result_hash)


def revision_snapshot_from_baseline(payload: Mapping[str, Any]) -> RevisionSnapshot:
    identity = payload.get("identity", {})
    revision_data = payload.get("revision", {})
    components = {
        str(item["id"]): int(item["required_credits"])
        for item in payload.get("components", [])
        if isinstance(item, Mapping)
    }
    groups = {
        str(item["id"]): CurriculumGroup(
            code=str(item["id"]),
            component=str(item["component"]),
            label=str(item.get("name", item["id"])),
            required_credits=int(item["required_credits"]),
            open_elective=str(item["id"]) == "FREE_ELECTIVE",
        )
        for item in payload.get("groups", [])
        if isinstance(item, Mapping)
    }
    course_credits = {
        str(item["code"]): item.get("credits") if isinstance(item.get("credits"), int) else None
        for item in payload.get("courses", [])
        if isinstance(item, Mapping)
    }
    memberships: list[MembershipSnapshot] = []
    mandatory_by_group: dict[str, set[str]] = defaultdict(set)
    for item in payload.get("memberships", []):
        if not isinstance(item, Mapping):
            continue
        membership = MembershipSnapshot(
            course_code=str(item["course_code"]),
            group_code=str(item["group"]),
            role="MANDATORY" if item.get("mandatory") is True else "ELECTIVE_OPTION",
        )
        memberships.append(membership)
        if membership.role == "MANDATORY":
            mandatory_by_group[membership.group_code].add(membership.course_code)

    def make_requirement(
        item: Mapping[str, Any], owner: str | None, code: str
    ) -> RequirementSnapshot:
        try:
            rule = parse_rule(item.get("ast", {}))
        except RuleSchemaError:
            rule = Unknown(f"invalid_ast:{code}")
        evidence = item.get("evidence")
        refs = (
            (f"{evidence.get('document')}#page:{evidence.get('page')}",)
            if isinstance(evidence, Mapping) and evidence.get("page")
            else ()
        )
        purpose = str(item.get("purpose", "GRADUATION"))
        purpose = {
            "PREREQUISITE": "ENROLLMENT_PREREQUISITE",
            "COREQUISITE": "COREQUISITE",
        }.get(purpose, purpose)
        return RequirementSnapshot(
            code=code,
            rule=rule,
            purpose=purpose,
            epistemic_status=str(item.get("epistemic_status", "UNKNOWN")),
            owner_course_code=owner,
            evidence_refs=refs,
            source_metadata=dict(item),
        )

    requirements = tuple(
        make_requirement(
            item,
            str(item.get("owner_course_code")),
            f"CURRICULUM:{item.get('purpose')}:{item.get('owner_course_code')}",
        )
        for item in payload.get("enrollment_requirements", [])
        if isinstance(item, Mapping)
    )
    graduation = tuple(
        make_requirement(item, None, f"GRADUATION:{item.get('id', 'UNKNOWN')}")
        for item in payload.get("graduation_requirements", [])
        if isinstance(item, Mapping)
    )
    return RevisionSnapshot(
        revision_id=str(revision_data.get("revision_code", "unknown")),
        content_hash=canonical_content_hash(payload),
        total_required_credits=int(identity.get("total_required_credits", 0)),
        components=components,
        groups=groups,
        course_credits=course_credits,
        memberships=tuple(memberships),
        mandatory_courses_by_group={
            key: frozenset(value) for key, value in mandatory_by_group.items()
        },
        requirements=requirements,
        graduation_requirements=graduation,
    )
