from __future__ import annotations

from datetime import date, time
from threading import Event

from hypothesis import given, settings
from hypothesis import strategies as st

from domain.offerings.schedule import MeetingWindow
from domain.optimization import (
    UNKNOWN_OFFERING_REQUIRE,
    CandidateFact,
    CourseFact,
    GroupFact,
    GroupMembershipFact,
    LockedChoice,
    OptimizationInput,
    OptimizationPreferences,
    OptimizationStatus,
    TermFact,
    solve_optimization,
)
from domain.rules.ast import AuditRule, Corequisite, CoursePassed


def _input(
    *,
    courses: tuple[CourseFact, ...],
    groups: tuple[GroupFact, ...],
    candidates: tuple[CandidateFact, ...],
    locked: tuple[LockedChoice, ...] = (),
    passed: frozenset[str] = frozenset(),
    preferences: OptimizationPreferences | None = None,
) -> OptimizationInput:
    return OptimizationInput(
        revision_id="revision-1",
        revision_hash="revision-hash",
        terms=(
            TermFact("2026-1S", 0, date(2026, 1, 1), date(2026, 6, 30)),
            TermFact("2026-2S", 1, date(2026, 7, 1), date(2026, 12, 31)),
        ),
        courses=courses,
        groups=groups,
        candidates=candidates,
        passed_courses=passed,
        locked_choices=locked,
        preferences=preferences or OptimizationPreferences(max_credits_per_term=12),
    )


def _course(
    code: str,
    *,
    mandatory: bool = True,
    credits: int = 4,
    rule: AuditRule | None = None,
) -> CourseFact:
    return CourseFact(
        id=code.lower(),
        code=code,
        credits=credits,
        mandatory=mandatory,
        memberships=(GroupMembershipFact("CORE", "MANDATORY"),),
        prerequisite_rules=(rule,) if rule is not None else (),
    )


def _candidates(
    courses: tuple[CourseFact, ...], state: str = "OFFERED"
) -> tuple[CandidateFact, ...]:
    return tuple(
        CandidateFact(course.id, course.code, term, state)
        for course in courses
        for term in ("2026-1S", "2026-2S")
    )


def test_optimal_result_respects_prerequisite_and_is_deterministic() -> None:
    courses = (_course("A"), _course("B", rule=CoursePassed("A")))
    input_data = _input(
        courses=courses,
        groups=(GroupFact("CORE", 8),),
        candidates=_candidates(courses),
    )

    first = solve_optimization(input_data)
    second = solve_optimization(input_data)

    assert first.status == OptimizationStatus.OPTIMAL.value
    assert [(item.course_code, item.term_code) for item in first.selected_courses] == [
        ("A", "2026-1S"),
        ("B", "2026-2S"),
    ]
    assert first.output_hash == second.output_hash
    assert first.objectives[0].name == "last_term"


def test_corequisite_can_be_scheduled_in_the_same_term() -> None:
    courses = (_course("A"), _course("B", rule=Corequisite("A")))
    result = solve_optimization(
        _input(
            courses=courses,
            groups=(GroupFact("CORE", 8),),
            candidates=_candidates(courses),
            preferences=OptimizationPreferences(max_credits_per_term=8),
        )
    )

    assert result.status == OptimizationStatus.OPTIMAL.value
    assert {item.term_code for item in result.selected_courses} == {"2026-1S"}


def test_unknown_future_offering_is_explicit_or_blocking_by_policy() -> None:
    course = _course("A")
    allowed = solve_optimization(
        _input(
            courses=(course,),
            groups=(GroupFact("CORE", 4),),
            candidates=_candidates((course,), state="UNKNOWN"),
        )
    )
    blocked = solve_optimization(
        _input(
            courses=(course,),
            groups=(GroupFact("CORE", 4),),
            candidates=_candidates((course,), state="UNKNOWN"),
            preferences=OptimizationPreferences(
                max_credits_per_term=12,
                unknown_offering_policy=UNKNOWN_OFFERING_REQUIRE,
            ),
        )
    )

    assert allowed.status == OptimizationStatus.OPTIMAL.value
    assert any(item.startswith("UNKNOWN_OFFERING_ASSUMPTION:A:") for item in allowed.assumptions)
    assert blocked.status == OptimizationStatus.INFEASIBLE.value
    assert any(item["code"] == "MANDATORY_COURSE_UNAVAILABLE" for item in blocked.conflicts)


