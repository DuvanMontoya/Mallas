from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from threading import Event
from time import monotonic
from typing import Any

from ortools.sat.python import cp_model

from domain.offerings.schedule import evaluate_schedule
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

from .model import (
    SOLVER_VERSION,
    UNKNOWN_OFFERING_ALLOW,
    CandidateFact,
    CourseFact,
    DecisionExplanation,
    OptimizationInput,
    OptimizationObjective,
    OptimizationResult,
    OptimizationStatus,
    SelectedCourse,
)


@dataclass(slots=True)
class _ModelState:
    model: Any
    x: dict[tuple[str, str], Any]
    y: dict[tuple[str, str, str], Any]
    objective_expressions: dict[str, Any]
    candidates: dict[tuple[str, str], CandidateFact]
    courses: dict[str, CourseFact]
    terms: dict[str, Any]
    unknown_candidates: set[tuple[str, str]]
    schedule_unknowns: list[str]


def _sum(values: list[Any]) -> Any:
    return sum(values, 0)


def _constant(model: Any, value: bool, name: str) -> Any:
    variable = model.new_bool_var(name)
    model.add(variable == int(value))
    return variable


def _equivalence_literal(model: Any, expression: Any, name: str) -> Any:
    literal = model.new_bool_var(name)
    model.add(expression >= 1).only_enforce_if(literal)
    model.add(expression == 0).only_enforce_if(literal.Not())
    return literal


def _comparison_literal(model: Any, expression: Any, operator: str, value: int, name: str) -> Any:
    literal = model.new_bool_var(name)
    if operator == ">=":
        model.add(expression >= value).only_enforce_if(literal)
        model.add(expression < value).only_enforce_if(literal.Not())
    elif operator == ">":
        model.add(expression > value).only_enforce_if(literal)
        model.add(expression <= value).only_enforce_if(literal.Not())
    elif operator == "=":
        model.add(expression == value).only_enforce_if(literal)
        model.add(expression != value).only_enforce_if(literal.Not())
    elif operator == "<=":
        model.add(expression <= value).only_enforce_if(literal)
        model.add(expression > value).only_enforce_if(literal.Not())
    elif operator == "<":
        model.add(expression < value).only_enforce_if(literal)
        model.add(expression >= value).only_enforce_if(literal.Not())
    else:
        raise ValueError(f"unsupported comparison operator {operator}")
    return literal


def _all_literal(model: Any, children: list[Any], name: str) -> Any:
    if not children:
        return _constant(model, True, name)
    literal = model.new_bool_var(name)
    model.add_bool_and(children).only_enforce_if(literal)
    model.add_bool_or([child.Not() for child in children]).only_enforce_if(literal.Not())
    return literal


def _any_literal(model: Any, children: list[Any], name: str) -> Any:
    if not children:
        return _constant(model, False, name)
    literal = model.new_bool_var(name)
    model.add_bool_or(children).only_enforce_if(literal)
    model.add_bool_and([child.Not() for child in children]).only_enforce_if(literal.Not())
    return literal


def _course_codes_in_rule(rule: AuditRule) -> frozenset[str]:
    if isinstance(rule, (CoursePassed, CourseInProgress, CoursePassedOrInProgress, Corequisite)):
        return frozenset({rule.course_code})
    if isinstance(rule, EquivalentCoursePassed):
        return frozenset(rule.course_codes)
    if isinstance(rule, MandatoryCoursesCompleted):
        return frozenset(rule.course_codes)
    if isinstance(rule, (All, AnyOf)):
        return frozenset(code for child in rule.children for code in _course_codes_in_rule(child))
    if isinstance(rule, Not):
        return _course_codes_in_rule(rule.child)
    return frozenset()


def _contains_unknown_rule(rule: AuditRule) -> bool:
    if isinstance(
        rule, (ExternalRequirement, Unknown, MinimumGrade, CreditsInComponent, PercentageOfPlan)
    ):
        return True
    if isinstance(rule, (All, AnyOf)):
        return any(_contains_unknown_rule(child) for child in rule.children)
    if isinstance(rule, Not):
        return _contains_unknown_rule(rule.child)
    return False


def _term_order(input_data: OptimizationInput) -> dict[str, int]:
    return {term.code: term.order for term in input_data.terms}


