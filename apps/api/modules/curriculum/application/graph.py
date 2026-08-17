from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from domain.rules import (
    CourseRelation,
    GraphProjection,
    parse_rule,
    project_rule_graph,
    shortest_course_path,
    transitive_course_dependencies,
)
from domain.rules.errors import RuleSchemaError
from modules.observability.metrics import measure_domain_timing

from .map import build_curriculum_map

CONDITION_LABELS = {
    "ALL": "Todas las condiciones",
    "ANY": "Cualquier alternativa",
    "CREDITS_IN_GROUP": "Umbral de créditos en agrupación",
    "CREDITS_IN_COMPONENT": "Umbral de créditos en componente",
    "TOTAL_CREDITS": "Umbral de créditos totales",
    "PERCENTAGE_OF_PLAN": "Porcentaje mínimo del plan",
    "GROUP_COMPLETED": "Agrupación completada",
    "MANDATORY_COURSES_COMPLETED": "Cursos obligatorios completados",
    "MINIMUM_GRADE": "Nota mínima",
    "EXTERNAL_REQUIREMENT": "Requisito externo",
    "EQUIVALENCE": "Equivalencia de cursos",
    "NOT": "Condición negada",
    "UNKNOWN": "Condición por verificar",
}

EDGE_LABELS = {
    "PREREQUISITE": "Prerrequisito",
    "COREQUISITE": "Correquisito",
    "CONDITION_INPUT": "Entrada de condición",
    "ALTERNATIVE_INPUT": "Alternativa",
    "THRESHOLD_INPUT": "Entrada de umbral",
    "CONDITION_SATISFIES": "Condición satisfecha para cursar",
}


def _href(path: str, **query: object) -> str:
    from urllib.parse import quote

    values = [
        (key, str(value)) for key, value in query.items() if value is not None and value != ""
    ]
    return (
        path
        if not values
        else f"{path}?" + "&".join(f"{quote(key)}={quote(value)}" for key, value in values)
    )


def _unique(values: list[str]) -> list[str]:
    return sorted(set(values))


def _graph_path(
    adjacency: Mapping[str, tuple[tuple[str, str], ...]], source: str, target: str
) -> tuple[list[str], list[str]] | None:
    """Find a stable shortest path through semantic nodes and edge kinds."""

    queue: deque[tuple[str, tuple[str, ...], tuple[str, ...]]] = deque([(source, (source,), ())])
    visited = {source}
    while queue:
        current, nodes, edge_kinds = queue.popleft()
        for next_node, edge_kind in adjacency.get(current, []):
            if next_node in visited:
                continue
            next_nodes = (*nodes, next_node)
            next_edge_kinds = (*edge_kinds, edge_kind)
            if next_node == target:
                return list(next_nodes), list(next_edge_kinds)
            visited.add(next_node)
            queue.append((next_node, next_nodes, next_edge_kinds))
    return None


def _graph_adjacency(projection: GraphProjection) -> dict[str, tuple[tuple[str, str], ...]]:
    adjacency: dict[str, list[tuple[str, str]]] = {}
    for edge in projection.edges:
        adjacency.setdefault(edge.source, []).append((edge.target, edge.edge_type))
    return {
        source: tuple(sorted(values, key=lambda value: (value[0], value[1])))
        for source, values in adjacency.items()
    }


def _relation_view(relation: CourseRelation) -> dict[str, Any]:
    return {
        "source_course": relation.source,
        "target_course": relation.target,
        "relation_type": relation.relation_type,
        "semantic": relation.semantic,
        "requirement_code": relation.requirement_code,
        "condition_node_id": relation.condition_node_id,
        "direct": relation.direct,
    }


def _reachability_view(
    *,
    source: str,
    targets: list[str],
    direct_targets: set[str],
    relations: tuple[CourseRelation, ...],
) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for target in sorted(targets):
        path = shortest_course_path(relations, source, target)
        values.append(
            {
                "course_code": target,
                "distance": max(0, len(path) - 1) if path else None,
                "direct": target in direct_targets,
            }
        )
    return values


