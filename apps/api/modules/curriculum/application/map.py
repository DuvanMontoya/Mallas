from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db.models import Count

from domain.enums import OfferingStatus, RevisionStatus
from domain.rules import direct_course_dependencies, parse_rule
from domain.rules.errors import RuleSchemaError
from modules.audit.application.overview import AcademicOverviewError, build_academic_overview
from modules.curriculum.models import Course, CourseVersion, CurriculumRevision
from modules.governance.models import Evidence, SourceSnapshot
from modules.identity.application.authorization import can_view_audit_for_enrollment
from modules.offerings.models import AcademicTerm, CourseOffering
from modules.rules.models import Requirement
from modules.student_records.application.enrollment import preferred_enrollment_for_user
from modules.student_records.models import ProgramEnrollment


class CurriculumMapError(RuntimeError):
    """A safe, explainable failure while projecting a curriculum map."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: object) -> list[Any]:
    return (
        list(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else []
    )


def _project_root() -> Path:
    configured = getattr(settings, "PROJECT_ROOT", None)
    return Path(configured) if configured else Path(__file__).resolve().parents[5]


def _href(path: str, **query: object) -> str:
    from urllib.parse import quote

    values = [
        (key, str(value)) for key, value in query.items() if value is not None and value != ""
    ]
    if not values:
        return path
    return f"{path}?" + "&".join(f"{quote(key)}={quote(value)}" for key, value in values)


def _source_component_code(group: Any) -> str:
    metadata = _mapping(group.metadata)
    return str(metadata.get("source_component_id") or group.code.removeprefix("COMPONENT::"))


def _load_layout_policy(plan_code: str) -> dict[str, Any]:
    path = _project_root() / "data" / "layouts" / f"plan_{plan_code}_layout_policy.json"
    if not path.is_file():
        return {
            "schema_version": "1.0.0",
            "plan": plan_code,
            "normative": False,
            "policy": "No existe una política de layout archivada para este plan.",
            "available_layouts": [],
        }
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return {
            "schema_version": "1.0.0",
            "plan": plan_code,
            "normative": False,
            "policy": "La política de layout no pudo leerse; no se afirma una posición oficial.",
            "available_layouts": [],
        }
    return dict(value) if isinstance(value, dict) else {}


def _layout_views(policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    labels = {
        "dependency-depth": "Nivel de dependencias",
        "suggested-path": "Ruta sugerida",
        "user-scenario": "Escenario personal",
        "component-lanes": "Componentes y agrupaciones",
    }
    views: list[dict[str, Any]] = []
    for item in _list(policy.get("available_layouts")):
        if not isinstance(item, Mapping):
            continue
        layout_id = str(item.get("id", ""))
        if not layout_id:
            continue
        views.append(
            {
                "id": layout_id,
                "label": labels.get(layout_id, layout_id.replace("-", " ").title()),
                "description": str(item.get("description", "")),
                "official": False,
            }
        )
    return views


def _evidence_view(evidence: Evidence) -> dict[str, Any]:
    snapshot = evidence.snapshot
    document = snapshot.document
    locator = (
        evidence.line_locator
        or evidence.section
        or (f"page:{evidence.page}" if evidence.page else "source")
    )
    return {
        "reference": f"{snapshot.sha256}#{locator}",
        "snapshot_sha256": snapshot.sha256,
        "locator": locator,
        "page": evidence.page,
        "section": evidence.section,
        "excerpt": evidence.excerpt,
        "annotation": evidence.annotation,
        "source_title": document.title,
        "source_url": snapshot.source_url or document.canonical_url or None,
    }


def _requirement_evidence(requirement: Requirement) -> list[dict[str, Any]]:
    return [_evidence_view(item) for item in requirement.evidence.all()]


def _membership_evidence(
    *,
    snapshot: SourceSnapshot | None,
    course_code: str,
    group: Any,
    source_page: object,
) -> list[dict[str, Any]]:
    if snapshot is None:
        return []
    page = (
        source_page if isinstance(source_page, int) and not isinstance(source_page, bool) else None
    )
    document = snapshot.document
    locator = f"course:{course_code}/group:{group.code}"
    return [
        {
            "reference": f"{snapshot.sha256}#{locator}",
            "snapshot_sha256": snapshot.sha256,
            "locator": locator,
            "page": page,
            "section": "",
            "excerpt": "",
            "annotation": "Ubicación declarada en el baseline archivado; la posición visual no es normativa.",
            "source_title": document.title,
            "source_url": snapshot.source_url or document.canonical_url or None,
        }
    ]


def _revision(
    *,
    plan_code: str | None,
    revision_id: UUID | str | None,
) -> CurriculumRevision:
    query = CurriculumRevision.objects.select_related("plan__program__faculty__campus__institution")
    if revision_id is not None:
        try:
            return query.get(pk=revision_id)
        except CurriculumRevision.DoesNotExist as exc:
            raise CurriculumMapError(
                "La revisión curricular no existe.", code="revision_not_found"
            ) from exc

    if plan_code:
        query = query.filter(plan__code=plan_code)
    revision = (
        query.filter(status=RevisionStatus.PUBLISHED.value)
        .order_by("-effective_from", "-created_at", "-revision_code")
        .first()
    )
    if revision is not None:
        return revision
    revision = query.order_by("-effective_from", "-created_at", "-revision_code").first()
    if revision is None:
        raise CurriculumMapError(
            "No hay una revisión curricular disponible.", code="revision_not_found"
        )
    return revision


def _student_enrollment(
    actor: Any | None,
    *,
    enrollment_id: UUID | str | None,
) -> ProgramEnrollment | None:
    if enrollment_id is not None:
        try:
            enrollment = ProgramEnrollment.objects.select_related(
                "student__user", "program", "plan", "revision_basis"
            ).get(pk=enrollment_id)
        except ProgramEnrollment.DoesNotExist as exc:
            raise CurriculumMapError(
                "La matrícula no existe.", code="enrollment_not_found"
            ) from exc
        if not can_view_audit_for_enrollment(actor, enrollment):
            raise CurriculumMapError(
                "No puedes ver el estado personal de esta matrícula.", code="map_forbidden"
            )
        return enrollment

    if (
        actor is None
        or not getattr(actor, "pk", None)
        or not getattr(actor, "is_authenticated", False)
    ):
        return None
    return preferred_enrollment_for_user(actor.pk)


def _depths(graph: Mapping[str, set[str]]) -> tuple[dict[str, int | None], set[str]]:
    depths: dict[str, int | None] = {}
    visiting: list[str] = []
    cycles: set[str] = set()

    def visit(code: str) -> int | None:
        if code in depths:
            return depths[code]
        if code in visiting:
            start = visiting.index(code)
            cycles.update(visiting[start:])
            return None
        visiting.append(code)
        dependencies = [item for item in sorted(graph.get(code, set())) if item in graph]
        dependency_depths = [visit(item) for item in dependencies]
        visiting.pop()
        if any(value is None for value in dependency_depths):
            result: int | None = None
        else:
            known_depths = [value for value in dependency_depths if value is not None]
            result = 0 if not known_depths else max(known_depths) + 1
        depths[code] = result
        return result

    for code in sorted(graph):
        visit(code)
    return depths, cycles


def _offering_context(
    *,
    versions: Mapping[str, CourseVersion],
    institution_id: UUID,
    term_code: str | None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any], list[str]]:
    offerings_query = (
        CourseOffering.objects.filter(
            course_version_id__in=[version.pk for version in versions.values()]
        )
        .select_related("term")
        .annotate(section_count=Count("sections"))
    )
    if term_code:
        offerings_query = offerings_query.filter(term__code=term_code)
    offerings = list(offerings_query.order_by("course_version__course__code", "term__code", "id"))
    by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for offering in offerings:
        code = offering.course_version.course.code
        by_code[code].append(
            {
                "term_code": offering.term.code,
                "status": offering.status,
                "section_count": int(getattr(offering, "section_count", 0)),
            }
        )

    warnings: list[str] = []
    if not term_code:
        context = {
            "term_code": None,
            "term_known": False,
            "note": "Selecciona un período académico para consultar oferta; no se infiere la oferta actual.",
        }
        warnings.append("OFFERING_PERIOD_NOT_SELECTED")
    else:
        term_known = AcademicTerm.objects.filter(
            institution_id=institution_id, code=term_code
        ).exists()
        context = {
            "term_code": term_code,
            "term_known": term_known,
            "note": (
                "El período no está registrado para esta institución."
                if not term_known
                else "La oferta se deriva sólo de registros del período seleccionado."
            ),
        }
        if not term_known:
            warnings.append("OFFERING_PERIOD_UNKNOWN")
    return by_code, context, warnings


def build_curriculum_map(
    actor: Any | None = None,
    *,
    plan_code: str | None = "2514",
    revision_id: UUID | str | None = None,
    enrollment_id: UUID | str | None = None,
    term_code: str | None = None,
) -> dict[str, Any]:
    """Project a revision into a presentation read model without inventing semesters.

    The layout policy and all personal statuses are explicit data. This service
    never turns a visual column into a normative academic term.
    """

    revision = _revision(plan_code=plan_code, revision_id=revision_id)
    enrollment = _student_enrollment(actor, enrollment_id=enrollment_id)
    if (
        enrollment is not None
        and enrollment.status != "NEEDS_REVIEW"
        and enrollment.revision_basis_id is not None
        and enrollment.revision_basis.plan_id != revision.plan_id
    ):
        raise CurriculumMapError(
            "La matrícula y la revisión pertenecen a planes distintos.",
            code="enrollment_plan_mismatch",
        )

    personal: dict[str, Any] | None = None
    personal_options: dict[str, Mapping[str, Any]] = {}
    personal_reasons: dict[str, Mapping[str, Any]] = {}
    if enrollment is not None:
        resolved_enrollment_id = enrollment.pk
        try:
            overview = build_academic_overview(actor, enrollment_id=resolved_enrollment_id)
        except AcademicOverviewError as exc:
            if exc.code != "enrollment_needs_review":
                raise CurriculumMapError(str(exc), code=exc.code) from exc
            enrollment = None
            overview = None
        if overview is None:
            personal = {
                "available": False,
                "enrollment_id": None,
                "state": "NEEDS_REVIEW",
                "note": "La revisión curricular de tu matrícula debe validarse antes de mostrar elegibilidad.",
            }
        else:
            personal = {
                "available": True,
                "enrollment_id": resolved_enrollment_id,
                "state": overview["state"],
                "note": "Los estados de las tarjetas provienen de la auditoría del backend.",
            }
            personal_options = {
                str(item.get("code")): item
                for item in _list(overview.get("course_options"))
                if isinstance(item, Mapping)
            }
            for item in personal_options.values():
                for reason in _list(item.get("reasons")):
                    if isinstance(reason, Mapping):
                        personal_reasons[str(reason.get("code", ""))] = reason
    else:
        personal = {
            "available": False,
            "enrollment_id": None,
            "state": "NOT_ASSESSED",
            "note": "Inicia sesión y vincula una matrícula para ver estados personales.",
        }

    groups = list(
        revision.requirement_groups.select_related("parent").order_by("sort_order", "code")
    )
    group_views = [
        {
            "code": group.code,
            "label": group.label,
            "component": _source_component_code(group.parent) if group.parent else "",
            "required_credits": group.required_credits,
            "kind": group.kind,
            "href": _href("/curriculum", group=group.code),
        }
        for group in groups
        if group.kind != "COMPONENT"
    ]
    component_views = [
        {
            "code": _source_component_code(group),
            "label": group.label,
            "required_credits": group.required_credits,
            "group_codes": [child.code for child in groups if child.parent_id == group.pk],
            "href": _href("/curriculum", component=_source_component_code(group)),
        }
        for group in groups
        if group.kind == "COMPONENT"
    ]

    memberships = list(
        revision.memberships.select_related(
            "course_version__course", "group", "group__parent"
        ).order_by("course_version__course__code", "group__sort_order", "group__code")
    )
    requirements = list(
        revision.requirements.prefetch_related("evidence__snapshot__document").order_by("code")
    )
    owner_ids = {
        requirement.owner_id for requirement in requirements if requirement.owner_type == "COURSE"
    }
    owner_courses = {
        str(course.pk): course.code
        for course in Course.objects.filter(
            pk__in=owner_ids, institution_id=revision.plan.program.faculty.campus.institution_id
        )
    }
    memberships_by_code: dict[str, list[Any]] = defaultdict(list)
    course_codes: set[str] = set()
    for membership in memberships:
        code = membership.course_version.course.code
        memberships_by_code[code].append(membership)
        course_codes.add(code)

    requirements_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    dependency_graph: dict[str, set[str]] = defaultdict(set)
    for requirement in requirements:
        if requirement.owner_type != "COURSE":
            continue
        owner_code = owner_courses.get(str(requirement.owner_id))
        if owner_code is None:
            continue
        try:
            rule = parse_rule(requirement.ast)
            dependencies = sorted(direct_course_dependencies(rule))
        except RuleSchemaError, ValueError:
            dependencies = []
        course_codes.add(owner_code)
        course_codes.update(dependencies)
        dependency_graph[owner_code].update(dependencies)
        requirements_by_code[owner_code].append(
            {
                "model": requirement,
                "dependencies": dependencies,
            }
        )

    versions: dict[str, CourseVersion] = {}
    for version in (
        CourseVersion.objects.filter(
            course__institution_id=revision.plan.program.faculty.campus.institution_id,
            course__code__in=course_codes,
        )
        .select_related("course")
        .order_by("course__code", "-valid_from", "-created_at")
    ):
        versions.setdefault(version.course.code, version)
    dependency_graph = {
        code: {dependency for dependency in dependencies if dependency in versions}
        for code, dependencies in dependency_graph.items()
    }
    for code in versions:
        dependency_graph.setdefault(code, set())
    unlocks_by_code: dict[str, set[str]] = defaultdict(set)
    for dependent, dependency_set in dependency_graph.items():
        for dependency in dependency_set:
            unlocks_by_code[dependency].add(dependent)
    depths, cycles = _depths(dependency_graph)

    source_snapshot = (
        SourceSnapshot.objects.filter(sha256=revision.source_set_hash)
        .select_related("document")
        .order_by("-captured_at")
        .first()
        if revision.source_set_hash
        else None
    )
    offering_by_code, offering_context, offering_warnings = _offering_context(
        versions=versions,
        institution_id=revision.plan.program.faculty.campus.institution_id,
        term_code=term_code,
    )

    requirement_views_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for owner_code, items in requirements_by_code.items():
        for item in items:
            requirement = item["model"]
            personal_reason = personal_reasons.get(requirement.code)
            requirement_views_by_code[owner_code].append(
                {
                    "code": requirement.code,
                    "purpose": requirement.purpose,
                    "status": str(personal_reason.get("status", "NOT_ASSESSED"))
                    if personal_reason
                    else "NOT_ASSESSED",
                    "epistemic_status": requirement.epistemic_status,
                    "explanation_key": str(
                        personal_reason.get("explanation_key", requirement.explanation_key)
                        if personal_reason
                        else requirement.explanation_key
                    ),
                    "ast": requirement.ast,
                    "dependencies": item["dependencies"],
                    "evidence": _requirement_evidence(requirement),
                    "note": str(_mapping(requirement.metadata).get("note", "")),
                    "source_url": str(_mapping(requirement.metadata).get("source_url", "")) or None,
                    "href": _href("/curriculum", selected=owner_code, requirement=requirement.code),
                }
            )

    courses: list[dict[str, Any]] = []
    for code, version in sorted(versions.items()):
        course_memberships = memberships_by_code.get(code, [])
        group_codes = [membership.group.code for membership in course_memberships]
        component_codes = sorted(
            {
                _source_component_code(membership.group.parent)
                for membership in course_memberships
                if membership.group.parent is not None
            }
        )
        option = personal_options.get(code)
        personal_status = str(option.get("eligibility")) if option else "NOT_ASSESSED"
        if not course_memberships and personal_status == "NOT_ASSESSED":
            personal_status = "NOT_ASSESSED"
        offering_rows = offering_by_code.get(code, [])
        if not term_code or not offering_context["term_known"]:
            offering_state = "UNKNOWN"
        elif not offering_rows:
            offering_state = "NOT_REPORTED"
        elif any(
            row["status"]
            in {
                OfferingStatus.PLANNED.value,
                OfferingStatus.PUBLISHED.value,
                OfferingStatus.COMPLETED.value,
            }
            for row in offering_rows
        ):
            offering_state = "AVAILABLE"
        else:
            offering_state = "NOT_AVAILABLE"
        membership_evidence = [
            evidence
            for membership in course_memberships
            for evidence in _membership_evidence(
                snapshot=source_snapshot,
                course_code=code,
                group=membership.group,
                source_page=_mapping(membership.metadata).get("source_page"),
            )
        ]
        courses.append(
            {
                "id": version.pk,
                "code": code,
                "name": version.name,
                "credits": version.credits,
                "personal_status": personal_status,
                "status_reason": str(
                    _list(option.get("reasons"))[0].get("explanation_key", "")
                    if option
                    and _list(option.get("reasons"))
                    and isinstance(_list(option.get("reasons"))[0], Mapping)
                    else ""
                ),
                "component_codes": component_codes,
                "group_codes": group_codes,
                "group_labels": [membership.group.label for membership in course_memberships],
                "membership_roles": [membership.role for membership in course_memberships],
                "dependency_depth": depths.get(code),
                "dependency_depth_label": (
                    f"Nivel de dependencias {depths[code]}"
                    if depths.get(code) is not None
                    else "Nivel de dependencias no determinable"
                ),
                "dependencies": sorted(dependency_graph.get(code, set())),
                "unlocks_directly": sorted(unlocks_by_code.get(code, set())),
                "requirements": requirement_views_by_code.get(code, []),
                "offering_state": offering_state,
                "offerings": offering_rows,
                "source_evidence": membership_evidence,
                "href": _href("/curriculum", selected=code, revision=revision.pk),
            }
        )

    policy = _load_layout_policy(revision.plan.code)
    layout_options = _layout_views(policy)
    warnings = list(offering_warnings)
    if revision.status != RevisionStatus.PUBLISHED.value:
        warnings.append("CURRICULUM_REVISION_NOT_PUBLISHED")
    if not bool(policy.get("normative", False)):
        warnings.append("LAYOUTS_ARE_NOT_NORMATIVE")
    if source_snapshot is None:
        warnings.append("CURRICULUM_SOURCE_SNAPSHOT_NOT_FOUND")
    if cycles:
        warnings.append("CURRICULUM_DEPENDENCY_CYCLE")

    institution = revision.plan.program.faculty.campus.institution
    program = revision.plan.program
    return {
        "revision": {
            "id": revision.pk,
            "plan_code": revision.plan.code,
            "plan_title": revision.plan.title,
            "revision_code": revision.revision_code,
            "status": revision.status,
            "effective_from": revision.effective_from,
            "content_hash": revision.content_hash or str(revision.pk),
            "total_required_credits": revision.total_required_credits,
            "institution_name": institution.display_name,
            "campus_name": revision.plan.program.faculty.campus.name,
            "program_code": program.code,
            "program_name": program.name,
            "normative": revision.status == RevisionStatus.PUBLISHED.value
            and bool(policy.get("normative", False)),
            "source_note": str(
                _mapping(revision.metadata)
                .get("source_payload", {})
                .get("revision", {})
                .get("note", "")
                if isinstance(_mapping(revision.metadata).get("source_payload", {}), Mapping)
                else ""
            ),
        },
        "layout_policy": {
            "schema_version": str(policy.get("schema_version", "1.0.0")),
            "normative": bool(policy.get("normative", False)),
            "policy": str(policy.get("policy", "")),
            "available_layouts": layout_options,
        },
        "components": component_views,
        "groups": group_views,
        "courses": courses,
        "offering_context": offering_context,
        "personal": personal,
        "warnings": sorted(set(warnings)),
        "links": {
            "self": _href("/curriculum", revision=revision.pk),
            "print": _href("/curriculum/print", revision=revision.pk),
            "sources": _href("/sources", revision=revision.pk),
        },
    }