def _candidate_blocked(input_data: OptimizationInput, candidate: CandidateFact) -> bool:
    state = candidate.offering_state.upper()
    return state == "NOT_OFFERED" or (
        state != "OFFERED"
        and input_data.preferences.unknown_offering_policy != UNKNOWN_OFFERING_ALLOW
    )


def _preflight(input_data: OptimizationInput) -> tuple[list[dict[str, Any]], list[str]]:
    conflicts: list[dict[str, Any]] = []
    unknowns: list[str] = []
    course_by_code = {course.code: course for course in input_data.courses}
    candidates_by_course: dict[str, list[CandidateFact]] = defaultdict(list)
    candidate_map: dict[tuple[str, str], CandidateFact] = {}
    for candidate in input_data.candidates:
        candidates_by_course[candidate.course_code].append(candidate)
        candidate_map[(candidate.course_code, candidate.term_code)] = candidate
        if (
            candidate.offering_state.upper() not in {"OFFERED", "NOT_OFFERED"}
            and input_data.preferences.unknown_offering_policy == UNKNOWN_OFFERING_ALLOW
        ):
            unknowns.append(
                f"UNKNOWN_OFFERING_ASSUMPTION:{candidate.course_code}:{candidate.term_code}"
            )
    locked_by_course: dict[str, list[str]] = defaultdict(list)
    for locked in input_data.locked_choices:
        locked_by_course[locked.course_code].append(locked.term_code)
        locked_candidate = candidate_map.get((locked.course_code, locked.term_code))
        if locked.course_code not in course_by_code:
            conflicts.append(
                {
                    "code": "LOCKED_COURSE_UNKNOWN",
                    "detail": f"El curso bloqueado {locked.course_code} no pertenece al snapshot.",
                    "course_code": locked.course_code,
                    "term_code": locked.term_code,
                }
            )
        elif locked_candidate is None:
            conflicts.append(
                {
                    "code": "LOCKED_TERM_UNAVAILABLE",
                    "detail": f"No existe una opción de {locked.course_code} en {locked.term_code}.",
                    "course_code": locked.course_code,
                    "term_code": locked.term_code,
                }
            )
        elif locked_candidate.course_code in input_data.passed_courses:
            conflicts.append(
                {
                    "code": "LOCKED_COURSE_ALREADY_PASSED",
                    "detail": f"El curso bloqueado {locked.course_code} ya figura como aprobado en la historia.",
                    "course_code": locked.course_code,
                    "term_code": locked.term_code,
                }
            )
        elif _candidate_blocked(input_data, locked_candidate):
            conflicts.append(
                {
                    "code": "LOCKED_OFFERING_UNAVAILABLE",
                    "detail": f"La oferta bloqueada de {locked.course_code} en {locked.term_code} no es utilizable.",
                    "course_code": locked.course_code,
                    "term_code": locked.term_code,
                }
            )
        elif (
            locked.selected_section_id is not None
            and locked_candidate.selected_section_id != locked.selected_section_id
        ):
            conflicts.append(
                {
                    "code": "LOCKED_SECTION_MISMATCH",
                    "detail": f"La sección bloqueada de {locked.course_code} no coincide con la opción del snapshot.",
                    "course_code": locked.course_code,
                    "term_code": locked.term_code,
                }
            )
    for course_code, terms in locked_by_course.items():
        if len(terms) > 1:
            conflicts.append(
                {
                    "code": "LOCKED_COURSE_MULTIPLE_TERMS",
                    "detail": f"{course_code} está bloqueado en más de un período.",
                    "course_code": course_code,
                    "term_code": None,
                }
            )
    term_by_code = {term.code: term for term in input_data.terms}
    locked_candidates_by_term: dict[str, list[CandidateFact]] = defaultdict(list)
    for locked in input_data.locked_choices:
        locked_candidate = candidate_map.get((locked.course_code, locked.term_code))
        if locked_candidate is not None:
            locked_candidates_by_term[locked.term_code].append(locked_candidate)
    for term_code, locked_candidates in locked_candidates_by_term.items():
        term = term_by_code[term_code]
        if term.starts_on is None or term.ends_on is None:
            continue
        for index, left in enumerate(locked_candidates):
            for right in locked_candidates[index + 1 :]:
                if not left.meetings or not right.meetings:
                    continue
                schedule = evaluate_schedule(
                    list(left.meetings) + list(right.meetings),
                    term_start=term.starts_on,
                    term_end=term.ends_on,
                )
                if schedule.state == "CONFLICT":
                    conflicts.append(
                        {
                            "code": "LOCKED_SCHEDULE_CONFLICT",
                            "detail": f"Las secciones bloqueadas de {left.course_code} y {right.course_code} se solapan.",
                            "course_code": left.course_code,
                            "other_course_code": right.course_code,
                            "term_code": term_code,
                        }
                    )
                elif schedule.state == "UNKNOWN":
                    unknowns.extend(schedule.unknown_reasons)
    for course in input_data.courses:
        viable = [
            candidate
            for candidate in candidates_by_course.get(course.code, [])
            if not _candidate_blocked(input_data, candidate)
        ]
        required = course.mandatory and course.code not in input_data.passed_courses
        if required and not viable:
            conflicts.append(
                {
                    "code": "MANDATORY_COURSE_UNAVAILABLE",
                    "detail": f"No existe una oferta utilizable para el curso obligatorio {course.code}.",
                    "course_code": course.code,
                }
            )
        if required and any(_contains_unknown_rule(rule) for rule in course.prerequisite_rules):
            unknowns.append(f"PREREQUISITE_RULE_UNKNOWN:{course.code}")
        if required and course.credits is None:
            unknowns.append(f"COURSE_CREDITS_UNKNOWN:{course.code}")
    group_by_code = {group.code: group for group in input_data.groups}
    for group in input_data.groups:
        members = {
            course.code: course
            for course in input_data.courses
            if any(item.group_code == group.code for item in course.memberships)
            and course.code not in input_data.passed_courses
        }
        known_capacity = sum(
            course.credits or 0
            for course in members.values()
            if any(
                not _candidate_blocked(input_data, candidate)
                for candidate in candidates_by_course.get(course.code, [])
            )
        )
        has_unknown_credits = any(
            course.credits is None
            and any(
                not _candidate_blocked(input_data, candidate)
                for candidate in candidates_by_course.get(course.code, [])
            )
            for course in members.values()
        )
        if known_capacity < group.required_credits:
            if has_unknown_credits:
                unknowns.append(f"GROUP_CREDITS_UNKNOWN:{group.code}")
            else:
                conflicts.append(
                    {
                        "code": "GROUP_CREDIT_CAPACITY",
                        "detail": f"El grupo {group.code} requiere {group.required_credits} créditos y las opciones ofrecen {known_capacity}.",
                        "group_code": group.code,
                    }
                )
    if input_data.preferences.credit_target is not None:
        known_capacity = sum(
            course.credits or 0
            for course in input_data.courses
            if course.code not in input_data.passed_courses
            and any(
                not _candidate_blocked(input_data, candidate)
                for candidate in candidates_by_course.get(course.code, [])
            )
        )
        if known_capacity < input_data.preferences.credit_target:
            conflicts.append(
                {
                    "code": "CREDIT_TARGET_CAPACITY",
                    "detail": f"El objetivo requiere {input_data.preferences.credit_target} créditos y la capacidad conocida es {known_capacity}.",
                }
            )
    del group_by_code
    return conflicts, sorted(set(unknowns))