def test_locked_schedule_conflict_is_explained_before_solving() -> None:
    left = MeetingWindow("m-left", "s-left", 0, time(8), time(10), "America/Bogota")
    right = MeetingWindow("m-right", "s-right", 0, time(9), time(11), "America/Bogota")
    courses = (_course("A"), _course("B"))
    candidates = (
        CandidateFact("a", "A", "2026-1S", "OFFERED", "s-left", (left,)),
        CandidateFact("a", "A", "2026-2S", "OFFERED"),
        CandidateFact("b", "B", "2026-1S", "OFFERED", "s-right", (right,)),
        CandidateFact("b", "B", "2026-2S", "OFFERED"),
    )
    result = solve_optimization(
        _input(
            courses=courses,
            groups=(GroupFact("CORE", 8),),
            candidates=candidates,
            locked=(
                LockedChoice("A", "2026-1S", "s-left"),
                LockedChoice("B", "2026-1S", "s-right"),
            ),
        )
    )

    assert result.status == OptimizationStatus.INFEASIBLE.value
    assert any(item["code"] == "LOCKED_SCHEDULE_CONFLICT" for item in result.conflicts)


def test_locked_offering_check_uses_the_locked_candidate() -> None:
    course = _course("A")
    candidates = (
        CandidateFact("a", "A", "2026-1S", "OFFERED"),
        CandidateFact("a", "A", "2026-2S", "NOT_OFFERED"),
    )
    result = solve_optimization(
        _input(
            courses=(course,),
            groups=(GroupFact("CORE", 4),),
            candidates=candidates,
            locked=(LockedChoice("A", "2026-1S"),),
        )
    )

    assert result.status == OptimizationStatus.OPTIMAL.value
    assert [(item.course_code, item.term_code) for item in result.selected_courses] == [
        ("A", "2026-1S")
    ]


def test_locked_already_passed_course_is_reported_as_infeasible() -> None:
    course = _course("A")
    result = solve_optimization(
        _input(
            courses=(course,),
            groups=(GroupFact("CORE", 0),),
            candidates=_candidates((course,)),
            locked=(LockedChoice("A", "2026-1S"),),
            passed=frozenset({"A"}),
        )
    )

    assert result.status == OptimizationStatus.INFEASIBLE.value


@given(st.integers(min_value=1, max_value=12))
@settings(max_examples=8, deadline=None)
def test_small_credit_inputs_preserve_single_selection_and_group_coverage(credits: int) -> None:
    course = _course("A", credits=credits)
    result = solve_optimization(
        _input(
            courses=(course,),
            groups=(GroupFact("CORE", credits),),
            candidates=_candidates((course,)),
        )
    )

    assert result.status == OptimizationStatus.OPTIMAL.value
    assert [item.course_code for item in result.selected_courses] == ["A"]
    assert sum(item.credits or 0 for item in result.selected_courses) >= credits


def test_input_round_trip_and_cancellation_are_explicit() -> None:
    course = _course("A")
    input_data = _input(
        courses=(course,),
        groups=(GroupFact("CORE", 4),),
        candidates=_candidates((course,)),
    )
    assert OptimizationInput.from_dict(input_data.to_dict()).input_hash == input_data.input_hash

    cancel = Event()
    cancel.set()
    result = solve_optimization(input_data, cancel_event=cancel)
    assert result.status == OptimizationStatus.UNKNOWN.value
    assert result.termination_reason == "cancelled"
