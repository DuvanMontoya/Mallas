from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, time
from enum import StrEnum
from typing import Any

from domain.offerings.schedule import MeetingWindow
from domain.rules.ast import AuditRule, parse_rule, serialize_rule

SOLVER_VERSION = "cp-sat-planner/1.0.0"
UNKNOWN_OFFERING_ALLOW = "ALLOW_UNKNOWN"
UNKNOWN_OFFERING_REQUIRE = "REQUIRE_OFFERED"
GROUP_ROLE_MANDATORY = "MANDATORY"


class OptimizationStatus(StrEnum):
    """Persisted solver outcomes; operational QUEUED/RUNNING are separate."""

    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _meeting_to_dict(meeting: MeetingWindow) -> dict[str, Any]:
    return {
        "meeting_id": meeting.meeting_id,
        "section_id": meeting.section_id,
        "day_of_week": meeting.day_of_week,
        "starts_at": meeting.starts_at.isoformat(),
        "ends_at": meeting.ends_at.isoformat(),
        "timezone": meeting.timezone,
        "starts_on": meeting.starts_on.isoformat() if meeting.starts_on else None,
        "ends_on": meeting.ends_on.isoformat() if meeting.ends_on else None,
        "session_code": meeting.session_code,
        "is_alternate": meeting.is_alternate,
    }


def _meeting_from_dict(value: dict[str, Any]) -> MeetingWindow:
    return MeetingWindow(
        meeting_id=str(value["meeting_id"]),
        section_id=str(value["section_id"]),
        day_of_week=int(value["day_of_week"]),
        starts_at=time.fromisoformat(str(value["starts_at"])),
        ends_at=time.fromisoformat(str(value["ends_at"])),
        timezone=str(value["timezone"]),
        starts_on=date.fromisoformat(value["starts_on"]) if value.get("starts_on") else None,
        ends_on=date.fromisoformat(value["ends_on"]) if value.get("ends_on") else None,
        session_code=str(value.get("session_code", "")),
        is_alternate=bool(value.get("is_alternate", False)),
    )


@dataclass(frozen=True, slots=True)
class TermFact:
    code: str
    order: int
    starts_on: date | None = None
    ends_on: date | None = None

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("term code is required")
        if isinstance(self.order, bool) or self.order < 0:
            raise ValueError("term order must be a non-negative integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "order": self.order,
            "starts_on": self.starts_on.isoformat() if self.starts_on else None,
            "ends_on": self.ends_on.isoformat() if self.ends_on else None,
        }


@dataclass(frozen=True, slots=True)
class GroupFact:
    code: str
    required_credits: int
    label: str = ""

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("group code is required")
        if isinstance(self.required_credits, bool) or self.required_credits < 0:
            raise ValueError("group credits must be a non-negative integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "required_credits": self.required_credits,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class GroupMembershipFact:
    group_code: str
    role: str
    count_policy: str = "CREDITS"

    def to_dict(self) -> dict[str, str]:
        return {
            "group_code": self.group_code,
            "role": self.role,
            "count_policy": self.count_policy,
        }


@dataclass(frozen=True, slots=True)
class CourseFact:
    id: str
    code: str
    credits: int | None
    mandatory: bool = False
    memberships: tuple[GroupMembershipFact, ...] = ()
    prerequisite_rules: tuple[AuditRule, ...] = ()
    preference_penalty: int = 0
    area_code: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.code.strip():
            raise ValueError("course id and code are required")
        if self.credits is not None and (isinstance(self.credits, bool) or self.credits < 0):
            raise ValueError("course credits must be a non-negative integer or None")
        if isinstance(self.preference_penalty, bool) or self.preference_penalty < 0:
            raise ValueError("preference penalty must be a non-negative integer")
        object.__setattr__(self, "memberships", tuple(self.memberships))
        object.__setattr__(self, "prerequisite_rules", tuple(self.prerequisite_rules))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "credits": self.credits,
            "mandatory": self.mandatory,
            "memberships": [item.to_dict() for item in self.memberships],
            "prerequisite_rules": [serialize_rule(rule) for rule in self.prerequisite_rules],
            "preference_penalty": self.preference_penalty,
            "area_code": self.area_code,
        }


@dataclass(frozen=True, slots=True)
class CandidateFact:
    course_id: str
    course_code: str
    term_code: str
    offering_state: str = "UNKNOWN"
    selected_section_id: str | None = None
    meetings: tuple[MeetingWindow, ...] = ()

    def __post_init__(self) -> None:
        if not self.course_id.strip() or not self.course_code.strip() or not self.term_code.strip():
            raise ValueError("candidate course, id and term are required")
        object.__setattr__(self, "meetings", tuple(self.meetings))

    def to_dict(self) -> dict[str, Any]:
        return {
            "course_id": self.course_id,
            "course_code": self.course_code,
            "term_code": self.term_code,
            "offering_state": self.offering_state,
            "selected_section_id": self.selected_section_id,
            "meetings": [_meeting_to_dict(item) for item in self.meetings],
        }