def _compile_rule(
    model: Any,
    rule: AuditRule,
    *,
    target_order: int,
    input_data: OptimizationInput,
    x_by_course: dict[str, list[tuple[int, Any]]],
    group_assignments: dict[tuple[str, str], list[tuple[int, Any, int]]],
    name: str,
) -> Any:
    passed = input_data.passed_courses
    in_progress = input_data.in_progress_courses
    if isinstance(rule, All):
        return _all_literal(
            model,
            [
                _compile_rule(
                    model,
                    child,
                    target_order=target_order,
                    input_data=input_data,
                    x_by_course=x_by_course,
                    group_assignments=group_assignments,
                    name=f"{name}_all_{index}",
                )
                for index, child in enumerate(rule.children)
            ],
            name,
        )
    if isinstance(rule, AnyOf):
        return _any_literal(
            model,
            [
                _compile_rule(
                    model,
                    child,
                    target_order=target_order,
                    input_data=input_data,
                    x_by_course=x_by_course,
                    group_assignments=group_assignments,
                    name=f"{name}_any_{index}",
                )
                for index, child in enumerate(rule.children)
            ],
            name,
        )
    if isinstance(rule, Not):
        child = _compile_rule(
            model,
            rule.child,
            target_order=target_order,
            input_data=input_data,
            x_by_course=x_by_course,
            group_assignments=group_assignments,
            name=f"{name}_not_child",
        )
        literal = model.new_bool_var(name)
        model.add(literal + child == 1)
        return literal
    if isinstance(rule, (CoursePassed, CourseInProgress, CoursePassedOrInProgress, Corequisite)):
        code = rule.course_code
        if isinstance(rule, CoursePassed):
            allowed_order = target_order - 1
            already = code in passed
        elif isinstance(rule, Corequisite):
            allowed_order = target_order
            already = code in passed or code in in_progress
        elif isinstance(rule, CourseInProgress):
            allowed_order = target_order
            already = code in in_progress
        else:
            allowed_order = target_order
            already = code in passed or code in in_progress
        options = [
            variable for order, variable in x_by_course.get(code, []) if order <= allowed_order
        ]
        if already:
            return _constant(model, True, name)
        return _equivalence_literal(model, _sum(options), name)
    if isinstance(rule, EquivalentCoursePassed):
        children = [
            _compile_rule(
                model,
                CoursePassed(code),
                target_order=target_order,
                input_data=input_data,
                x_by_course=x_by_course,
                group_assignments=group_assignments,
                name=f"{name}_{index}",
            )
            for index, code in enumerate(rule.course_codes)
        ]
        return _any_literal(model, children, name)
    if isinstance(rule, MandatoryCoursesCompleted):
        children = [
            _compile_rule(
                model,
                CoursePassed(code),
                target_order=target_order,
                input_data=input_data,
                x_by_course=x_by_course,
                group_assignments=group_assignments,
                name=f"{name}_{index}",
            )
            for index, code in enumerate(rule.course_codes)
        ]
        return _all_literal(model, children, name)
    if isinstance(rule, TotalCredits):
        expression = _sum(
            [
                variable * (course.credits or 0)
                for course_code, values in x_by_course.items()
                for order, variable in values
                if order <= target_order
                for course in input_data.courses
                if course.code == course_code
            ]
        )
        return _comparison_literal(model, expression, rule.operator, rule.value, name)
    if isinstance(rule, CreditsInGroup):
        expression = _sum(
            [
                variable * credits
                for (group_code, _course_code), values in group_assignments.items()
                if group_code == rule.group
                for order, variable, credits in values
                if order <= target_order
            ]
        )
        return _comparison_literal(model, expression, rule.operator, rule.value, name)
    if isinstance(rule, GroupCompleted):
        group = next((item for item in input_data.groups if item.code == rule.group), None)
        required = group.required_credits if group else 0
        expression = _sum(
            [
                variable * credits
                for (group_code, _course_code), values in group_assignments.items()
                if group_code == rule.group
                for order, variable, credits in values
                if order <= target_order
            ]
        )
        return _comparison_literal(model, expression, ">=", required, name)
    return _constant(model, False, name)


