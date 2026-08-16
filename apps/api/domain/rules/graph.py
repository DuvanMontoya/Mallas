from __future__ import annotations

from collections.abc import Mapping

from .ast import (
    All,
    AnyOf,
    AuditRule,
    Corequisite,
    CoursePassed,
    CoursePassedOrInProgress,
    EquivalentCoursePassed,
    Not,
)


def direct_course_dependencies(rule: AuditRule) -> frozenset[str]:
    """Return direct course references without interpreting rule semantics."""

    if isinstance(rule, (CoursePassed, CoursePassedOrInProgress, Corequisite)):
        return frozenset({rule.course_code})
    if isinstance(rule, EquivalentCoursePassed):
        return frozenset(rule.course_codes)
    if isinstance(rule, (All, AnyOf)):
        return frozenset(
            dependency
            for child in rule.children
            for dependency in direct_course_dependencies(child)
        )
    if isinstance(rule, Not):
        return direct_course_dependencies(rule.child)
    return frozenset()


def find_requirement_cycles(
    requirements: Mapping[str, AuditRule],
) -> tuple[tuple[str, ...], ...]:
    """Find deterministic cycles in an owner-course -> direct dependency graph."""

    graph = {owner: set(direct_course_dependencies(rule)) for owner, rule in requirements.items()}
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str, stack: tuple[str, ...]) -> None:
        if node in visiting:
            start = stack.index(node)
            cycles.add(stack[start:] + (node,))
            return
        if node in visited:
            return
        visiting.add(node)
        for dependency in sorted(graph.get(node, set())):
            if dependency in graph:
                visit(dependency, (*stack, node))
        visiting.remove(node)
        visited.add(node)

    for owner in sorted(graph):
        visit(owner, ())
    return tuple(sorted(cycles))
