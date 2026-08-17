from __future__ import annotations

import datetime
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from domain.enums import (
    CountPolicy,
    EpistemicStatus,
    MembershipRole,
    ProposalStatus,
    RequirementGroupKind,
    RequirementPurpose,
    RevisionStatus,
)
from domain.rules.ast import AST_SCHEMA_VERSION, ast_hash, parse_rule
from domain.rules.errors import RuleSchemaError
from modules.curriculum.models import (
    Course,
    CourseVersion,
    CurriculumPlan,
    CurriculumRevision,
    PlanMembership,
    RequirementGroup,
)
from modules.governance.models import (
    ChangeProposal,
    Evidence,
    ExtractionCandidate,
    NormativeDocument,
    SourceSnapshot,
)
from modules.imports.models import ImportBatch
from modules.institutions.models import Campus, Faculty, Institution, Program
from modules.observability.metrics import measure_job_timing
from modules.rules.models import Requirement

from .baseline import (
    BaselineDocument,
    load_baseline,
    render_ingestion_report,
    semantic_diff,
    sha256_file,
    validated_document,
)

IMPORTER_VERSION = "curriculum-baseline/1.0.0"
DEFAULT_BASELINE = (
    Path(__file__).resolve().parents[5]
    / "data"
    / "curricula"
    / "unal"
    / "bogota"
    / "estadistica"
    / "2514"
    / "plan_2514_acuerdo_496_2023.json"
)


class CurriculumImportError(RuntimeError):
    """Raised when an import cannot safely be applied."""


@dataclass(frozen=True, slots=True)
class CurriculumImportResult:
    batch_id: str
    revision_id: str
    proposal_id: str
    fingerprint: str
    source_sha256: str
    report_path: str
    report_markdown: str
    validation: dict[str, Any]
    semantic_diff: dict[str, Any]
    counts: dict[str, int]


def project_root() -> Path:
    configured = getattr(settings, "PROJECT_ROOT", None)
    return Path(configured) if configured else Path(__file__).resolve().parents[5]


def _resolve_repo_path(value: str | Path | None) -> Path:
    if value is None:
        return DEFAULT_BASELINE
    path = Path(value)
    return path if path.is_absolute() else project_root() / path