def _build_model(input_data: OptimizationInput, fixed: dict[str, int]) -> _ModelState:
    model = cp_model.CpModel()
    term_orders = _term_order(input_data)
    term_map = {term.code: term for term in input_data.terms}
    course_map = {course.code: course for course in input_data.courses}
    candidate_map = {
        (candidate.course_code, candidate.term_code): candidate
        for candidate in input_data.candidates
    }
    x: dict[tuple[str, str], Any] = {}
    x_by_course: dict[str, list[tuple[int, Any]]] = defaultdict(list)
    unknown_candidates: set[tuple[str, str]] = set()
    for candidate in input_data.candidates:
        variable = model.new_bool_var(f"x_{candidate.course_code}_{candidate.term_code}")
        key = (candidate.course_code, candidate.term_code)
        x[key] = variable
        x_by_course[candidate.course_code].append((term_orders[candidate.term_code], variable))
        if candidate.offering_state.upper() not in {"OFFERED", "NOT_OFFERED"}:
            unknown_candidates.add(key)
        if candidate.course_code in input_data.passed_courses or _candidate_blocked(
            input_data, candidate
        ):
            model.add(variable == 0)
    for course in input_data.courses:
        values = [variable for _order, variable in x_by_course.get(course.code, [])]
        if values:
            model.add(_sum(values) <= 1)
        elif course.mandatory and course.code not in input_data.passed_courses:
            model.add(0 >= 1)

    group_assignments: dict[tuple[str, str], list[tuple[int, Any, int]]] = defaultdict(list)
    for candidate in input_data.candidates:
        variable = x[(candidate.course_code, candidate.term_code)]
        course = course_map[candidate.course_code]
        for membership in course.memberships:
            assignment = model.new_bool_var(
                f"y_{candidate.course_code}_{candidate.term_code}_{membership.group_code}"
            )
            model.add(assignment <= variable)
            group_assignments[(membership.group_code, course.code)].append(
                (term_orders[candidate.term_code], assignment, course.credits or 0)
            )
    for course in input_data.courses:
        assignments = [
            assignment
            for (course_code, _group_code), values in group_assignments.items()
            if course_code == course.code
            for _order, assignment, _credits in values
        ]
        values = [variable for _order, variable in x_by_course.get(course.code, [])]
        if assignments:
            model.add(_sum(assignments) <= _sum(values))
    group_by_code = {group.code: group for group in input_data.groups}
    for group_code, group in group_by_code.items():
        expression = _sum(
            [
                assignment * credits
                for (candidate_group, _course_code), values in group_assignments.items()
                if candidate_group == group_code
                for _order, assignment, credits in values
            ]
        )
        model.add(expression >= group.required_credits)
    for course in input_data.courses:
        if course.mandatory and course.code not in input_data.passed_courses:
            model.add(
                _sum([variable for _order, variable in x_by_course.get(course.code, [])]) >= 1
            )
    if input_data.preferences.credit_target is not None:
        model.add(
            _sum(
                [
                    variable * (course.credits or 0)
                    for course in input_data.courses
                    for _order, variable in x_by_course.get(course.code, [])
                ]
            )
            >= input_data.preferences.credit_target
        )
    for term in input_data.terms:
        variables = [
            variable for (course_code, term_code), variable in x.items() if term_code == term.code
        ]
        active = model.new_bool_var(f"active_{term.code}")
        if variables:
            model.add_max_equality(active, variables)
        else:
            model.add(active == 0)
        credits_expression = _sum(
            [
                variable * (course_map[course_code].credits or 0)
                for (course_code, term_code), variable in x.items()
                if term_code == term.code
            ]
        )
        model.add(credits_expression <= input_data.preferences.max_credits_per_term)
        model.add(credits_expression >= input_data.preferences.min_credits_per_term * active)

    for course in input_data.courses:
        for candidate in input_data.candidates:
            if candidate.course_code != course.code:
                continue
            variable = x[(candidate.course_code, candidate.term_code)]
            target_order = term_orders[candidate.term_code]
            for index, rule in enumerate(course.prerequisite_rules):
                literal = _compile_rule(
                    model,
                    rule,
                    target_order=target_order,
                    input_data=input_data,
                    x_by_course=x_by_course,
                    group_assignments=group_assignments,
                    name=f"rule_{course.code}_{candidate.term_code}_{index}",
                )
                model.add_implication(variable, literal)

    schedule_unknowns: list[str] = []
    by_term: dict[str, list[CandidateFact]] = defaultdict(list)
    for candidate in input_data.candidates:
        by_term[candidate.term_code].append(candidate)
    for term_code, candidates in by_term.items():
        term = term_map[term_code]
        for index, left in enumerate(candidates):
            for right in candidates[index + 1 :]:
                if left.selected_section_id is None or right.selected_section_id is None:
                    continue
                if not left.meetings or not right.meetings:
                    continue
                if term.starts_on is None or term.ends_on is None:
                    schedule_unknowns.append(f"SCHEDULE_DATES_UNKNOWN:{term_code}")
                    continue
                schedule = evaluate_schedule(
                    list(left.meetings) + list(right.meetings),
                    term_start=term.starts_on,
                    term_end=term.ends_on,
                )
                if schedule.state == "CONFLICT":
                    model.add(
                        x[(left.course_code, left.term_code)]
                        + x[(right.course_code, right.term_code)]
                        <= 1
                    )
                elif schedule.state == "UNKNOWN":
                    schedule_unknowns.extend(schedule.unknown_reasons)

    locked_by_key = {(item.course_code, item.term_code): item for item in input_data.locked_choices}
    for key, locked in locked_by_key.items():
        if key in x:
            model.add(x[key] == 1)
            candidate = candidate_map[key]
            if (
                locked.selected_section_id is not None
                and candidate.selected_section_id != locked.selected_section_id
            ):
                model.add(x[key] == 0)
    objective_expressions = _objective_expressions(
        model, input_data, x, course_map, unknown_candidates
    )
    for objective_name, value in fixed.items():
        model.add(objective_expressions[objective_name] == value)
    return _ModelState(
        model=model,
        x=x,
        y={
            (group_code, course_code, term_code): assignment
            for (group_code, course_code), values in group_assignments.items()
            for term_order, assignment, _credits in values
            for term_code, order in term_orders.items()
            if order == term_order
        },
        objective_expressions=objective_expressions,
        candidates=candidate_map,
        courses=course_map,
        terms=term_map,
        unknown_candidates=unknown_candidates,
        schedule_unknowns=sorted(set(schedule_unknowns)),
    )


