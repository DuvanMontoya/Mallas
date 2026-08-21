from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from ninja import Router, Schema
from ninja.security import django_auth

from modules.common.api import raise_problem, with_problem_responses
from modules.curriculum.application.graph import build_dependency_graph
from modules.curriculum.application.map import CurriculumMapError, build_curriculum_map


class LayoutView(Schema):
    id: str
    label: str
    description: str
    official: bool


class LayoutPolicyView(Schema):
    schema_version: str
    normative: bool
    policy: str
    available_layouts: list[LayoutView]


class MapRevisionView(Schema):
    id: UUID
    plan_code: str
    plan_title: str
    revision_code: str
    status: str
    effective_from: date
    content_hash: str
    total_required_credits: int
    institution_name: str
    campus_name: str
    program_code: str
    program_name: str
    normative: bool
    source_note: str


class MapComponentView(Schema):
    code: str
    label: str
    required_credits: int
    group_codes: list[str]
    href: str


class MapGroupView(Schema):
    code: str
    label: str
    component: str
    required_credits: int
    kind: str
    href: str


class MapEvidenceView(Schema):
    reference: str
    snapshot_sha256: str
    locator: str
    page: int | None
    section: str
    excerpt: str
    annotation: str
    source_title: str
    source_url: str | None


class MapOfferingView(Schema):
    term_code: str
    status: str
    section_count: int


class MapRequirementView(Schema):
    code: str
    purpose: str
    status: str
    epistemic_status: str
    explanation_key: str
    ast: dict[str, Any]
    dependencies: list[str]
    evidence: list[MapEvidenceView]
    note: str
    source_url: str | None
    href: str


class MapCourseView(Schema):
    id: UUID
    code: str
    name: str
    credits: int | None
    personal_status: str
    status_reason: str
    component_codes: list[str]
    group_codes: list[str]
    group_labels: list[str]
    membership_roles: list[str]
    dependency_depth: int | None
    dependency_depth_label: str
    dependencies: list[str]
    unlocks_directly: list[str]
    requirements: list[MapRequirementView]
    offering_state: str
    offerings: list[MapOfferingView]
    source_evidence: list[MapEvidenceView]
    href: str


class OfferingContextView(Schema):
    term_code: str | None
    term_known: bool
    note: str


class PersonalMapView(Schema):
    available: bool
    enrollment_id: UUID | None
    state: str
    note: str


class MapLinkSetView(Schema):
    self: str
    print: str
    sources: str


class CurriculumMapView(Schema):
    revision: MapRevisionView
    layout_policy: LayoutPolicyView
    components: list[MapComponentView]
    groups: list[MapGroupView]
    courses: list[MapCourseView]
    offering_context: OfferingContextView
    personal: PersonalMapView
    warnings: list[str]
    links: MapLinkSetView


class GraphNodeView(Schema):
    id: str
    kind: str
    label: str
    course_code: str | None
    condition_type: str | None
    requirement_code: str | None
    path: list[int]
    state: str
    epistemic_status: str
    component_codes: list[str]
    group_codes: list[str]
    credits: int | None
    evidence_count: int
    explanation_key: str
    href: str


class GraphEdgeView(Schema):
    id: str
    source: str
    target: str
    kind: str
    semantic: str
    label: str
    requirement_code: str
    direct: bool


class GraphRelationView(Schema):
    source_course: str
    target_course: str
    relation_type: str
    semantic: str
    requirement_code: str
    condition_node_id: str | None
    direct: bool


class GraphReachabilityView(Schema):
    course_code: str
    distance: int | None
    direct: bool


class GraphPathView(Schema):
    target_course: str
    node_ids: list[str]
    node_labels: list[str]
    edge_kinds: list[str]
    distance: int
    direct: bool
    explanation: str


class GraphFocusView(Schema):
    course_code: str
    course_name: str
    direct_prerequisites: list[GraphRelationView]
    direct_corequisites: list[GraphRelationView]
    direct_unlocks: list[GraphRelationView]
    ancestors: list[GraphReachabilityView]
    descendants: list[GraphReachabilityView]
    shortest_unlock_paths: list[GraphPathView]
    requirement_codes: list[str]


class GraphCycleView(Schema):
    cycle_id: str
    course_codes: list[str]
    node_ids: list[str]
    explanation: str
    severity: str


class GraphLinkSetView(Schema):
    self: str
    curriculum: str
    sources: str


class DependencyGraphView(Schema):
    revision: MapRevisionView
    nodes: list[GraphNodeView]
    edges: list[GraphEdgeView]
    direct_relations: list[GraphRelationView]
    focus: GraphFocusView | None
    cycles: list[GraphCycleView]
    warnings: list[str]
    links: GraphLinkSetView


router = Router(tags=["Curriculum map"])


@router.get(
    "/curriculum-map",
    auth=django_auth,
    response=with_problem_responses(CurriculumMapView),
)
def curriculum_map(
    request: HttpRequest,
    response: HttpResponse,
    plan_code: str = "2514",
    revision_id: UUID | None = None,
    enrollment_id: UUID | None = None,
    term_code: str | None = None,
) -> dict[str, Any]:
    try:
        result = build_curriculum_map(
            getattr(request, "auth", None) or getattr(request, "user", None),
            plan_code=plan_code or None,
            revision_id=revision_id,
            enrollment_id=enrollment_id,
            term_code=term_code,
        )
    except CurriculumMapError as error:
        status = 403 if error.code == "map_forbidden" else 404
        raise_problem(
            status=status,
            code=error.code.upper(),
            title="Curriculum map unavailable",
            detail=str(error),
        )
    response["ETag"] = f'"{result["revision"]["content_hash"]}"'
    return result


@router.get(
    "/dependency-graph",
    auth=django_auth,
    response=with_problem_responses(DependencyGraphView),
)
def dependency_graph(
    request: HttpRequest,
    response: HttpResponse,
    plan_code: str = "2514",
    revision_id: UUID | None = None,
    enrollment_id: UUID | None = None,
    term_code: str | None = None,
    selected: str | None = None,
) -> dict[str, Any]:
    try:
        result = build_dependency_graph(
            getattr(request, "auth", None) or getattr(request, "user", None),
            plan_code=plan_code or None,
            revision_id=revision_id,
            enrollment_id=enrollment_id,
            term_code=term_code,
            selected=selected,
        )
    except CurriculumMapError as error:
        status = 403 if error.code == "map_forbidden" else 404
        raise_problem(
            status=status,
            code=error.code.upper(),
            title="Dependency graph unavailable",
            detail=str(error),
        )
    fingerprint = hashlib.sha256(
        json.dumps(result, default=str, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    response["ETag"] = f'"{fingerprint}"'
    return result