def _source_document(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("source_documents")
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        return value[0]
    raise CurriculumImportError("baseline must contain one source_documents object")


def _date(value: object, context: str) -> datetime.date:
    if not isinstance(value, str):
        raise CurriculumImportError(f"{context} must be an ISO date")
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise CurriculumImportError(f"{context} must be an ISO date") from exc


def _json_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _status(value: object) -> str:
    if value in {
        EpistemicStatus.VERIFIED.value,
        EpistemicStatus.DERIVED.value,
        EpistemicStatus.INFERRED_PENDING_REVIEW.value,
        EpistemicStatus.UNKNOWN.value,
        EpistemicStatus.DISPUTED.value,
        EpistemicStatus.SUPERSEDED.value,
    }:
        return str(value)
    # Preserve the source value in metadata, but do not publish a status that
    # has no archived local evidence in the project.
    return EpistemicStatus.INFERRED_PENDING_REVIEW.value


def _requirement_purpose(value: object) -> str:
    if value == "PREREQUISITE":
        return RequirementPurpose.ENROLLMENT_PREREQUISITE.value
    if value == "COREQUISITE":
        return RequirementPurpose.COREQUISITE.value
    # Source tables occasionally label the dependency column without proving
    # whether it is a prerequisite or a corequisite. Preserve that raw label
    # in metadata while storing the safe enrollment-purpose category.
    return RequirementPurpose.ENROLLMENT_PREREQUISITE.value


def _membership_role(row: dict[str, Any]) -> str:
    if row.get("mandatory") is True:
        return MembershipRole.MANDATORY.value
    if row.get("group") == "FREE_ELECTIVE":
        return MembershipRole.FREE_ELECTIVE_OPTION.value
    return MembershipRole.ELECTIVE_OPTION.value


def _component_code(component_id: str) -> str:
    return f"COMPONENT::{component_id}"


def _evidence(
    *,
    snapshot: SourceSnapshot,
    row: dict[str, Any],
    locator_key: str,
    annotation: str,
) -> Evidence | None:
    source_evidence = row.get("evidence")
    if not isinstance(source_evidence, dict):
        return None
    page = source_evidence.get("page")
    if isinstance(page, bool) or not isinstance(page, int) or page <= 0:
        return None
    excerpt = str(
        row.get("raw_source_text")
        or row.get("note")
        or json.dumps(row.get("ast", {}), ensure_ascii=False)
    )
    excerpt_hash = _json_hash(
        {
            "snapshot": str(snapshot.pk),
            "page": page,
            "locator": locator_key,
            "excerpt": excerpt,
        }
    )
    evidence, _ = Evidence.objects.get_or_create(
        snapshot=snapshot,
        page=page,
        line_locator=locator_key,
        excerpt_hash=excerpt_hash,
        defaults={
            "section": str(source_evidence.get("section", "")),
            "excerpt": excerpt,
            "annotation": annotation,
        },
    )
    changed = False
    if evidence.excerpt != excerpt:
        evidence.excerpt = excerpt
        changed = True
    if evidence.annotation != annotation:
        evidence.annotation = annotation
        changed = True
    if changed:
        evidence.save(update_fields=["excerpt", "annotation", "updated_at"])
    return evidence


def _validated_ast(value: object) -> tuple[dict[str, Any], str]:
    try:
        rule = parse_rule(value)
    except RuleSchemaError as exc:
        raise CurriculumImportError(f"invalid requirement AST: {exc}") from exc
    if not isinstance(value, dict):
        raise CurriculumImportError("requirement AST must be a JSON object")
    return value, ast_hash(rule)


def _published_version_is_protected(version: CourseVersion) -> bool:
    return PlanMembership.objects.filter(
        course_version=version, revision__status=RevisionStatus.PUBLISHED.value
    ).exists()


def _upsert_course_version(
    *,
    course: Course,
    row: dict[str, Any],
    valid_from: datetime.date,
    revision_code: str,
) -> CourseVersion:
    code = str(row["code"])
    version, created = CourseVersion.objects.get_or_create(
        course=course,
        valid_from=valid_from,
        defaults={
            "name": str(row.get("name", code)),
            "credits": row.get("credits"),
            "metadata": {
                "source": "curriculum_baseline",
                "source_code": code,
                "source_revision": revision_code,
            },
        },
    )
    desired_metadata = {
        "source": "curriculum_baseline",
        "source_code": code,
        "source_revision": revision_code,
    }
    changed = (
        version.name != row.get("name", code)
        or version.credits != row.get("credits")
        or version.metadata != desired_metadata
    )
    if not created and changed and _published_version_is_protected(version):
        raise CurriculumImportError(
            f"cannot update CourseVersion {code}: it is referenced by a published revision"
        )
    if changed:
        version.name = str(row.get("name", code))
        version.credits = row.get("credits")
        version.metadata = desired_metadata
        version.save(update_fields=["name", "credits", "metadata", "updated_at"])
    return version


def _latest_base_revision(
    plan: CurriculumPlan, candidate: CurriculumRevision
) -> CurriculumRevision | None:
    return (
        CurriculumRevision.objects.filter(plan=plan)
        .exclude(pk=candidate.pk)
        .order_by("-effective_from", "-created_at")
        .first()
    )


def _proposal_payload(revision: CurriculumRevision) -> dict[str, Any]:
    metadata = revision.metadata if isinstance(revision.metadata, dict) else {}
    source_payload = metadata.get("source_payload")
    return source_payload if isinstance(source_payload, dict) else {}


def _sync_extraction_candidates(
    *, proposal: ChangeProposal, snapshot: SourceSnapshot, semantic: dict[str, Any]
) -> None:
    """Materialize the semantic diff as reviewable, idempotent candidates."""

    added = semantic.get("added", {})
    if isinstance(added, dict):
        for entity in sorted(added):
            rows = added[entity]
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                key = "/".join(
                    str(row.get(field, ""))
                    for field in {
                        "courses": ("code",),
                        "components": ("id",),
                        "groups": ("id",),
                        "memberships": ("course_code", "group"),
                        "enrollment_requirements": ("owner_course_code", "purpose"),
                        "graduation_requirements": ("id",),
                        "known_ambiguities": ("course_code", "issue"),
                    }.get(entity, ("id",))
                )
                ExtractionCandidate.objects.get_or_create(
                    proposal=proposal,
                    source_snapshot=snapshot,
                    entity=entity,
                    entity_key=key,
                    operation="ADD",
                    defaults={"after": row},
                )

    removed = semantic.get("removed", {})
    if isinstance(removed, dict):
        for entity in sorted(removed):
            rows = removed[entity]
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                key = "/".join(
                    str(row.get(field, ""))
                    for field in {
                        "courses": ("code",),
                        "components": ("id",),
                        "groups": ("id",),
                        "memberships": ("course_code", "group"),
                        "enrollment_requirements": ("owner_course_code", "purpose"),
                        "graduation_requirements": ("id",),
                        "known_ambiguities": ("course_code", "issue"),
                    }.get(entity, ("id",))
                )
                ExtractionCandidate.objects.get_or_create(
                    proposal=proposal,
                    source_snapshot=snapshot,
                    entity=entity,
                    entity_key=key,
                    operation="REMOVE",
                    defaults={"before": row},
                )

    changed = semantic.get("changed", [])
    if isinstance(changed, list):
        for row in changed:
            if not isinstance(row, dict):
                continue
            ExtractionCandidate.objects.get_or_create(
                proposal=proposal,
                source_snapshot=snapshot,
                entity=str(row.get("entity", "unknown")),
                entity_key=str(row.get("key", "")),
                operation="CHANGE",
                defaults={"before": row.get("before"), "after": row.get("after")},
            )


@measure_job_timing("curriculum_import")
@transaction.atomic  # type: ignore[untyped-decorator]
def import_curriculum_baseline(
    path: str | Path | None = DEFAULT_BASELINE,
    *,
    report_path: str | Path | None = None,
    created_by: object | None = None,
) -> CurriculumImportResult:
    """Import a verified source baseline into a DRAFT revision idempotently."""

    document = load_baseline(_resolve_repo_path(path))
    validation = validated_document(document)
    source = _source_document(document.payload)
    source_path = _resolve_repo_path(str(source.get("local_path", "")))
    if not source_path.is_file():
        raise CurriculumImportError(f"source snapshot file does not exist: {source_path}")
    source_sha256 = sha256_file(source_path)
    expected_sha256 = str(source.get("sha256", "")).lower()
    if source_sha256.lower() != expected_sha256:
        raise CurriculumImportError(
            f"source SHA-256 mismatch: expected {expected_sha256}, got {source_sha256}"
        )

    identity = document.payload["identity"]
    revision_data = document.payload["revision"]
    if not isinstance(identity, dict) or not isinstance(revision_data, dict):
        raise CurriculumImportError("baseline identity and revision must be objects")
    effective_from = _date(revision_data.get("effective_from"), "revision.effective_from")
    revision_code = str(revision_data.get("revision_code", ""))
    if not revision_code:
        raise CurriculumImportError("revision.revision_code is required")

    institution, _ = Institution.objects.update_or_create(
        slug="unal",
        defaults={
            "legal_name": "Universidad Nacional de Colombia",
            "display_name": "Universidad Nacional de Colombia",
            "country_code": "CO",
        },
    )
    campus, _ = Campus.objects.update_or_create(
        institution=institution,
        code="BOGOTA",
        defaults={"name": str(identity.get("campus", "Bogotá")), "timezone": "America/Bogota"},
    )
    faculty, _ = Faculty.objects.update_or_create(
        campus=campus,
        code="CIENCIAS",
        defaults={"name": str(identity.get("faculty", "Facultad de Ciencias"))},
    )
    program, _ = Program.objects.update_or_create(
        faculty=faculty,
        code=str(identity.get("program_code", "2514")),
        defaults={
            "snies": str(identity.get("snies", "")),
            "name": str(identity.get("program", "Estadística")),
            "degree_name": str(identity.get("degree_name", "Estadístico(a)")),
            "estimated_terms": identity.get("estimated_terms"),
        },
    )
    plan, _ = CurriculumPlan.objects.update_or_create(
        program=program,
        code=str(identity.get("program_code", "2514")),
        defaults={
            "title": f"{identity.get('program', 'Estadística')} — Plan {identity.get('program_code', '2514')}"
        },
    )

    source_document, _ = NormativeDocument.objects.update_or_create(
        issuer="Universidad Nacional de Colombia",
        document_type="ACUERDO",
        number="496",
        year=2023,
        defaults={
            "title": str(source.get("title", "Acuerdo 496 de 2023")),
            "metadata": {
                "source_id": source.get("id"),
                "schema_version": document.schema_version,
                "baseline_fingerprint": document.fingerprint,
            },
        },
    )
    snapshot, _ = SourceSnapshot.objects.get_or_create(
        document=source_document,
        sha256=source_sha256,
        defaults={
            "captured_at": timezone.now(),
            "mime_type": "application/pdf",
            "storage_key": str(source.get("local_path", "")),
            "metadata": {
                "source_id": source.get("id"),
                "pages": source.get("pages"),
                "baseline_fingerprint": document.fingerprint,
                "capture_mode": "archived_local_source",
            },
        },
    )

    revision, revision_created = CurriculumRevision.objects.get_or_create(
        plan=plan,
        revision_code=revision_code,
        defaults={
            "effective_from": effective_from,
            "status": RevisionStatus.DRAFT.value,
            "total_required_credits": int(identity.get("total_required_credits", 0)),
            "source_set_hash": source_sha256,
            "content_hash": document.fingerprint,
        },
    )
    if not revision_created and revision.status != RevisionStatus.DRAFT.value:
        raise CurriculumImportError(
            f"cannot import into revision {revision.revision_code} with status {revision.status}; "
            "source ingestion only mutates DRAFT revisions"
        )
    revision.effective_from = effective_from
    revision.total_required_credits = int(identity.get("total_required_credits", 0))
    revision.source_set_hash = source_sha256
    revision.content_hash = document.fingerprint
    revision.metadata = {
        "schema_version": document.schema_version,
        "fingerprint": document.fingerprint,
        "source_id": source.get("id"),
        "source_path": str(source.get("local_path", "")),
        "source_pages": source.get("pages"),
        "components": document.payload.get("components", []),
        "source_payload": document.payload,
    }
    revision.save()

    component_groups: dict[str, RequirementGroup] = {}
    for index, row in enumerate(document.payload.get("components", [])):
        if not isinstance(row, dict):
            continue
        component_id = str(row.get("id", ""))
        component_group, _ = RequirementGroup.objects.update_or_create(
            revision=revision,
            code=_component_code(component_id),
            defaults={
                "parent": None,
                "label": str(row.get("name", component_id)),
                "kind": RequirementGroupKind.COMPONENT.value,
                "required_credits": int(row.get("required_credits", 0)),
                "sort_order": index,
                "metadata": {"source_component_id": component_id, "source": "curriculum_baseline"},
            },
        )
        component_groups[component_id] = component_group

    groups: dict[str, RequirementGroup] = {}
    for index, row in enumerate(document.payload.get("groups", [])):
        if not isinstance(row, dict):
            continue
        group_id = str(row.get("id", ""))
        component_id = str(row.get("component", ""))
        group, _ = RequirementGroup.objects.update_or_create(
            revision=revision,
            code=group_id,
            defaults={
                "parent": component_groups.get(component_id),
                "label": str(row.get("name", group_id)),
                "kind": RequirementGroupKind.GROUP.value,
                "required_credits": int(row.get("required_credits", 0)),
                "sort_order": index,
                "metadata": {
                    "source_group_id": group_id,
                    "source_component_id": component_id,
                    "source": "curriculum_baseline",
                },
            },
        )
        groups[group_id] = group

    versions: dict[str, CourseVersion] = {}
    for row in document.payload.get("courses", []):
        if not isinstance(row, dict):
            continue
        code = str(row.get("code", ""))
        course, _ = Course.objects.update_or_create(
            institution=institution,
            code=code,
            defaults={"active": True},
        )
        versions[code] = _upsert_course_version(
            course=course,
            row=row,
            valid_from=effective_from,
            revision_code=revision_code,
        )

    for row in document.payload.get("memberships", []):
        if not isinstance(row, dict):
            continue
        course_code = str(row.get("course_code", ""))
        group_id = str(row.get("group", ""))
        if course_code not in versions or group_id not in groups:
            raise CurriculumImportError(f"membership reference missing: {course_code}/{group_id}")
        PlanMembership.objects.update_or_create(
            revision=revision,
            course_version=versions[course_code],
            group=groups[group_id],
            defaults={
                "role": _membership_role(row),
                "count_policy": CountPolicy.CREDITS.value,
                "metadata": {
                    "source_page": row.get("source_page"),
                    "epistemic_status": row.get("status"),
                    "source_group_id": group_id,
                },
            },
        )

    evidence_without_snapshot = 0
    for row in document.payload.get("enrollment_requirements", []):
        if not isinstance(row, dict):
            continue
        owner_code = str(row.get("owner_course_code", ""))
        if owner_code not in versions:
            raise CurriculumImportError(f"requirement owner course missing: {owner_code}")
        raw_purpose = row.get("purpose")
        purpose = _requirement_purpose(raw_purpose)
        status = _status(row.get("epistemic_status"))
        code = f"CURRICULUM:{purpose}:{owner_code}"
        ast, ast_digest = _validated_ast(row.get("ast", {}))
        requirement, _ = Requirement.objects.update_or_create(
            revision=revision,
            owner_type="COURSE",
            owner_id=versions[owner_code].course_id,
            code=code,
            defaults={
                "purpose": purpose,
                "ast": ast,
                "ast_schema_version": AST_SCHEMA_VERSION,
                "ast_hash": ast_digest,
                "epistemic_status": status,
                "explanation_key": f"curriculum.{revision_code}.{code}",
                "metadata": {
                    "source_id": source.get("id"),
                    "source_page": row.get("evidence", {}).get("page")
                    if isinstance(row.get("evidence"), dict)
                    else None,
                    "raw_epistemic_status": row.get("epistemic_status"),
                    "raw_purpose": raw_purpose,
                    "note": row.get("note", ""),
                    "raw_source_text": row.get("raw_source_text", ""),
                    "revision_id": str(revision.pk),
                },
            },
        )
        attached = _evidence(
            snapshot=snapshot,
            row=row,
            locator_key=f"course:{owner_code}/requirement:{raw_purpose}",
            annotation="Imported from archived Acuerdo 496 de 2023 baseline.",
        )
        requirement.evidence.set([attached] if attached else [])
        if status == EpistemicStatus.VERIFIED.value and attached is None:
            requirement.epistemic_status = EpistemicStatus.INFERRED_PENDING_REVIEW.value
            requirement.save(update_fields=["epistemic_status", "updated_at"])
            evidence_without_snapshot += 1

    for row in document.payload.get("graduation_requirements", []):
        if not isinstance(row, dict):
            continue
        raw_status = row.get("epistemic_status")
        status = _status(raw_status)
        if status == EpistemicStatus.VERIFIED.value and not row.get("evidence"):
            status = EpistemicStatus.INFERRED_PENDING_REVIEW.value
            evidence_without_snapshot += 1
        code = f"GRADUATION:{row.get('id', 'UNKNOWN')}"
        ast, ast_digest = _validated_ast(row.get("ast", {}))
        requirement, _ = Requirement.objects.update_or_create(
            revision=revision,
            owner_type="REVISION",
            owner_id=revision.pk,
            code=code,
            defaults={
                "purpose": RequirementPurpose.GRADUATION.value,
                "ast": ast,
                "ast_schema_version": AST_SCHEMA_VERSION,
                "ast_hash": ast_digest,
                "epistemic_status": status,
                "explanation_key": f"curriculum.{revision_code}.{code}",
                "metadata": {
                    "raw_epistemic_status": raw_status,
                    "note": row.get("note", ""),
                    "source_url": row.get("source_url", ""),
                    "evidence_missing": not bool(row.get("evidence")),
                    "revision_id": str(revision.pk),
                },
            },
        )
        requirement.evidence.clear()

    base_revision = _latest_base_revision(plan, revision)
    base_payload = _proposal_payload(base_revision) if base_revision else None
    semantic = semantic_diff(base_payload, document.payload)
    proposal_key = f"{plan.code}:{revision.revision_code}:{document.fingerprint}"
    proposal, _ = ChangeProposal.objects.get_or_create(
        proposal_key=proposal_key,
        defaults={
            "title": f"Ingestión {revision.revision_code}",
            "status": ProposalStatus.DRAFT.value,
            "base_revision": base_revision,
            "candidate_revision": revision,
            "source_snapshot": snapshot,
            "content_fingerprint": document.fingerprint,
            "semantic_diff": semantic,
            "rationale": "Generated from an archived source baseline; requires human review before publication.",
            "created_by": created_by if getattr(created_by, "pk", None) else None,
        },
    )
    if proposal.semantic_diff != semantic and proposal.status == ProposalStatus.DRAFT.value:
        proposal.semantic_diff = semantic
        proposal.save(update_fields=["semantic_diff", "updated_at"])
    _sync_extraction_candidates(proposal=proposal, snapshot=snapshot, semantic=semantic)

    report = render_ingestion_report(
        document,
        validation,
        source_sha256=source_sha256,
        source_path=source_path,
        semantic=semantic,
        revision_status=revision.status,
        evidence_without_snapshot=evidence_without_snapshot,
    )
    if report_path is None:
        target_report = (
            project_root()
            / "artifacts"
            / "ingestion"
            / f"{plan.code}_{revision.revision_code}_{document.fingerprint[:12]}.md"
        )
    else:
        target_report = _resolve_repo_path(report_path)
    target_report.parent.mkdir(parents=True, exist_ok=True)
    target_report.write_text(report, encoding="utf-8")

    batch, _ = ImportBatch.objects.get_or_create(
        source_kind="CURRICULUM_BASELINE",
        content_fingerprint=document.fingerprint,
        parser_version=IMPORTER_VERSION,
        defaults={
            "original_filename": document.path.name,
            "content_sha256": document.fingerprint,
            "storage_key": str(document.path),
            "schema_version": document.schema_version,
        },
    )
    batch.status = "APPLIED"
    batch.original_filename = document.path.name
    batch.content_sha256 = document.fingerprint
    batch.storage_key = str(document.path)
    batch.schema_version = document.schema_version
    batch.source_snapshot = snapshot
    batch.curriculum_revision = revision
    batch.validation_errors = validation.errors
    batch.report_markdown = report
    batch.semantic_diff = semantic
    batch.metadata = {
        "source_sha256": source_sha256,
        "source_path": str(source_path),
        "revision_code": revision.revision_code,
        "proposal_id": str(proposal.pk),
        "counts": validation.counts,
    }
    batch.save()

    return CurriculumImportResult(
        batch_id=str(batch.pk),
        revision_id=str(revision.pk),
        proposal_id=str(proposal.pk),
        fingerprint=document.fingerprint,
        source_sha256=source_sha256,
        report_path=str(target_report),
        report_markdown=report,
        validation=validation.as_dict(),
        semantic_diff=semantic,
        counts=validation.counts,
    )


def validate_curriculum_file(
    path: str | Path | None = DEFAULT_BASELINE,
) -> tuple[BaselineDocument, dict[str, Any]]:
    document = load_baseline(_resolve_repo_path(path))
    report = validated_document(document)
    return document, report.as_dict()


def diff_curriculum_files(
    candidate: str | Path | None = DEFAULT_BASELINE,
    base: str | Path | None = None,
) -> dict[str, Any]:
    candidate_document = load_baseline(_resolve_repo_path(candidate))
    base_document = load_baseline(_resolve_repo_path(base)) if base else None
    if base_document:
        validated_document(base_document)
    validated_document(candidate_document)
    return semantic_diff(
        base_document.payload if base_document else None,
        candidate_document.payload,
    )