def _objective_expressions(
    model: Any,
    input_data: OptimizationInput,
    x: dict[tuple[str, str], Any],
    course_map: dict[str, CourseFact],
    unknown_candidates: set[tuple[str, str]],
) -> dict[str, Any]:
    max_order = max((term.order for term in input_data.terms), default=0)
    end_term = model.new_int_var(0, max_order, "last_term")
    all_variables = list(x.values())
    if all_variables:
        for (_course_code, term_code), variable in x.items():
            term = next(item for item in input_data.terms if item.code == term_code)
            model.add(end_term >= term.order * variable)
        model.add(end_term <= max_order * _sum(all_variables))
    else:
        model.add(end_term == 0)
    unknown_count = model.new_int_var(0, len(unknown_candidates), "unknown_offerings")
    model.add(unknown_count == _sum([x[key] for key in sorted(unknown_candidates)]))
    preferred = input_data.preferences.preferred_credits_per_term
    if preferred is None:
        target = input_data.preferences.credit_target or 0
        preferred = max(
            input_data.preferences.min_credits_per_term,
            min(
                input_data.preferences.max_credits_per_term, target // max(len(input_data.terms), 1)
            ),
        )
    deviations: list[Any] = []
    for term in input_data.terms:
        credits = _sum(
            [
                variable * (course_map[course_code].credits or 0)
                for (course_code, term_code), variable in x.items()
                if term_code == term.code
            ]
        )
        deviation = model.new_int_var(
            0,
            input_data.preferences.max_credits_per_term + preferred,
            f"credit_deviation_{term.code}",
        )
        model.add_abs_equality(deviation, credits - preferred)
        deviations.append(deviation)
    balance = model.new_int_var(
        0,
        max(len(input_data.terms), 1) * (input_data.preferences.max_credits_per_term + preferred),
        "credit_balance",
    )
    model.add(balance == _sum(deviations))
    penalty_max = sum(course.preference_penalty for course in input_data.courses)
    preference_penalty = model.new_int_var(0, penalty_max, "preference_penalty")
    model.add(
        preference_penalty
        == _sum(
            [
                variable * course_map[course_code].preference_penalty
                for (course_code, _term_code), variable in x.items()
            ]
        )
    )
    return {
        "last_term": end_term,
        "unknown_offerings": unknown_count,
        "credit_balance": balance,
        "preference_penalty": preference_penalty,
    }