@dataclass(frozen=True, slots=True)
class LockedChoice:
    course_code: str
    term_code: str
    selected_section_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "course_code": self.course_code,
            "term_code": self.term_code,
            "selected_section_id": self.selected_section_id,
        }


@dataclass(frozen=True, slots=True)
class OptimizationPreferences:
    min_credits_per_term: int = 0
    max_credits_per_term: int = 18
    unknown_offering_policy: str = UNKNOWN_OFFERING_ALLOW
    credit_target: int | None = None
    preferred_credits_per_term: int | None = None
    random_seed: int = 0
    time_limit_seconds: int = 30

    def __post_init__(self) -> None:
        if self.min_credits_per_term < 0 or self.max_credits_per_term < 0:
            raise ValueError("credit bounds must be non-negative")
        if self.min_credits_per_term > self.max_credits_per_term:
            raise ValueError("minimum credits cannot exceed maximum credits")
        if self.unknown_offering_policy not in {
            UNKNOWN_OFFERING_ALLOW,
            UNKNOWN_OFFERING_REQUIRE,
        }:
            raise ValueError("unknown offering policy is invalid")
        if self.credit_target is not None and self.credit_target < 0:
            raise ValueError("credit target must be non-negative")
        if self.preferred_credits_per_term is not None and self.preferred_credits_per_term < 0:
            raise ValueError("preferred credits must be non-negative")
        if self.time_limit_seconds <= 0:
            raise ValueError("time limit must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_credits_per_term": self.min_credits_per_term,
            "max_credits_per_term": self.max_credits_per_term,
            "unknown_offering_policy": self.unknown_offering_policy,
            "credit_target": self.credit_target,
            "preferred_credits_per_term": self.preferred_credits_per_term,
            "random_seed": self.random_seed,
            "time_limit_seconds": self.time_limit_seconds,
        }


@dataclass(frozen=True, slots=True)
class OptimizationInput:
    revision_id: str
    revision_hash: str
    terms: tuple[TermFact, ...]
    courses: tuple[CourseFact, ...]
    groups: tuple[GroupFact, ...]
    candidates: tuple[CandidateFact, ...]
    passed_courses: frozenset[str] = frozenset()
    in_progress_courses: frozenset[str] = frozenset()
    locked_choices: tuple[LockedChoice, ...] = ()
    preferences: OptimizationPreferences = field(default_factory=OptimizationPreferences)

    def __post_init__(self) -> None:
        if not self.revision_id.strip() or not self.revision_hash.strip():
            raise ValueError("revision identity is required")
        object.__setattr__(self, "terms", tuple(self.terms))
        object.__setattr__(self, "courses", tuple(self.courses))
        object.__setattr__(self, "groups", tuple(self.groups))
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(self, "passed_courses", frozenset(self.passed_courses))
        object.__setattr__(self, "in_progress_courses", frozenset(self.in_progress_courses))
        object.__setattr__(self, "locked_choices", tuple(self.locked_choices))
        term_codes = [item.code for item in self.terms]
        course_codes = [item.code for item in self.courses]
        group_codes = [item.code for item in self.groups]
        if len(set(term_codes)) != len(term_codes):
            raise ValueError("term codes must be unique")
        if len(set(course_codes)) != len(course_codes):
            raise ValueError("course codes must be unique")
        if len(set(group_codes)) != len(group_codes):
            raise ValueError("group codes must be unique")
        if len({(item.course_code, item.term_code) for item in self.candidates}) != len(
            self.candidates
        ):
            raise ValueError("candidate course/term pairs must be unique")
        if any(item.term_code not in term_codes for item in self.candidates):
            raise ValueError("candidate references an unknown term")
        if any(item.course_code not in course_codes for item in self.candidates):
            raise ValueError("candidate references an unknown course")

    @property
    def input_hash(self) -> str:
        return canonical_hash(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision_id": self.revision_id,
            "revision_hash": self.revision_hash,
            "terms": [item.to_dict() for item in sorted(self.terms, key=lambda item: item.order)],
            "courses": [
                item.to_dict() for item in sorted(self.courses, key=lambda item: item.code)
            ],
            "groups": [item.to_dict() for item in sorted(self.groups, key=lambda item: item.code)],
            "candidates": [
                item.to_dict()
                for item in sorted(
                    self.candidates, key=lambda item: (item.course_code, item.term_code)
                )
            ],
            "passed_courses": sorted(self.passed_courses),
            "in_progress_courses": sorted(self.in_progress_courses),
            "locked_choices": [
                item.to_dict()
                for item in sorted(
                    self.locked_choices, key=lambda item: (item.course_code, item.term_code)
                )
            ],
            "preferences": self.preferences.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> OptimizationInput:
        terms = tuple(
            TermFact(
                code=str(item["code"]),
                order=int(item["order"]),
                starts_on=date.fromisoformat(item["starts_on"]) if item.get("starts_on") else None,
                ends_on=date.fromisoformat(item["ends_on"]) if item.get("ends_on") else None,
            )
            for item in value["terms"]
        )
        courses = tuple(
            CourseFact(
                id=str(item["id"]),
                code=str(item["code"]),
                credits=item.get("credits"),
                mandatory=bool(item.get("mandatory", False)),
                memberships=tuple(
                    GroupMembershipFact(
                        group_code=str(membership["group_code"]),
                        role=str(membership["role"]),
                        count_policy=str(membership.get("count_policy", "CREDITS")),
                    )
                    for membership in item.get("memberships", [])
                ),
                prerequisite_rules=tuple(
                    parse_rule(rule) for rule in item.get("prerequisite_rules", [])
                ),
                preference_penalty=int(item.get("preference_penalty", 0)),
                area_code=item.get("area_code"),
            )
            for item in value["courses"]
        )
        candidates = tuple(
            CandidateFact(
                course_id=str(item["course_id"]),
                course_code=str(item["course_code"]),
                term_code=str(item["term_code"]),
                offering_state=str(item.get("offering_state", "UNKNOWN")),
                selected_section_id=item.get("selected_section_id"),
                meetings=tuple(_meeting_from_dict(meeting) for meeting in item.get("meetings", [])),
            )
            for item in value["candidates"]
        )
        preferences = value.get("preferences", {})
        return cls(
            revision_id=str(value["revision_id"]),
            revision_hash=str(value["revision_hash"]),
            terms=terms,
            courses=courses,
            groups=tuple(
                GroupFact(
                    code=str(item["code"]),
                    required_credits=int(item["required_credits"]),
                    label=str(item.get("label", "")),
                )
                for item in value["groups"]
            ),
            candidates=candidates,
            passed_courses=frozenset(str(item) for item in value.get("passed_courses", [])),
            in_progress_courses=frozenset(
                str(item) for item in value.get("in_progress_courses", [])
            ),
            locked_choices=tuple(
                LockedChoice(
                    course_code=str(item["course_code"]),
                    term_code=str(item["term_code"]),
                    selected_section_id=item.get("selected_section_id"),
                )
                for item in value.get("locked_choices", [])
            ),
            preferences=OptimizationPreferences(**preferences),
        )


@dataclass(frozen=True, slots=True)
class SelectedCourse:
    course_id: str
    course_code: str
    term_code: str
    credits: int | None
    selected_section_id: str | None
    offering_state: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "course_id": self.course_id,
            "course_code": self.course_code,
            "term_code": self.term_code,
            "credits": self.credits,
            "selected_section_id": self.selected_section_id,
            "offering_state": self.offering_state,
        }


