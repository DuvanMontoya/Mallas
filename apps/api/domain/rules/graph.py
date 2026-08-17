from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass

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
)


@dataclass(frozen=True, slots=True)
class GraphNode:
    """A semantic graph node; it is independent of any UI graph library."""

    node_id: str
    kind: str
    label: str
    course_code: str | None = None
    condition_type: str | None = None
    requirement_code: str | None = None
    path: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """A directed explanation edge from a prerequisite/condition to a target."""

    edge_id: str
    source: str
    target: str
    edge_type: str
    semantic: str
    requirement_code: str
    path: tuple[int, ...] = ()
    direct: bool = True


@dataclass(frozen=True, slots=True)
class CourseRelation:
    """A direct AST course reference used for closure and unlock analysis."""

    source: str
    target: str
    relation_type: str
    semantic: str
    requirement_code: str
    condition_node_id: str | None = None
    direct: bool = True


@dataclass(frozen=True, slots=True)
class GraphProjection:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    course_relations: tuple[CourseRelation, ...]
    cycles: tuple[tuple[str, ...], ...]


def _course_node_id(code: str) -> str:
    return f"course:{code}"


def _condition_node_id(owner: str, requirement_code: str, path: tuple[int, ...]) -> str:
    suffix = "root" if not path else ".".join(str(part) for part in path)
    return f"condition:{owner}:{requirement_code}:{suffix}"


def _condition_node(
    nodes: dict[str, GraphNode],
    *,
    owner: str,
    requirement_code: str,
    path: tuple[int, ...],
    condition_type: str,
) -> str:
    node_id = _condition_node_id(owner, requirement_code, path)
    nodes.setdefault(
        node_id,
        GraphNode(
            node_id=node_id,
            kind="CONDITION",
            label=condition_type,
            condition_type=condition_type,
            requirement_code=requirement_code,
            path=path,
        ),
    )
    return node_id


def _add_edge(
    edges: dict[str, GraphEdge],
    *,
    source: str,
    target: str,
    edge_type: str,
    semantic: str,
    requirement_code: str,
    path: tuple[int, ...],
    direct: bool = True,
) -> None:
    edge_id = (
        f"edge:{requirement_code}:{'.'.join(map(str, path)) or 'root'}:"
        f"{edge_type}:{source}->{target}"
    )
    edges.setdefault(
        edge_id,
        GraphEdge(
            edge_id=edge_id,
            source=source,
            target=target,
            edge_type=edge_type,
            semantic=semantic,
            requirement_code=requirement_code,
            path=path,
            direct=direct,
        ),
    )


def _course_leaf_relation_type(rule: AuditRule, *, nested: bool) -> tuple[str, str]:
    if isinstance(rule, Corequisite):
        return "COREQUISITE", "COREQUISITE"
    if isinstance(rule, CoursePassedOrInProgress):
        return (
            ("CONDITION_INPUT", "PASSED_OR_IN_PROGRESS")
            if nested
            else (
                "PREREQUISITE",
                "PASSED_OR_IN_PROGRESS",
            )
        )
    if isinstance(rule, CourseInProgress):
        return ("CONDITION_INPUT", "IN_PROGRESS") if nested else ("PREREQUISITE", "IN_PROGRESS")
    return ("CONDITION_INPUT", "PASSED") if nested else ("PREREQUISITE", "PASSED")


def _condition_type(rule: AuditRule) -> str:
    if isinstance(rule, All):
        return "ALL"
    if isinstance(rule, AnyOf):
        return "ANY"
    if isinstance(rule, CreditsInGroup):
        return "CREDITS_IN_GROUP"
    if isinstance(rule, CreditsInComponent):
        return "CREDITS_IN_COMPONENT"
    if isinstance(rule, TotalCredits):
        return "TOTAL_CREDITS"
    if isinstance(rule, PercentageOfPlan):
        return "PERCENTAGE_OF_PLAN"
    if isinstance(rule, GroupCompleted):
        return "GROUP_COMPLETED"
    if isinstance(rule, MandatoryCoursesCompleted):
        return "MANDATORY_COURSES_COMPLETED"
    if isinstance(rule, MinimumGrade):
        return "MINIMUM_GRADE"
    if isinstance(rule, ExternalRequirement):
        return "EXTERNAL_REQUIREMENT"
    if isinstance(rule, Unknown):
        return "UNKNOWN"
    if isinstance(rule, EquivalentCoursePassed):
        return "EQUIVALENCE"
    if isinstance(rule, Not):
        return "NOT"
    return type(rule).__name__.upper()