def _selected_courses(
    input_data: OptimizationInput, state: _ModelState, solver: Any
) -> tuple[SelectedCourse, ...]:
    selected: list[SelectedCourse] = []
    for key, variable in sorted(state.x.items(), key=lambda item: (item[0][1], item[0][0])):
        if solver.value(variable) != 1:
            continue
        candidate = state.candidates[key]
        course = state.courses[candidate.course_code]
        selected.append(
            SelectedCourse(
                course_id=candidate.course_id,
                course_code=candidate.course_code,
                term_code=candidate.term_code,
                credits=course.credits,
                selected_section_id=candidate.selected_section_id,
                offering_state=candidate.offering_state,
            )
        )
    return tuple(selected)


def _explain_selected(
    input_data: OptimizationInput, selected: tuple[SelectedCourse, ...], assumptions: list[str]
) -> tuple[DecisionExplanation, ...]:
    course_map = {course.code: course for course in input_data.courses}
    selected_codes = {item.course_code for item in selected}
    explanations: list[DecisionExplanation] = []
    for item in selected:
        course = course_map[item.course_code]
        groups = tuple(sorted({membership.group_code for membership in course.memberships}))
        unlocks = tuple(
            sorted(
                other.code
                for other in input_data.courses
                if other.code not in selected_codes
                and any(
                    item.course_code in _course_codes_in_rule(rule)
                    for rule in other.prerequisite_rules
                )
            )
        )
        reasons: list[str] = []
        if course.mandatory:
            reasons.append("MANDATORY_COURSE")
        if groups:
            reasons.append("GROUP_CREDIT_COVERAGE")
        if any(
            locked.course_code == item.course_code and locked.term_code == item.term_code
            for locked in input_data.locked_choices
        ):
            reasons.append("LOCKED_USER_CHOICE")
        if item.selected_section_id:
            reasons.append("SELECTED_SECTION_SCHEDULE")
        if item.offering_state.upper() not in {"OFFERED", "NOT_OFFERED"}:
            reasons.append("UNKNOWN_OFFERING_ASSUMPTION")
        explanations.append(
            DecisionExplanation(
                course_code=item.course_code,
                term_code=item.term_code,
                reasons=tuple(reasons or ["SATISFIES_HARD_CONSTRAINTS"]),
                satisfies_groups=groups,
                unlocks_courses=unlocks,
                assumptions=tuple(
                    value
                    for value in assumptions
                    if value.startswith(f"UNKNOWN_OFFERING_ASSUMPTION:{item.course_code}:")
                ),
            )
        )
    return tuple(explanations)