def _focus_view(
    projection: GraphProjection,
    courses: Mapping[str, Mapping[str, Any]],
    requirements: Mapping[tuple[str, str], Mapping[str, Any]],
    selected: str,
    descendants_by_course: Mapping[str, tuple[str, ...]],
    node_by_id: Mapping[str, Any],
    adjacency: Mapping[str, tuple[tuple[str, str], ...]],
) -> dict[str, Any]:
    relations = projection.course_relations
    direct_prerequisites = [
        relation
        for relation in relations
        if relation.target == selected and relation.relation_type != "COREQUISITE"
    ]
    direct_corequisites = [
        relation
        for relation in relations
        if relation.target == selected and relation.relation_type == "COREQUISITE"
    ]
    direct_unlocks = [
        relation
        for relation in relations
        if relation.source == selected and relation.relation_type != "COREQUISITE"
    ]
    direct_prerequisite_codes = {relation.source for relation in direct_prerequisites}
    direct_unlock_codes = {relation.target for relation in direct_unlocks}
    descendants = descendants_by_course.get(selected, ())
    ancestors = tuple(
        sorted(
            source
            for source, targets in descendants_by_course.items()
            if selected in targets and source != selected
        )
    )
    paths: list[dict[str, Any]] = []
    source_node_id = f"course:{selected}"
    for target in descendants:
        target_node_id = f"course:{target}"
        path = _graph_path(adjacency, source_node_id, target_node_id)
        if path is None:
            continue
        node_ids, edge_kinds = path
        labels = []
        for node_id in node_ids:
            node = node_by_id[node_id]
            if node.kind == "COURSE":
                labels.append(str(courses.get(node.course_code or "", {}).get("name", node.label)))
            else:
                labels.append(CONDITION_LABELS.get(node.condition_type or node.label, node.label))
        paths.append(
            {
                "target_course": target,
                "node_ids": node_ids,
                "node_labels": labels,
                "edge_kinds": edge_kinds,
                "distance": max(
                    0, len(shortest_course_path(relations, selected, target) or ()) - 1
                ),
                "direct": target in direct_unlock_codes,
                "explanation": f"{selected} abre una ruta hacia {target} mediante "
                f"{' → '.join(labels)}.",
            }
        )

    selected_course = courses.get(selected, {})
    selected_requirements = [
        value for (owner, _), value in requirements.items() if owner == selected
    ]
    return {
        "course_code": selected,
        "course_name": str(selected_course.get("name", selected)),
        "direct_prerequisites": [_relation_view(relation) for relation in direct_prerequisites],
        "direct_corequisites": [_relation_view(relation) for relation in direct_corequisites],
        "direct_unlocks": [_relation_view(relation) for relation in direct_unlocks],
        "ancestors": _reachability_view(
            source=selected,
            targets=list(ancestors),
            direct_targets=direct_prerequisite_codes,
            relations=relations,
        ),
        "descendants": _reachability_view(
            source=selected,
            targets=list(descendants),
            direct_targets=direct_unlock_codes,
            relations=relations,
        ),
        "shortest_unlock_paths": paths,
        "requirement_codes": sorted(str(value.get("code", "")) for value in selected_requirements),
    }