@dataclass(frozen=True, slots=True)
class DecisionExplanation:
    course_code: str
    term_code: str
    reasons: tuple[str, ...]
    satisfies_groups: tuple[str, ...] = ()
    unlocks_courses: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "course_code": self.course_code,
            "term_code": self.term_code,
            "reasons": list(self.reasons),
            "satisfies_groups": list(self.satisfies_groups),
            "unlocks_courses": list(self.unlocks_courses),
            "assumptions": list(self.assumptions),
        }


@dataclass(frozen=True, slots=True)
class OptimizationObjective:
    name: str
    value: int
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value, "explanation": self.explanation}


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    status: str
    input_hash: str
    solver_version: str
    selected_courses: tuple[SelectedCourse, ...] = ()
    objectives: tuple[OptimizationObjective, ...] = ()
    explanations: tuple[DecisionExplanation, ...] = ()
    conflicts: tuple[dict[str, Any], ...] = ()
    assumptions: tuple[str, ...] = ()
    termination_reason: str = ""
    wall_time_seconds: int = 0
    output_hash: str = ""

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "input_hash": self.input_hash,
            "solver_version": self.solver_version,
            "selected_courses": [item.to_dict() for item in self.selected_courses],
            "objectives": [item.to_dict() for item in self.objectives],
            "explanations": [item.to_dict() for item in self.explanations],
            "conflicts": list(self.conflicts),
            "assumptions": list(self.assumptions),
            "termination_reason": self.termination_reason,
            "wall_time_seconds": self.wall_time_seconds,
        }
        if include_hash:
            payload["output_hash"] = self.output_hash or canonical_hash(payload)
        return payload

    def with_output_hash(self) -> OptimizationResult:
        result_hash = canonical_hash(self.to_dict(include_hash=False))
        return OptimizationResult(
            status=self.status,
            input_hash=self.input_hash,
            solver_version=self.solver_version,
            selected_courses=self.selected_courses,
            objectives=self.objectives,
            explanations=self.explanations,
            conflicts=self.conflicts,
            assumptions=self.assumptions,
            termination_reason=self.termination_reason,
            wall_time_seconds=self.wall_time_seconds,
            output_hash=result_hash,
        )