def _result(
    input_data: OptimizationInput,
    *,
    status: str,
    start: float,
    selected: tuple[SelectedCourse, ...] = (),
    objectives: tuple[OptimizationObjective, ...] = (),
    conflicts: tuple[dict[str, Any], ...] = (),
    assumptions: tuple[str, ...] = (),
    termination_reason: str,
) -> OptimizationResult:
    return OptimizationResult(
        status=status,
        input_hash=input_data.input_hash,
        solver_version=SOLVER_VERSION,
        selected_courses=selected,
        objectives=objectives,
        explanations=_explain_selected(input_data, selected, list(assumptions)),
        conflicts=conflicts,
        assumptions=assumptions,
        termination_reason=termination_reason,
        wall_time_seconds=max(0, int(round(monotonic() - start))),
    ).with_output_hash()


class _CancellationCallback(cp_model.CpSolverSolutionCallback):
    def __init__(self, cancel_event: Event | None) -> None:
        super().__init__()
        self.cancel_event = cancel_event

    def on_solution_callback(self) -> None:
        if self.cancel_event is not None and self.cancel_event.is_set():
            self.stop_search()


def solve_optimization(
    input_data: OptimizationInput,
    *,
    cancel_event: Event | None = None,
) -> OptimizationResult:
    """Solve a portable input with hard constraints and documented lexicographic passes."""

    start = monotonic()
    conflicts, unknowns = _preflight(input_data)
    if conflicts:
        return _result(
            input_data,
            status=OptimizationStatus.INFEASIBLE.value,
            start=start,
            conflicts=tuple(conflicts),
            assumptions=tuple(unknowns),
            termination_reason="preflight_conflict",
        )
    if unknowns and any(
        item.startswith("PREREQUISITE_RULE_UNKNOWN")
        or item.startswith("COURSE_CREDITS_UNKNOWN")
        or item.startswith("GROUP_CREDITS_UNKNOWN")
        for item in unknowns
    ):
        return _result(
            input_data,
            status=OptimizationStatus.UNKNOWN.value,
            start=start,
            assumptions=tuple(unknowns),
            termination_reason="required_facts_unknown",
        )
    if cancel_event is not None and cancel_event.is_set():
        return _result(
            input_data,
            status=OptimizationStatus.UNKNOWN.value,
            start=start,
            assumptions=tuple(unknowns),
            termination_reason="cancelled",
        )
    fixed: dict[str, int] = {}
    objective_specs = (
        ("last_term", "Minimiza el último período ocupado; evita retrasar la finalización."),
        ("unknown_offerings", "Minimiza cursos cuya oferta futura está explícitamente UNKNOWN."),
        ("credit_balance", "Minimiza la desviación absoluta respecto de la carga preferida."),
        (
            "preference_penalty",
            "Minimiza sólo la penalización declarada por las preferencias del input.",
        ),
    )
    final_state: _ModelState | None = None
    final_solver: Any = None
    objective_values: list[OptimizationObjective] = []
    for objective_name, explanation in objective_specs:
        remaining = input_data.preferences.time_limit_seconds - (monotonic() - start)
        if remaining <= 0:
            break
        state = _build_model(input_data, fixed)
        state.model.minimize(state.objective_expressions[objective_name])
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(0.01, remaining)
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = input_data.preferences.random_seed
        callback = _CancellationCallback(cancel_event)
        status = solver.solve(state.model, callback)
        if status == cp_model.INFEASIBLE:
            return _result(
                input_data,
                status=OptimizationStatus.INFEASIBLE.value,
                start=start,
                conflicts=tuple(
                    [
                        {
                            "code": "SOLVER_INFEASIBLE",
                            "detail": "Las restricciones duras no tienen una asignación compatible.",
                        }
                    ]
                ),
                assumptions=tuple(sorted(set(unknowns + state.schedule_unknowns))),
                termination_reason="solver_proved_infeasible",
            )
        if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
            selected = (
                _selected_courses(input_data, final_state, final_solver)
                if final_state is not None and final_solver is not None
                else ()
            )
            return _result(
                input_data,
                status=OptimizationStatus.FEASIBLE.value
                if selected
                else OptimizationStatus.UNKNOWN.value,
                start=start,
                selected=selected,
                objectives=tuple(objective_values),
                assumptions=tuple(sorted(set(unknowns + state.schedule_unknowns))),
                termination_reason="cancelled"
                if cancel_event and cancel_event.is_set()
                else "time_limit",
            )
        value = int(solver.value(state.objective_expressions[objective_name]))
        fixed[objective_name] = value
        objective_values.append(OptimizationObjective(objective_name, value, explanation))
        final_state = state
        final_solver = solver
        if status != cp_model.OPTIMAL:
            selected = _selected_courses(input_data, state, solver)
            return _result(
                input_data,
                status=OptimizationStatus.FEASIBLE.value,
                start=start,
                selected=selected,
                objectives=tuple(objective_values),
                assumptions=tuple(sorted(set(unknowns + state.schedule_unknowns))),
                termination_reason="cancelled"
                if cancel_event and cancel_event.is_set()
                else "time_limit",
            )
    if final_state is None or final_solver is None:
        return _result(
            input_data,
            status=OptimizationStatus.UNKNOWN.value,
            start=start,
            assumptions=tuple(unknowns),
            termination_reason="time_limit",
        )
    selected = _selected_courses(input_data, final_state, final_solver)
    final_assumptions = tuple(sorted(set(unknowns + final_state.schedule_unknowns)))
    final_status = OptimizationStatus.FEASIBLE.value
    termination = "time_limit"
    if len(objective_values) == len(objective_specs) and not (
        cancel_event and cancel_event.is_set()
    ):
        final_status = OptimizationStatus.OPTIMAL.value
        termination = "all_lexicographic_objectives_proven"
    elif cancel_event and cancel_event.is_set():
        termination = "cancelled"
    return _result(
        input_data,
        status=final_status,
        start=start,
        selected=selected,
        objectives=tuple(objective_values),
        assumptions=final_assumptions,
        termination_reason=termination,
    )