def project_rule_graph(
    requirements: Mapping[tuple[str, str], AuditRule],
) -> GraphProjection:
    """Project AST rules without losing logical conditions.

    Keys are ``(owner_course_code, requirement_code)``. Course references are
    never collapsed into a plain edge when the AST expresses a compound or
    threshold condition. The result is deterministic and has no ORM/UI
    dependencies.
    """

    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}
    relations: list[CourseRelation] = []

    def add_course(code: str) -> str:
        node_id = _course_node_id(code)
        nodes.setdefault(
            node_id,
            GraphNode(node_id=node_id, kind="COURSE", label=code, course_code=code),
        )
        return node_id

    def add_relation(
        *,
        source: str,
        target: str,
        relation_type: str,
        semantic: str,
        requirement_code: str,
        condition_node_id: str | None,
    ) -> None:
        relations.append(
            CourseRelation(
                source=source,
                target=target,
                relation_type=relation_type,
                semantic=semantic,
                requirement_code=requirement_code,
                condition_node_id=condition_node_id,
            )
        )

    def visit(
        rule: AuditRule,
        *,
        owner: str,
        requirement_code: str,
        path: tuple[int, ...],
        parent_condition_id: str | None = None,
        parent_semantic: str = "CONDITION",
    ) -> str:
        nested = parent_condition_id is not None
        if isinstance(
            rule, (CoursePassed, CourseInProgress, CoursePassedOrInProgress, Corequisite)
        ):
            code = rule.course_code
            node_id = add_course(code)
            relation_type, semantic = _course_leaf_relation_type(rule, nested=nested)
            add_relation(
                source=code,
                target=owner,
                relation_type=relation_type,
                semantic=parent_semantic if nested else semantic,
                requirement_code=requirement_code,
                condition_node_id=parent_condition_id,
            )
            return node_id

        if isinstance(rule, EquivalentCoursePassed):
            node_id = _condition_node(
                nodes,
                owner=owner,
                requirement_code=requirement_code,
                path=path,
                condition_type=_condition_type(rule),
            )
            for index, code in enumerate(rule.course_codes):
                course_id = add_course(code)
                child_path = (*path, index)
                _add_edge(
                    edges,
                    source=course_id,
                    target=node_id,
                    edge_type="ALTERNATIVE_INPUT",
                    semantic="EQUIVALENCE",
                    requirement_code=requirement_code,
                    path=child_path,
                )
                add_relation(
                    source=code,
                    target=owner,
                    relation_type="ALTERNATIVE_INPUT",
                    semantic="EQUIVALENCE",
                    requirement_code=requirement_code,
                    condition_node_id=node_id,
                )
            return node_id

        if isinstance(rule, MandatoryCoursesCompleted):
            node_id = _condition_node(
                nodes,
                owner=owner,
                requirement_code=requirement_code,
                path=path,
                condition_type=_condition_type(rule),
            )
            for index, code in enumerate(rule.course_codes):
                course_id = add_course(code)
                child_path = (*path, index)
                _add_edge(
                    edges,
                    source=course_id,
                    target=node_id,
                    edge_type="THRESHOLD_INPUT",
                    semantic="MANDATORY_COURSE",
                    requirement_code=requirement_code,
                    path=child_path,
                )
                add_relation(
                    source=code,
                    target=owner,
                    relation_type="THRESHOLD_INPUT",
                    semantic="MANDATORY_COURSE",
                    requirement_code=requirement_code,
                    condition_node_id=node_id,
                )
            return node_id

        if isinstance(rule, (All, AnyOf)):
            condition_type = _condition_type(rule)
            node_id = _condition_node(
                nodes,
                owner=owner,
                requirement_code=requirement_code,
                path=path,
                condition_type=condition_type,
            )
            for index, child in enumerate(rule.children):
                child_path = (*path, index)
                child_id = visit(
                    child,
                    owner=owner,
                    requirement_code=requirement_code,
                    path=child_path,
                    parent_condition_id=node_id,
                    parent_semantic=condition_type,
                )
                _add_edge(
                    edges,
                    source=child_id,
                    target=node_id,
                    edge_type="CONDITION_INPUT",
                    semantic=condition_type,
                    requirement_code=requirement_code,
                    path=child_path,
                )
            return node_id

        if isinstance(rule, Not):
            node_id = _condition_node(
                nodes,
                owner=owner,
                requirement_code=requirement_code,
                path=path,
                condition_type=_condition_type(rule),
            )
            child_id = visit(
                rule.child,
                owner=owner,
                requirement_code=requirement_code,
                path=(*path, 0),
                parent_condition_id=node_id,
                parent_semantic="NOT",
            )
            _add_edge(
                edges,
                source=child_id,
                target=node_id,
                edge_type="CONDITION_INPUT",
                semantic="NOT",
                requirement_code=requirement_code,
                path=(*path, 0),
            )
            return node_id

        condition_type = _condition_type(rule)
        node_id = _condition_node(
            nodes,
            owner=owner,
            requirement_code=requirement_code,
            path=path,
            condition_type=condition_type,
        )
        if isinstance(rule, MinimumGrade):
            course_id = add_course(rule.course_code)
            _add_edge(
                edges,
                source=course_id,
                target=node_id,
                edge_type="THRESHOLD_INPUT",
                semantic="MINIMUM_GRADE",
                requirement_code=requirement_code,
                path=(*path, 0),
            )
            add_relation(
                source=rule.course_code,
                target=owner,
                relation_type="THRESHOLD_INPUT",
                semantic="MINIMUM_GRADE",
                requirement_code=requirement_code,
                condition_node_id=node_id,
            )
        return node_id

    for (owner, requirement_code), rule in sorted(requirements.items()):
        owner_id = add_course(owner)
        root_id = visit(rule, owner=owner, requirement_code=requirement_code, path=())
        if isinstance(rule, Corequisite):
            edge_type, semantic = "COREQUISITE", "COREQUISITE"
        elif isinstance(rule, (CoursePassed, CourseInProgress, CoursePassedOrInProgress)):
            edge_type, semantic = _course_leaf_relation_type(rule, nested=False)
        else:
            edge_type, semantic = "CONDITION_SATISFIES", type(rule).__name__.upper()
        _add_edge(
            edges,
            source=root_id,
            target=owner_id,
            edge_type=edge_type,
            semantic=semantic,
            requirement_code=requirement_code,
            path=(),
        )

    rules_by_owner: dict[str, list[AuditRule]] = {}
    for (owner, _), rule in sorted(requirements.items()):
        rules_by_owner.setdefault(owner, []).append(rule)
    cycle_input = {
        owner: rules[0] if len(rules) == 1 else All(tuple(rules))
        for owner, rules in rules_by_owner.items()
    }
    unique_relations = {
        (
            relation.source,
            relation.target,
            relation.relation_type,
            relation.semantic,
            relation.requirement_code,
            relation.condition_node_id,
        ): relation
        for relation in relations
    }
    return GraphProjection(
        nodes=tuple(sorted(nodes.values(), key=lambda node: node.node_id)),
        edges=tuple(sorted(edges.values(), key=lambda edge: edge.edge_id)),
        course_relations=tuple(
            sorted(
                unique_relations.values(),
                key=lambda relation: (
                    relation.source,
                    relation.target,
                    relation.requirement_code,
                    relation.relation_type,
                    relation.condition_node_id or "",
                ),
            )
        ),
        cycles=find_requirement_cycles(cycle_input),
    )


