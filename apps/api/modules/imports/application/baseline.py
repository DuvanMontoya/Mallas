from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from domain.revision import canonical_content_hash

JSONValue = Any

REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "identity",
    "revision",
    "components",
    "groups",
    "courses",
    "memberships",
    "enrollment_requirements",
    "graduation_requirements",
    "source_documents",
    "known_ambiguities",
}
ALLOWED_EPISTEMIC_STATUSES = {
    "VERIFIED",
    "DERIVED",
    "INFERRED_PENDING_REVIEW",
    "UNKNOWN",
    "DISPUTED",
    "SUPERSEDED",
    "VERIFIED_AT_INSTITUTION_LEVEL",
}
ALLOWED_AST_TYPES = {
    "ALL",
    "ANY",
    "COURSE_PASSED",
    "CREDITS_IN_GROUP",
    "CREDITS_IN_COMPONENT",
    "TOTAL_CREDITS",
    "PERCENTAGE_OF_PLAN",
    "GROUP_COMPLETED",
    "EXTERNAL_REQUIREMENT",
    "UNKNOWN",
}
ENTITY_KEYS = (
    ("components", "id"),
    ("groups", "id"),
    ("courses", "code"),
    ("memberships", "course_code|group"),
    ("enrollment_requirements", "owner_course_code|purpose"),
    ("graduation_requirements", "id"),
    ("known_ambiguities", "course_code|issue"),
)


@dataclass(slots=True)
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unknowns: list[dict[str, Any]] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    totals: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "unknowns": list(self.unknowns),
            "counts": dict(sorted(self.counts.items())),
            "totals": dict(sorted(self.totals.items())),
        }


@dataclass(frozen=True, slots=True)
class BaselineDocument:
    path: Path
    payload: dict[str, Any]
    schema_version: str
    fingerprint: str


class BaselineValidationError(ValueError):
    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        message = "Curriculum baseline validation failed: " + "; ".join(report.errors)
        super().__init__(message)


def _as_mapping(value: object, context: str, report: ValidationReport) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        report.errors.append(f"{context} must be an object")
        return {}
    return value


def _as_sequence(value: object, context: str, report: ValidationReport) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        report.errors.append(f"{context} must be an array")
        return []
    return value


def _string(value: object, context: str, report: ValidationReport) -> str:
    if not isinstance(value, str) or not value.strip():
        report.errors.append(f"{context} must be a non-empty string")
        return ""
    return value.strip()


def _integer(value: object, context: str, report: ValidationReport) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        report.errors.append(f"{context} must be a non-negative integer")
        return None
    return value


def _sort_records(records: object, key_fields: str) -> list[dict[str, Any]]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes, bytearray)):
        return []
    rows = [dict(item) for item in records if isinstance(item, Mapping)]
    fields = key_fields.split("|")
    return sorted(
        rows,
        key=lambda row: tuple(str(row.get(field, "")) for field in fields),
    )