@measure_domain_timing("dependency_graph")
def build_dependency_graph(
    actor: Any | None = None,
    *,
    plan_code: str | None = "2514",
    revision_id: UUID | str | None = None,
    enrollment_id: UUID | str | None = None,
    term_code: str | None = None,
    selected: str | None = None,
) -> dict[str, Any]:
    """Build a provenance-aware graph projection from the curriculum read model."""

    curriculum = build_curriculum_map(
        actor,
        plan_code=plan_code,
        revision_id=revision_id,
        enrollment_id=enrollment_id,
        term_code=term_code,
    )
    courses = {
        str(course["code"]): course
        for course in curriculum["courses"]
        if isinstance(course, Mapping) and course.get("code")
    }
    requirements: dict[tuple[str, str], Any] = {}
    requirement_views: dict[tuple[str, str], Mapping[str, Any]] = {}
    warnings = list(curriculum.get("warnings", []))
    for course_code, course in courses.items():
        for requirement in course.get("requirements", []):
            if not isinstance(requirement, Mapping):
                continue
            requirement_code = str(requirement.get("code", ""))
            if not requirement_code:
                continue
            try:
                requirements[(course_code, requirement_code)] = parse_rule(
                    requirement.get("ast", {})
                )
                requirement_views[(course_code, requirement_code)] = requirement
            except RuleSchemaError, ValueError:
                warnings.append(f"GRAPH_RULE_UNPARSEABLE:{requirement_code}")

    projection = project_rule_graph(requirements)
    descendants_by_course = transitive_course_dependencies(projection.course_relations)
    node_by_id = {node.node_id: node for node in projection.nodes}
    adjacency = _graph_adjacency(projection)
    condition_meta: dict[str, tuple[str, Mapping[str, Any]]] = {}
    for (owner, requirement_code), requirement in requirement_views.items():
        prefix = f"condition:{owner}:{requirement_code}:"
        for node in projection.nodes:
            if node.node_id.startswith(prefix):
                condition_meta[node.node_id] = (owner, requirement)

    nodes: list[dict[str, Any]] = []
    for node in projection.nodes:
        if node.kind == "COURSE":
            course = courses.get(node.course_code or "", {})
            nodes.append(
                {
                    "id": node.node_id,
                    "kind": node.kind,
                    "label": str(course.get("name", node.label)),
                    "course_code": node.course_code,
                    "condition_type": None,
                    "requirement_code": None,
                    "path": list(node.path),
                    "state": str(course.get("personal_status", "NOT_ASSESSED")),
                    "epistemic_status": "VERIFIED" if course.get("source_evidence") else "UNKNOWN",
                    "component_codes": list(course.get("component_codes", [])),
                    "group_codes": list(course.get("group_codes", [])),
                    "credits": course.get("credits"),
                    "evidence_count": len(course.get("source_evidence", [])),
                    "explanation_key": "course.curriculum_reference",
                    "href": str(
                        course.get("href", _href("/curriculum", selected=node.course_code))
                    ),
                }
            )
            continue
        owner, requirement = condition_meta.get(node.node_id, ("", {}))
        condition_type = node.condition_type or node.label
        nodes.append(
            {
                "id": node.node_id,
                "kind": node.kind,
                "label": CONDITION_LABELS.get(condition_type, condition_type),
                "course_code": None,
                "condition_type": condition_type,
                "requirement_code": node.requirement_code,
                "path": list(node.path),
                "state": str(requirement.get("status", "NOT_ASSESSED")),
                "epistemic_status": str(requirement.get("epistemic_status", "UNKNOWN")),
                "component_codes": list(courses.get(owner, {}).get("component_codes", [])),
                "group_codes": list(courses.get(owner, {}).get("group_codes", [])),
                "credits": None,
                "evidence_count": len(requirement.get("evidence", [])),
                "explanation_key": str(requirement.get("explanation_key", "rule.unknown")),
                "href": str(
                    requirement.get(
                        "href",
                        _href("/curriculum", selected=owner, requirement=node.requirement_code),
                    )
                ),
            }
        )

    projected_course_ids = {node.node_id for node in projection.nodes if node.kind == "COURSE"}
    for course_code, course in courses.items():
        if f"course:{course_code}" in projected_course_ids:
            continue
        nodes.append(
            {
                "id": f"course:{course_code}",
                "kind": "COURSE",
                "label": str(course.get("name", course_code)),
                "course_code": course_code,
                "condition_type": None,
                "requirement_code": None,
                "path": [],
                "state": str(course.get("personal_status", "NOT_ASSESSED")),
                "epistemic_status": "VERIFIED" if course.get("source_evidence") else "UNKNOWN",
                "component_codes": list(course.get("component_codes", [])),
                "group_codes": list(course.get("group_codes", [])),
                "credits": course.get("credits"),
                "evidence_count": len(course.get("source_evidence", [])),
                "explanation_key": "course.curriculum_reference",
                "href": str(course.get("href", _href("/curriculum", selected=course_code))),
            }
        )
    nodes.sort(key=lambda node: str(node["id"]))

    edges = [
        {
            "id": edge.edge_id,
            "source": edge.source,
            "target": edge.target,
            "kind": edge.edge_type,
            "semantic": edge.semantic,
            "label": EDGE_LABELS.get(edge.edge_type, edge.edge_type),
            "requirement_code": edge.requirement_code,
            "direct": edge.direct,
        }
        for edge in projection.edges
    ]
    direct_relations = [_relation_view(relation) for relation in projection.course_relations]
    focus = None
    if selected:
        if selected in courses:
            focus = _focus_view(
                projection,
                courses,
                requirement_views,
                selected,
                descendants_by_course,
                node_by_id,
                adjacency,
            )
        else:
            warnings.append("GRAPH_FOCUS_NOT_FOUND")

    cycles = [
        {
            "cycle_id": f"cycle:{index}",
            "course_codes": list(cycle[:-1]),
            "node_ids": [f"course:{code}" for code in cycle],
            "explanation": f"Ciclo de dependencias detectado: {' → '.join(cycle)}.",
            "severity": "ERROR",
        }
        for index, cycle in enumerate(projection.cycles, start=1)
    ]
    if cycles:
        warnings.append("CURRICULUM_DEPENDENCY_CYCLE")

    revision = curriculum["revision"]
    return {
        "revision": revision,
        "nodes": nodes,
        "edges": edges,
        "direct_relations": direct_relations,
        "focus": focus,
        "cycles": cycles,
        "warnings": sorted(set(str(value) for value in warnings)),
        "links": {
            "self": _href("/graph", revision=revision["id"], selected=selected),
            "curriculum": _href("/curriculum", revision=revision["id"], selected=selected),
            "sources": _href("/sources", revision=revision["id"]),
        },
    }