def transitive_course_dependencies(
    relations: tuple[CourseRelation, ...] | list[CourseRelation],
    *,
    include_corequisites: bool = False,
) -> dict[str, tuple[str, ...]]:
    """Return deterministic course descendants for direct AST relationships."""

    graph: dict[str, set[str]] = {}
    for relation in relations:
        if relation.relation_type == "COREQUISITE" and not include_corequisites:
            continue
        graph.setdefault(relation.source, set()).add(relation.target)
        graph.setdefault(relation.target, set())

    result: dict[str, tuple[str, ...]] = {}
    for source in sorted(graph):
        seen: set[str] = set()
        queue = deque(sorted(graph[source]))
        while queue:
            target = queue.popleft()
            if target in seen or target == source:
                continue
            seen.add(target)
            queue.extend(sorted(graph.get(target, set()) - seen))
        result[source] = tuple(sorted(seen))
    return result


def shortest_course_path(
    relations: tuple[CourseRelation, ...] | list[CourseRelation],
    source: str,
    target: str,
    *,
    include_corequisites: bool = False,
) -> tuple[str, ...] | None:
    """Return the lexicographically stable shortest course-code path."""

    adjacency: dict[str, set[str]] = {}
    for relation in relations:
        if relation.relation_type == "COREQUISITE" and not include_corequisites:
            continue
        adjacency.setdefault(relation.source, set()).add(relation.target)
        adjacency.setdefault(relation.target, set())
    if source == target:
        return (source,)
    queue: deque[tuple[str, ...]] = deque([(source,)])
    visited = {source}
    while queue:
        path = queue.popleft()
        for next_code in sorted(adjacency.get(path[-1], set())):
            if next_code in visited:
                continue
            next_path = (*path, next_code)
            if next_code == target:
                return next_path
            visited.add(next_code)
            queue.append(next_path)
    return None


def direct_course_dependencies(rule: AuditRule) -> frozenset[str]:
    """Return direct course references without interpreting rule semantics."""

    if isinstance(rule, (CoursePassed, CourseInProgress, CoursePassedOrInProgress, Corequisite)):
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
    if isinstance(rule, MandatoryCoursesCompleted):
        return frozenset(rule.course_codes)
    if isinstance(rule, MinimumGrade):
        return frozenset({rule.course_code})
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