def canonical_baseline_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a stable representation that ignores source array ordering."""

    normalized = dict(payload)
    for entity, key_fields in ENTITY_KEYS:
        if entity in normalized:
            normalized[entity] = _sort_records(normalized[entity], key_fields)
    return normalized


def baseline_fingerprint(payload: Mapping[str, Any]) -> str:
    return canonical_content_hash(canonical_baseline_payload(payload))


def load_baseline(path: Path) -> BaselineDocument:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read curriculum baseline {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Curriculum baseline root must be a JSON object")
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        raise ValueError("Curriculum baseline requires a non-empty schema_version")
    return BaselineDocument(
        path=path,
        payload=payload,
        schema_version=schema_version,
        fingerprint=baseline_fingerprint(payload),
    )


def _validate_ast(
    node: object,
    *,
    context: str,
    course_codes: set[str],
    group_ids: set[str],
    component_ids: set[str],
    report: ValidationReport,
) -> list[str]:
    """Validate AST shape and return course references for cycle analysis."""

    if not isinstance(node, Mapping):
        report.errors.append(f"{context} must be an object")
        return []
    node_type = node.get("type")
    if node_type not in ALLOWED_AST_TYPES:
        report.errors.append(f"{context}.type has unsupported value {node_type!r}")
        return []
    if node_type == "COURSE_PASSED":
        code = node.get("course_code")
        if not isinstance(code, str) or not code:
            report.errors.append(f"{context}.course_code is required")
            return []
        if code not in course_codes:
            report.errors.append(f"{context} references unknown course {code}")
        return [code]
    if node_type in {"ALL", "ANY"}:
        children = _as_sequence(node.get("children"), f"{context}.children", report)
        if not children:
            report.errors.append(f"{context}.children cannot be empty")
        references: list[str] = []
        for index, child in enumerate(children):
            references.extend(
                _validate_ast(
                    child,
                    context=f"{context}.children[{index}]",
                    course_codes=course_codes,
                    group_ids=group_ids,
                    component_ids=component_ids,
                    report=report,
                )
            )
        return references
    if node_type == "CREDITS_IN_GROUP":
        group = node.get("group")
        if not isinstance(group, str) or group not in group_ids:
            report.errors.append(f"{context}.group references unknown group {group!r}")
    elif node_type == "CREDITS_IN_COMPONENT":
        component = node.get("component")
        if not isinstance(component, str) or component not in component_ids:
            report.errors.append(f"{context}.component references unknown component {component!r}")
    elif node_type == "GROUP_COMPLETED":
        group = node.get("group")
        if not isinstance(group, str) or group not in group_ids:
            report.errors.append(f"{context}.group references unknown group {group!r}")
    elif node_type == "PERCENTAGE_OF_PLAN":
        numerator = node.get("numerator")
        denominator = node.get("denominator")
        if (
            isinstance(numerator, bool)
            or not isinstance(numerator, int)
            or numerator < 0
            or isinstance(denominator, bool)
            or not isinstance(denominator, int)
            or denominator <= 0
        ):
            report.errors.append(f"{context} has an invalid percentage")
    elif node_type == "UNKNOWN":
        reason = node.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            report.errors.append(f"{context}.reason is required for UNKNOWN")
    elif node_type == "EXTERNAL_REQUIREMENT":
        if not isinstance(node.get("key"), str) or not str(node.get("key")).strip():
            report.errors.append(f"{context}.key is required")
    else:
        operator = node.get("operator")
        value = node.get("value")
        if operator not in {">=", ">", "=", "<=", "<"}:
            report.errors.append(f"{context}.operator is invalid")
        _integer(value, f"{context}.value", report)
    return []


def _find_cycles(graph: Mapping[str, set[str]]) -> list[list[str]]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in visiting:
            start = stack.index(node)
            cycle = tuple(stack[start:] + [node])
            cycles.add(cycle)
            return
        if node in visited:
            return
        visiting.add(node)
        for dependency in sorted(graph.get(node, set())):
            visit(dependency, stack + [node])
        visiting.remove(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node, [])
    return [list(cycle) for cycle in sorted(cycles)]


def validate_baseline(payload: Mapping[str, Any]) -> ValidationReport:
    report = ValidationReport()
    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - set(payload))
    if missing:
        report.errors.append(f"missing top-level keys: {', '.join(missing)}")

    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        report.errors.append("schema_version must be a non-empty string")

    identity = _as_mapping(payload.get("identity"), "identity", report)
    revision = _as_mapping(payload.get("revision"), "revision", report)
    components = _as_sequence(payload.get("components"), "components", report)
    groups = _as_sequence(payload.get("groups"), "groups", report)
    courses = _as_sequence(payload.get("courses"), "courses", report)
    memberships = _as_sequence(payload.get("memberships"), "memberships", report)
    enrollment = _as_sequence(
        payload.get("enrollment_requirements"), "enrollment_requirements", report
    )
    graduation = _as_sequence(
        payload.get("graduation_requirements"), "graduation_requirements", report
    )
    ambiguities = _as_sequence(payload.get("known_ambiguities"), "known_ambiguities", report)

    course_codes: set[str] = set()
    for index, row in enumerate(courses):
        item = _as_mapping(row, f"courses[{index}]", report)
        code = _string(item.get("code"), f"courses[{index}].code", report)
        if code in course_codes:
            report.errors.append(f"duplicate course code {code}")
        course_codes.add(code)
        credits = item.get("credits")
        if credits is not None:
            _integer(credits, f"courses[{index}].credits", report)

    component_ids: set[str] = set()
    component_total = 0
    for index, row in enumerate(components):
        item = _as_mapping(row, f"components[{index}]", report)
        component_id = _string(item.get("id"), f"components[{index}].id", report)
        if component_id in component_ids:
            report.errors.append(f"duplicate component id {component_id}")
        component_ids.add(component_id)
        required = _integer(
            item.get("required_credits"), f"components[{index}].required_credits", report
        )
        mandatory = _integer(
            item.get("mandatory_credits"), f"components[{index}].mandatory_credits", report
        )
        elective = _integer(
            item.get("elective_credits"), f"components[{index}].elective_credits", report
        )
        if required is not None:
            component_total += required
        if (
            required is not None
            and mandatory is not None
            and elective is not None
            and mandatory + elective != required
        ):
            report.errors.append(
                f"component {component_id} mandatory+elective does not equal required"
            )

    group_ids: set[str] = set()
    group_totals: dict[str, int] = {}
    for index, row in enumerate(groups):
        item = _as_mapping(row, f"groups[{index}]", report)
        group_id = _string(item.get("id"), f"groups[{index}].id", report)
        if group_id in group_ids:
            report.errors.append(f"duplicate group id {group_id}")
        group_ids.add(group_id)
        component = item.get("component")
        if component not in component_ids:
            report.errors.append(f"group {group_id} references unknown component {component!r}")
        required = _integer(
            item.get("required_credits"), f"groups[{index}].required_credits", report
        )
        if required is not None:
            group_totals[group_id] = required

    for component in components:
        item = component if isinstance(component, Mapping) else {}
        source_component_id = item.get("id")
        expected = item.get("required_credits")
        actual = sum(
            item.get("required_credits", 0)
            for item in groups
            if isinstance(item, Mapping) and item.get("component") == source_component_id
        )
        if isinstance(expected, int) and actual != expected:
            report.errors.append(
                f"component {source_component_id} group total {actual} does not equal required {expected}"
            )

    membership_keys: set[tuple[str, str]] = set()
    for index, row in enumerate(memberships):
        item = _as_mapping(row, f"memberships[{index}]", report)
        course_code = _string(item.get("course_code"), f"memberships[{index}].course_code", report)
        group_id = _string(item.get("group"), f"memberships[{index}].group", report)
        key = (course_code, group_id)
        if key in membership_keys:
            report.errors.append(f"duplicate membership {course_code}/{group_id}")
        membership_keys.add(key)
        if course_code not in course_codes:
            report.errors.append(f"membership references unknown course {course_code}")
        if group_id not in group_ids:
            report.errors.append(f"membership references unknown group {group_id}")
        if item.get("status") not in ALLOWED_EPISTEMIC_STATUSES:
            report.errors.append(f"membership {course_code}/{group_id} has invalid status")

    graph: dict[str, set[str]] = {code: set() for code in course_codes}
    requirement_keys: set[tuple[str, str]] = set()
    for index, row in enumerate(enrollment):
        item = _as_mapping(row, f"enrollment_requirements[{index}]", report)
        owner = _string(
            item.get("owner_course_code"),
            f"enrollment_requirements[{index}].owner_course_code",
            report,
        )
        purpose = _string(item.get("purpose"), f"enrollment_requirements[{index}].purpose", report)
        key = (owner, purpose)
        if key in requirement_keys:
            report.errors.append(f"duplicate requirement {owner}/{purpose}")
        requirement_keys.add(key)
        if owner not in course_codes:
            report.errors.append(f"requirement references unknown owner course {owner}")
        status = item.get("epistemic_status")
        if status not in ALLOWED_EPISTEMIC_STATUSES:
            report.errors.append(f"requirement {owner}/{purpose} has invalid epistemic_status")
        evidence = item.get("evidence")
        if status == "VERIFIED" and not isinstance(evidence, Mapping):
            report.errors.append(f"verified requirement {owner}/{purpose} has no evidence")
        refs = _validate_ast(
            item.get("ast"),
            context=f"enrollment_requirements[{index}].ast",
            course_codes=course_codes,
            group_ids=group_ids,
            component_ids=component_ids,
            report=report,
        )
        if purpose in {"PREREQUISITE", "COREQUISITE"} and status != "UNKNOWN":
            graph.setdefault(owner, set()).update(refs)
        if status in {"UNKNOWN", "INFERRED_PENDING_REVIEW", "DISPUTED"}:
            report.unknowns.append(
                {
                    "owner_course_code": owner,
                    "purpose": purpose,
                    "status": status,
                    "reason": item.get("note") or item.get("raw_source_text") or "review required",
                }
            )

    for index, row in enumerate(graduation):
        item = _as_mapping(row, f"graduation_requirements[{index}]", report)
        status = item.get("epistemic_status")
        if status == "VERIFIED" and not item.get("evidence") and not item.get("source_url"):
            report.errors.append(f"graduation requirement {item.get('id')} has no evidence")
        _validate_ast(
            item.get("ast"),
            context=f"graduation_requirements[{index}].ast",
            course_codes=course_codes,
            group_ids=group_ids,
            component_ids=component_ids,
            report=report,
        )

    for index, row in enumerate(ambiguities):
        item = _as_mapping(row, f"known_ambiguities[{index}]", report)
        status = item.get("status")
        if status not in {"UNKNOWN", "INFERRED_PENDING_REVIEW", "DISPUTED"}:
            report.errors.append(f"known ambiguity {index} must remain reviewable")
        report.unknowns.append(dict(item))

    cycles = _find_cycles(graph)
    if cycles:
        report.errors.extend("prerequisite cycle: " + " -> ".join(cycle) for cycle in cycles)

    declared_total = identity.get("total_required_credits")
    if not isinstance(declared_total, int):
        report.errors.append("identity.total_required_credits must be an integer")
    elif declared_total != component_total:
        report.errors.append(
            f"identity total {declared_total} does not equal component total {component_total}"
        )
    revision_code = revision.get("revision_code")
    if not isinstance(revision_code, str) or not revision_code:
        report.errors.append("revision.revision_code must be a non-empty string")

    report.counts = {
        "components": len(components),
        "groups": len(groups),
        "courses": len(courses),
        "memberships": len(memberships),
        "enrollment_requirements": len(enrollment),
        "graduation_requirements": len(graduation),
        "known_ambiguities": len(ambiguities),
    }
    report.totals = {
        "required_credits": declared_total if isinstance(declared_total, int) else 0,
        "foundation": next(
            (
                item.get("required_credits", 0)
                for item in components
                if isinstance(item, Mapping) and item.get("id") == "FOUNDATION"
            ),
            0,
        ),
        "disciplinary": next(
            (
                item.get("required_credits", 0)
                for item in components
                if isinstance(item, Mapping) and item.get("id") == "DISCIPLINARY"
            ),
            0,
        ),
        "free_elective": next(
            (
                item.get("required_credits", 0)
                for item in components
                if isinstance(item, Mapping) and item.get("id") == "FREE_ELECTIVE"
            ),
            0,
        ),
    }
    if not report.ok:
        return report
    if report.unknowns:
        report.warnings.append(f"{len(report.unknowns)} items remain UNKNOWN or pending review")
    return report


def validated_document(document: BaselineDocument) -> ValidationReport:
    report = validate_baseline(document.payload)
    if not report.ok:
        raise BaselineValidationError(report)
    return report


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _semantic_entities(payload: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    projection: dict[str, list[dict[str, Any]]] = {}
    for entity, key_fields in ENTITY_KEYS:
        rows = _sort_records(payload.get(entity, []), key_fields)
        # Page locators and raw excerpts are provenance, not semantic content.
        for row in rows:
            row.pop("source_page", None)
            row.pop("evidence", None)
        projection[entity] = rows
    return projection


def semantic_diff(
    base: Mapping[str, Any] | None,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Compute deterministic entity-level semantic differences."""

    base_entities = _semantic_entities(base or {})
    candidate_entities = _semantic_entities(candidate)
    added: dict[str, list[dict[str, Any]]] = {}
    removed: dict[str, list[dict[str, Any]]] = {}
    changed: list[dict[str, Any]] = []
    for entity, key_fields in ENTITY_KEYS:
        fields = key_fields.split("|")
        base_map = {
            tuple(str(row.get(field, "")) for field in fields): row for row in base_entities[entity]
        }
        candidate_map = {
            tuple(str(row.get(field, "")) for field in fields): row
            for row in candidate_entities[entity]
        }
        entity_added = [candidate_map[key] for key in sorted(set(candidate_map) - set(base_map))]
        entity_removed = [base_map[key] for key in sorted(set(base_map) - set(candidate_map))]
        if entity_added:
            added[entity] = entity_added
        if entity_removed:
            removed[entity] = entity_removed
        for key in sorted(set(base_map) & set(candidate_map)):
            if base_map[key] != candidate_map[key]:
                changed.append(
                    {
                        "entity": entity,
                        "key": "/".join(key),
                        "before": base_map[key],
                        "after": candidate_map[key],
                    }
                )
    base_identity = dict(_as_mapping((base or {}).get("identity"), "identity", ValidationReport()))
    candidate_identity = dict(
        _as_mapping(candidate.get("identity"), "identity", ValidationReport())
    )
    if base_identity != candidate_identity:
        changed.append(
            {
                "entity": "identity",
                "key": "identity",
                "before": base_identity,
                "after": candidate_identity,
            }
        )
    base_revision = dict(_as_mapping((base or {}).get("revision"), "revision", ValidationReport()))
    candidate_revision = dict(
        _as_mapping(candidate.get("revision"), "revision", ValidationReport())
    )
    if base_revision != candidate_revision:
        changed.append(
            {
                "entity": "revision",
                "key": "revision",
                "before": base_revision,
                "after": candidate_revision,
            }
        )
    return {
        "base_fingerprint": baseline_fingerprint(base) if base else None,
        "candidate_fingerprint": baseline_fingerprint(candidate),
        "added": added,
        "removed": removed,
        "changed": changed,
        "has_changes": bool(added or removed or changed),
    }


def render_ingestion_report(
    document: BaselineDocument,
    validation: ValidationReport,
    *,
    source_sha256: str,
    source_path: Path,
    semantic: Mapping[str, Any],
    revision_status: str,
    evidence_without_snapshot: int,
) -> str:
    counts = "\n".join(f"- {key}: {value}" for key, value in validation.counts.items())
    totals = "\n".join(f"- {key}: {value}" for key, value in validation.totals.items())
    unknowns = (
        "\n".join(
            f"- `{item.get('course_code') or item.get('owner_course_code') or item.get('id', 'unknown')}`: "
            f"{item.get('issue') or item.get('reason') or item.get('status')}"
            for item in validation.unknowns
        )
        or "- Ninguno"
    )
    errors = "\n".join(f"- {error}" for error in validation.errors) or "- Ninguno"
    warnings = "\n".join(f"- {warning}" for warning in validation.warnings) or "- Ninguno"
    return f"""# Informe de ingestión curricular

- Archivo estructurado: `{document.path}`
- Schema: `{document.schema_version}`
- Fingerprint JSON: `{document.fingerprint}`
- Snapshot fuente: `{source_path}`
- SHA-256 fuente: `{source_sha256}`
- Estado de la revisión generada: `{revision_status}`
- Propuesta editorial: `DRAFT`; la ingestión no publica automáticamente.

## Conteos

{counts}

## Créditos declarados

{totals}

## Validación

### Errores
{errors}

### Advertencias
{warnings}

## Ambigüedades y revisión humana

{unknowns}

## Evidencia

- Reglas con snapshot y locator de página: importadas cuando el baseline proporciona `evidence.page`.
- Reglas sin snapshot local: `{evidence_without_snapshot}`; permanecen pendientes y no se marcan como `VERIFIED`.

## Diff semántico

- Cambios: `{semantic.get("has_changes", False)}`
- Entidades agregadas: `{sum(len(items) for items in semantic.get("added", {}).values())}`
- Entidades eliminadas: `{sum(len(items) for items in semantic.get("removed", {}).values())}`
- Entidades modificadas: `{len(semantic.get("changed", []))}`
"""
