from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any
from uuid import UUID, uuid4

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from domain.enums import (
    EpistemicStatus,
    ExtractionCandidateStatus,
    NotificationDeliveryStatus,
    ProposalStatus,
    PublicationImpactStatus,
    ReviewDecision,
    RevisionStatus,
    UserRole,
)
from modules.audit.models import DegreeAuditRun
from modules.curriculum.application.services import (
    CurriculumRevisionService,
    RevisionTransitionError,
)
from modules.curriculum.models import CurriculumRevision
from modules.identity.application.audit import record_audit_event
from modules.identity.application.authorization import (
    active_role_assignments,
    can_edit_revision,
    can_publish_revision,
    has_role,
)
from modules.imports.application.baseline import ValidationReport, validate_baseline
from modules.notifications.models import NotificationOutbox
from modules.observability.metrics import measure_domain_timing
from modules.rules.models import Requirement
from modules.student_records.models import ProgramEnrollment

from ..models import (
    ChangeProposal,
    Evidence,
    ExtractionCandidate,
    NormativeDocument,
    Publication,
    PublicationEvent,
    PublicationImpact,
    Review,
    SourceSnapshot,
)


class GovernanceError(RuntimeError):
    """An explainable failure in the source-to-publication workflow."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def proposal_version(proposal: ChangeProposal) -> str:
    return proposal.updated_at.isoformat()


def candidate_version(candidate: ExtractionCandidate) -> str:
    return candidate.updated_at.isoformat()


def _safe_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_json(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _role_allowed(actor: Any) -> bool:
    return any(
        has_role(actor, role) for role in (UserRole.EDITOR, UserRole.REVIEWER, UserRole.ADMIN)
    )


def _proposal_scope_filter(actor: Any) -> Q:
    """Return a queryset predicate for the actor's editorial scopes.

    Source documents and snapshots do not carry a duplicated institution key;
    their access is therefore derived through the candidate revision of a
    proposal. The predicate is applied in the queryset, not after fetching
    rows, so a scoped role cannot enumerate another institution's inbox.
    """

    if getattr(actor, "is_superuser", False):
        return Q()
    assignments = [
        assignment
        for assignment in active_role_assignments(actor)
        if assignment.role in {UserRole.EDITOR.value, UserRole.REVIEWER.value, UserRole.ADMIN.value}
    ]
    if not assignments:
        return Q(pk__in=[])
    predicate = Q(pk__in=[])
    for assignment in assignments:
        if assignment.program_id:
            predicate |= Q(candidate_revision__plan__program_id=assignment.program_id)
        elif assignment.institution_id:
            predicate |= Q(
                candidate_revision__plan__program__faculty__campus__institution_id=assignment.institution_id
            )
        else:
            return Q()
    return predicate


def _accessible_proposals(actor: Any) -> Any:
    return ChangeProposal.objects.filter(_proposal_scope_filter(actor))


def _require_editor_access(actor: Any, proposal: ChangeProposal) -> None:
    if not can_edit_revision(actor, proposal.candidate_revision):
        raise GovernanceError(
            "The actor cannot edit this draft revision.", code="governance_forbidden"
        )


def _can_view_proposal(actor: Any, proposal: ChangeProposal) -> bool:
    if can_edit_revision(actor, proposal.candidate_revision):
        return True
    revision = proposal.candidate_revision
    institution_id = revision.plan.program.faculty.campus.institution_id
    program_id = revision.plan.program_id
    return any(
        has_role(actor, role, institution_id=institution_id, program_id=program_id)
        for role in (UserRole.EDITOR, UserRole.REVIEWER, UserRole.ADMIN)
    )


def _require_reviewer_access(actor: Any, proposal: ChangeProposal) -> None:
    if not can_publish_revision(actor, proposal.candidate_revision):
        raise GovernanceError(
            "Only a scoped reviewer or administrator may approve or publish a revision.",
            code="governance_reviewer_required",
        )


def _require_version(actual: str, expected: str | None) -> None:
    if not expected:
        raise GovernanceError(
            "The current resource version is required.", code="precondition_required"
        )
    if expected.strip('"') != actual:
        raise GovernanceError(
            "The resource changed while it was being edited; reload before retrying.",
            code="governance_concurrency_conflict",
        )


def _proposal_queryset() -> Any:
    return ChangeProposal.objects.select_related(
        "base_revision__plan__program__faculty__campus__institution",
        "candidate_revision__plan__program__faculty__campus__institution",
        "source_snapshot__document",
        "created_by",
    ).prefetch_related(
        "reviews__reviewer",
        "extraction_candidates__evidence__snapshot__document",
        "candidate_revision__requirements__evidence__snapshot__document",
    )


def get_proposal(actor: Any, proposal_id: UUID | str) -> ChangeProposal:
    try:
        proposal = _proposal_queryset().get(pk=proposal_id)
    except ChangeProposal.DoesNotExist as exc:
        raise GovernanceError("The proposal was not found.", code="proposal_not_found") from exc
    if not _can_view_proposal(actor, proposal):
        raise GovernanceError(
            "The actor cannot view this editorial proposal.", code="governance_forbidden"
        )
    return proposal


def list_source_inbox(actor: Any) -> dict[str, Any]:
    if not _role_allowed(actor):
        raise GovernanceError(
            "Editorial access is required for the source inbox.", code="governance_forbidden"
        )
    scoped_proposals = _accessible_proposals(actor)
    documents = list(
        NormativeDocument.objects.filter(snapshots__change_proposals__in=scoped_proposals)
        .distinct()
        .order_by("-updated_at", "-year")[:100]
    )
    snapshots = list(
        SourceSnapshot.objects.filter(change_proposals__in=scoped_proposals)
        .select_related("document")
        .distinct()
        .order_by("-captured_at", "-id")[:100]
    )
    proposals = list(
        _proposal_queryset()
        .filter(_proposal_scope_filter(actor))
        .order_by("-updated_at", "-id")[:100]
    )
    return {
        "documents": [_document_view(document) for document in documents],
        "snapshots": [_snapshot_view(snapshot) for snapshot in snapshots],
        "proposals": [_proposal_summary(proposal) for proposal in proposals],
        "workflow": [
            "DISCOVERED",
            "SNAPSHOT",
            "EXTRACTED",
            "DRAFT",
            "VALIDATED",
            "IN_REVIEW",
            "APPROVED",
            "PUBLISHED",
        ],
    }


def get_document(actor: Any, document_id: UUID | str) -> dict[str, Any]:
    if not _role_allowed(actor):
        raise GovernanceError(
            "Editorial access is required for source documents.", code="governance_forbidden"
        )
    if not NormativeDocument.objects.filter(
        pk=document_id,
        snapshots__change_proposals__in=_accessible_proposals(actor),
    ).exists():
        raise GovernanceError("The normative document was not found.", code="document_not_found")
    try:
        document = NormativeDocument.objects.prefetch_related("snapshots__evidence").get(
            pk=document_id
        )
    except NormativeDocument.DoesNotExist as exc:
        raise GovernanceError(
            "The normative document was not found.", code="document_not_found"
        ) from exc
    return {
        **_document_view(document),
        "snapshots": [_snapshot_view(snapshot) for snapshot in document.snapshots.all()],
    }


def get_snapshot(actor: Any, snapshot_id: UUID | str) -> dict[str, Any]:
    if not _role_allowed(actor):
        raise GovernanceError(
            "Editorial access is required for source snapshots.", code="governance_forbidden"
        )
    if not SourceSnapshot.objects.filter(
        pk=snapshot_id,
        change_proposals__in=_accessible_proposals(actor),
    ).exists():
        raise GovernanceError("The source snapshot was not found.", code="snapshot_not_found")
    try:
        snapshot = (
            SourceSnapshot.objects.select_related("document")
            .prefetch_related("evidence")
            .get(pk=snapshot_id)
        )
    except SourceSnapshot.DoesNotExist as exc:
        raise GovernanceError(
            "The source snapshot was not found.", code="snapshot_not_found"
        ) from exc
    return {
        **_snapshot_view(snapshot),
        "document": _document_view(snapshot.document),
        "evidence": [_evidence_view(item) for item in snapshot.evidence.all()],
        "archived_content": {
            "available": False,
            "storage_key": snapshot.storage_key,
            "note": "The viewer exposes the archived locator and hash; raw source bytes remain in private storage.",
        },
    }


def _validation_report(revision: CurriculumRevision) -> dict[str, Any]:
    payload = (
        revision.metadata.get("source_payload") if isinstance(revision.metadata, dict) else None
    )
    if isinstance(payload, dict):
        return validate_baseline(payload).as_dict()

    report = ValidationReport()
    verified_without_evidence = list(
        Requirement.objects.filter(
            revision=revision,
            epistemic_status=EpistemicStatus.VERIFIED.value,
            evidence__isnull=True,
        ).values_list("code", flat=True)
    )
    report.errors.extend(
        f"verified requirement {code} has no evidence" for code in verified_without_evidence
    )
    unknown_count = Requirement.objects.filter(
        revision=revision,
        epistemic_status__in=[
            EpistemicStatus.UNKNOWN.value,
            EpistemicStatus.INFERRED_PENDING_REVIEW.value,
            EpistemicStatus.DISPUTED.value,
        ],
    ).count()
    report.unknowns = (
        [{"count": unknown_count, "reason": "Rules require review."}] if unknown_count else []
    )
    report.warnings = [
        "The revision has no archived baseline payload for full structural validation."
    ]
    report.counts = {"requirements": revision.requirements.count()}
    report.totals = {"required_credits": revision.total_required_credits}
    return report.as_dict()


def _diff_bucket(entity: str) -> str:
    normalized = entity.lower()
    if "requirement" in normalized or "prerequisite" in normalized:
        return "requirements"
    if "group" in normalized or "component" in normalized or "membership" in normalized:
        return "groups"
    if "course" in normalized:
        return "courses"
    return "other"


def _row_key(row: Mapping[str, Any]) -> str:
    for key in ("code", "id", "key", "course_code", "owner_course_code"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return hashlib.sha256(
        json.dumps(_safe_json(dict(row)), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]


def _semantic_impact(diff: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Normalize the source diff into stable course/group/rule impact rows."""

    result: dict[str, list[dict[str, Any]]] = {
        "courses": [],
        "groups": [],
        "requirements": [],
        "other": [],
    }
    for operation_key in ("added", "removed"):
        values = diff.get(operation_key)
        if not isinstance(values, Mapping):
            continue
        for entity, rows in values.items():
            if not isinstance(rows, list):
                continue
            bucket = _diff_bucket(str(entity))
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                result[bucket].append(
                    {
                        "operation": "ADD" if operation_key == "added" else "REMOVE",
                        "entity": str(entity),
                        "key": _row_key(row),
                        "value": _safe_json(dict(row)),
                    }
                )
    changed = diff.get("changed")
    if isinstance(changed, list):
        for row in changed:
            if not isinstance(row, Mapping):
                continue
            entity = str(row.get("entity", "other"))
            bucket = _diff_bucket(entity)
            result[bucket].append(
                {
                    "operation": "CHANGE",
                    "entity": entity,
                    "key": str(row.get("key") or row.get("code") or row.get("id") or "unknown"),
                    "before": _safe_json(row.get("before")),
                    "after": _safe_json(row.get("after")),
                }
            )
    return result


def _affected_enrollment_snapshot(
    previous_revision: CurriculumRevision | None,
) -> list[dict[str, Any]]:
    if previous_revision is None:
        return []
    enrollments = list(
        ProgramEnrollment.objects.filter(revision_basis_id=previous_revision.pk)
        .select_related("student__user")
        .order_by("id")
    )
    audit_runs = list(
        DegreeAuditRun.objects.filter(
            enrollment_id__in=[enrollment.pk for enrollment in enrollments],
            revision_id=previous_revision.pk,
        ).order_by("enrollment_id", "-generated_at", "-created_at", "-id")
    )
    latest_by_enrollment: dict[str, DegreeAuditRun] = {}
    for run in audit_runs:
        latest_by_enrollment.setdefault(str(run.enrollment_id), run)
    return [
        {
            "enrollment": enrollment,
            "audit_run": latest_by_enrollment.get(str(enrollment.pk)),
        }
        for enrollment in enrollments
    ]


def _impact_analysis(proposal: ChangeProposal, validation: Mapping[str, Any]) -> dict[str, Any]:
    base_id = proposal.base_revision_id
    candidate_id = proposal.candidate_revision_id
    affected_audits = DegreeAuditRun.objects.filter(
        revision_id__in=[item for item in (base_id, candidate_id) if item]
    ).count()
    affected_enrollment_ids: list[str] = []
    if base_id:
        affected_enrollment_ids = list(
            ProgramEnrollment.objects.filter(revision_basis_id=base_id).values_list("pk", flat=True)
        )
    affected_students = len(affected_enrollment_ids)
    diff = proposal.semantic_diff if isinstance(proposal.semantic_diff, dict) else {}
    changed_items = sum(
        len(value) for value in diff.get("added", {}).values() if isinstance(value, list)
    )
    changed_items += sum(
        len(value) for value in diff.get("removed", {}).values() if isinstance(value, list)
    )
    changed_items += (
        len(diff.get("changed", [])) if isinstance(diff.get("changed", []), list) else 0
    )
    errors = [str(item) for item in validation.get("errors", [])]
    semantic_impact = _semantic_impact(diff)
    affected_audit_ids = list(
        DegreeAuditRun.objects.filter(enrollment_id__in=affected_enrollment_ids).values_list(
            "pk", flat=True
        )
    )
    return {
        "audits_affected": affected_audits,
        "students_potentially_affected": affected_students,
        "affected_enrollment_ids": affected_enrollment_ids,
        "affected_audit_ids": affected_audit_ids,
        "changed_semantic_items": changed_items,
        "changed_courses": semantic_impact["courses"],
        "changed_groups": semantic_impact["groups"],
        "changed_requirements": semantic_impact["requirements"],
        "new_unknowns": len(validation.get("unknowns", []))
        if isinstance(validation.get("unknowns"), list)
        else 0,
        "cycles_detected": sum(1 for item in errors if "cycle" in item.lower()),
        "totals_inconsistent": any("total" in item.lower() for item in errors),
        "publish_blockers": errors,
    }


def proposal_validation(proposal: ChangeProposal) -> dict[str, Any]:
    report = _validation_report(proposal.candidate_revision)
    evidence_missing = list(
        Requirement.objects.filter(
            revision=proposal.candidate_revision,
            epistemic_status=EpistemicStatus.VERIFIED.value,
            evidence__isnull=True,
        ).values_list("code", flat=True)
    )
    if evidence_missing:
        report = dict(report)
        report["errors"] = [
            *report.get("errors", []),
            *[f"verified requirement {code} has no evidence" for code in evidence_missing],
        ]
        report["ok"] = False
    report["verified_rules_without_evidence"] = evidence_missing
    return report


def _rule_explanation(node: object, depth: int = 0) -> str:
    if depth > 8 or not isinstance(node, Mapping):
        return "Condición no representable con la versión conocida del AST."
    node_type = str(node.get("type", "UNKNOWN"))
    if node_type == "COURSE_PASSED":
        return f"Haber aprobado el curso {node.get('course_code', 'desconocido')}."
    if node_type == "COURSE_IN_PROGRESS":
        return f"Tener en curso el curso {node.get('course_code', 'desconocido')}."
    if node_type == "COURSE_PASSED_OR_IN_PROGRESS":
        return f"Haber aprobado o estar cursando el curso {node.get('course_code', 'desconocido')}."
    if node_type == "COREQUISITE":
        return f"Cursar simultáneamente el curso {node.get('course_code', 'desconocido')}."
    if node_type == "GROUP_COMPLETED":
        return f"Completar la agrupación {node.get('group', 'desconocida')}."
    if node_type == "CREDITS_IN_GROUP":
        return f"Alcanzar {node.get('value', '?')} créditos en la agrupación {node.get('group', 'desconocida')} ({node.get('operator', '≥')})."
    if node_type == "CREDITS_IN_COMPONENT":
        return f"Alcanzar {node.get('value', '?')} créditos en el componente {node.get('component', 'desconocido')} ({node.get('operator', '≥')})."
    if node_type == "TOTAL_CREDITS":
        return f"Tener {node.get('value', '?')} créditos totales ({node.get('operator', '≥')})."
    if node_type == "PERCENTAGE_OF_PLAN":
        return f"Cumplir {node.get('numerator', '?')}/{node.get('denominator', '?')} de la regla porcentual del plan."
    if node_type == "MANDATORY_COURSES_COMPLETED":
        courses = ", ".join(str(item) for item in node.get("course_codes", []))
        return f"Completar los cursos obligatorios: {courses}."
    if node_type == "MINIMUM_GRADE":
        return f"Obtener al menos {node.get('minimum_grade', '?')} en el curso {node.get('course_code', 'desconocido')}."
    if node_type == "EXTERNAL_REQUIREMENT":
        return f"Acreditar el requisito externo {node.get('key', 'desconocido')}."
    if node_type == "EQUIVALENT_COURSE_PASSED":
        courses = ", ".join(str(item) for item in node.get("course_codes", []))
        return f"Haber aprobado una equivalencia entre: {courses}."
    if node_type == "NOT":
        return f"No cumplir: {_rule_explanation(node.get('child'), depth + 1)}"
    if node_type in {"ALL", "ANY"}:
        children = [_rule_explanation(item, depth + 1) for item in node.get("children", [])]
        joiner = " y " if node_type == "ALL" else " o "
        qualifier = "Todas las condiciones: " if node_type == "ALL" else "Al menos una condición: "
        return qualifier + joiner.join(children)
    return f"Condición {node_type}: {_safe_json(dict(node))}."


def _evidence_view(evidence: Evidence) -> dict[str, Any]:
    snapshot = evidence.snapshot
    document = snapshot.document
    locator = (
        evidence.line_locator
        or evidence.section
        or (f"page:{evidence.page}" if evidence.page else "source")
    )
    return {
        "id": evidence.pk,
        "reference": f"{snapshot.sha256}#{locator}",
        "snapshot_id": snapshot.pk,
        "snapshot_sha256": snapshot.sha256,
        "locator": locator,
        "page": evidence.page,
        "section": evidence.section,
        "excerpt": evidence.excerpt,
        "annotation": evidence.annotation,
        "source_title": document.title,
        "source_url": snapshot.source_url or document.canonical_url or None,
    }


def _document_view(document: NormativeDocument) -> dict[str, Any]:
    return {
        "id": document.pk,
        "issuer": document.issuer,
        "document_type": document.document_type,
        "number": document.number,
        "year": document.year,
        "title": document.title,
        "publication_date": document.publication_date,
        "canonical_url": document.canonical_url or None,
        "status": document.status,
        "metadata": document.metadata,
        "snapshot_count": document.snapshots.count() if hasattr(document, "snapshots") else 0,
        "version": document.updated_at.isoformat(),
    }


def _snapshot_view(snapshot: SourceSnapshot) -> dict[str, Any]:
    return {
        "id": snapshot.pk,
        "document_id": snapshot.document_id,
        "document_title": snapshot.document.title,
        "captured_at": snapshot.captured_at,
        "sha256": snapshot.sha256,
        "mime_type": snapshot.mime_type,
        "storage_key": snapshot.storage_key,
        "source_url": snapshot.source_url or None,
        "metadata": snapshot.metadata,
        "evidence_count": snapshot.evidence.count() if hasattr(snapshot, "evidence") else 0,
        "version": snapshot.updated_at.isoformat(),
    }


def _proposal_summary(proposal: ChangeProposal) -> dict[str, Any]:
    return {
        "id": proposal.pk,
        "proposal_key": proposal.proposal_key,
        "title": proposal.title,
        "status": proposal.status,
        "base_revision_id": proposal.base_revision_id,
        "candidate_revision_id": proposal.candidate_revision_id,
        "candidate_revision_code": proposal.candidate_revision.revision_code,
        "source_snapshot_id": proposal.source_snapshot_id,
        "source_title": proposal.source_snapshot.document.title,
        "content_fingerprint": proposal.content_fingerprint,
        "semantic_has_changes": bool(proposal.semantic_diff.get("has_changes")),
        "created_by": proposal.created_by.email if proposal.created_by else None,
        "updated_at": proposal.updated_at,
        "version": proposal_version(proposal),
        "pending_candidates": proposal.extraction_candidates.filter(
            status=ExtractionCandidateStatus.PENDING.value
        ).count(),
    }


def _requirement_view(requirement: Requirement) -> dict[str, Any]:
    return {
        "id": requirement.pk,
        "code": requirement.code,
        "owner_type": requirement.owner_type,
        "owner_id": requirement.owner_id,
        "purpose": requirement.purpose,
        "ast": requirement.ast,
        "ast_schema_version": requirement.ast_schema_version,
        "ast_hash": requirement.ast_hash,
        "epistemic_status": requirement.epistemic_status,
        "explanation_key": requirement.explanation_key,
        "human_explanation": _rule_explanation(requirement.ast),
        "metadata": requirement.metadata,
        "evidence": [_evidence_view(item) for item in requirement.evidence.all()],
        "version": requirement.updated_at.isoformat(),
    }


def _candidate_view(candidate: ExtractionCandidate) -> dict[str, Any]:
    return {
        "id": candidate.pk,
        "entity": candidate.entity,
        "entity_key": candidate.entity_key,
        "operation": candidate.operation,
        "before": candidate.before,
        "after": candidate.after,
        "status": candidate.status,
        "epistemic_status": candidate.epistemic_status,
        "evidence": [_evidence_view(item) for item in candidate.evidence.all()],
        "reviewed_by": candidate.reviewed_by.email if candidate.reviewed_by else None,
        "reviewed_at": candidate.reviewed_at,
        "note": candidate.note,
        "version": candidate_version(candidate),
    }


def _audit_view(event: Any) -> dict[str, Any]:
    return {
        "id": event.pk,
        "action": event.action,
        "object_type": event.object_type,
        "object_id": event.object_id,
        "actor": event.actor.email if event.actor else None,
        "created_at": event.created_at,
        "metadata": event.metadata,
    }


def get_proposal_detail(actor: Any, proposal_id: UUID | str) -> dict[str, Any]:
    proposal = get_proposal(actor, proposal_id)
    from modules.identity.models import AuditEvent

    requirements = list(
        proposal.candidate_revision.requirements.all().prefetch_related(
            "evidence__snapshot__document"
        )
    )
    candidate_ids = [str(item.pk) for item in proposal.extraction_candidates.all()]
    requirement_ids = [str(item.pk) for item in requirements]
    revision_ids = [
        str(item)
        for item in (proposal.base_revision_id, proposal.candidate_revision_id)
        if item is not None
    ]
    publication = getattr(proposal, "publication", None)
    publication_ids = [str(publication.pk)] if publication is not None else []
    publication_event = getattr(publication, "publication_event", None)
    publication_event_ids = [str(publication_event.pk)] if publication_event is not None else []
    events = (
        AuditEvent.objects.filter(
            Q(object_type="ChangeProposal", object_id=str(proposal.pk))
            | Q(object_type="ExtractionCandidate", object_id__in=candidate_ids)
            | Q(object_type="CurriculumRevision", object_id__in=revision_ids)
            | Q(object_type="Publication", object_id__in=publication_ids)
            | Q(object_type="PublicationEvent", object_id__in=publication_event_ids)
            | Q(object_type="Requirement", object_id__in=requirement_ids)
        )
        .select_related("actor")
        .order_by("-created_at", "-id")[:100]
    )
    validation = proposal_validation(proposal)
    return {
        **_proposal_summary(proposal),
        "rationale": proposal.rationale,
        "base_revision": _revision_view(proposal.base_revision),
        "candidate_revision": _revision_view(proposal.candidate_revision),
        "source_snapshot": _snapshot_view(proposal.source_snapshot),
        "semantic_diff": proposal.semantic_diff,
        "validation_report": validation,
        "impact_analysis": _impact_analysis(proposal, validation),
        "requirements": [_requirement_view(item) for item in requirements],
        "candidates": [_candidate_view(item) for item in proposal.extraction_candidates.all()],
        "reviews": [
            {
                "id": item.pk,
                "reviewer": item.reviewer.email,
                "decision": item.decision,
                "comment": item.comment,
                "proposal_version": item.proposal_version,
                "created_at": item.created_at,
            }
            for item in proposal.reviews.all()
        ],
        "publication": _publication_view(getattr(proposal, "publication", None)),
        "audit_events": [_audit_view(item) for item in events],
    }


def get_publication_impact(actor: Any, publication_id: UUID | str) -> dict[str, Any]:
    try:
        publication = Publication.objects.select_related(
            "proposal__candidate_revision__plan__program__faculty__campus",
            "revision",
        ).get(pk=publication_id)
    except Publication.DoesNotExist as exc:
        raise GovernanceError(
            "The publication receipt was not found.", code="publication_not_found"
        ) from exc
    if not _can_view_proposal(actor, publication.proposal):
        raise GovernanceError(
            "The actor cannot view this publication impact.", code="governance_forbidden"
        )
    try:
        event = PublicationEvent.objects.prefetch_related("enrollment_impacts").get(
            publication=publication
        )
    except PublicationEvent.DoesNotExist as exc:
        raise GovernanceError(
            "The publication has no immutable event record.", code="publication_event_missing"
        ) from exc
    return {"publication_id": publication.pk, "event": _publication_event_view(event)}


def _revision_view(revision: CurriculumRevision | None) -> dict[str, Any] | None:
    if revision is None:
        return None
    return {
        "id": revision.pk,
        "plan_code": revision.plan.code,
        "revision_code": revision.revision_code,
        "status": revision.status,
        "effective_from": revision.effective_from,
        "effective_to": revision.effective_to,
        "total_required_credits": revision.total_required_credits,
        "source_set_hash": revision.source_set_hash,
        "content_hash": revision.content_hash,
        "published_at": revision.published_at,
        "version": revision.updated_at.isoformat(),
    }


def _publication_view(publication: Publication | None) -> dict[str, Any] | None:
    if publication is None:
        return None
    event = getattr(publication, "publication_event", None)
    return {
        "id": publication.pk,
        "revision_id": publication.revision_id,
        "published_by": publication.published_by.email,
        "published_at": publication.published_at,
        "content_hash": publication.content_hash,
        "source_set_hash": publication.source_set_hash,
        "validation_report": publication.validation_report,
        "confirmation": publication.confirmation,
        "event": _publication_event_view(event),
    }


def _publication_event_view(event: PublicationEvent | None) -> dict[str, Any] | None:
    if event is None:
        return None
    impacts = list(event.enrollment_impacts.all())
    return {
        "id": event.pk,
        "event_key": event.event_key,
        "event_type": event.event_type,
        "schema_version": event.schema_version,
        "revision_id": event.revision_id,
        "superseded_revision_id": event.superseded_revision_id,
        "created_at": event.created_at,
        "changed_courses": event.changed_courses,
        "changed_groups": event.changed_groups,
        "changed_requirements": event.changed_requirements,
        "impact_summary": event.impact_summary,
        "recompute_plan": event.recompute_plan,
        "notification_plan": event.notification_plan,
        "enrollment_impacts": [
            {
                "id": item.pk,
                "enrollment_id": item.enrollment_id,
                "previous_revision_id": item.previous_revision_id,
                "previous_audit_run_id": item.previous_audit_run_id,
                "previous_audit_result_hash": item.previous_audit_result_hash,
                "impact_status": item.impact_status,
                "recompute_job_key": item.recompute_job_key,
                "recompute_requested_at": item.recompute_requested_at,
                "recomputed_audit_run_id": item.recomputed_audit_run_id,
                "requires_revision_decision": item.requires_revision_decision,
            }
            for item in impacts
        ],
    }


@transaction.atomic  # type: ignore[untyped-decorator]
def submit_proposal(
    actor: Any, proposal_id: UUID | str, *, expected_version: str, request: Any | None = None
) -> ChangeProposal:
    proposal = _proposal_queryset().select_for_update(of=("self",)).get(pk=proposal_id)
    _require_editor_access(actor, proposal)
    _require_version(proposal_version(proposal), expected_version)
    if proposal.status not in {
        ProposalStatus.DRAFT.value,
        ProposalStatus.REJECTED.value,
        ProposalStatus.WITHDRAWN.value,
    }:
        raise GovernanceError(
            "Only a draft proposal can enter review.", code="proposal_status_invalid"
        )
    proposal.status = ProposalStatus.IN_REVIEW.value
    proposal.candidate_revision.status = RevisionStatus.IN_REVIEW.value
    proposal.candidate_revision.save(update_fields=["status", "updated_at"])
    proposal.save(update_fields=["status", "updated_at"])
    record_audit_event(
        request,
        action="GOVERNANCE_PROPOSAL_SUBMITTED",
        actor=actor,
        object_type="ChangeProposal",
        object_id=proposal.pk,
        institution_id=proposal.candidate_revision.plan.program.faculty.campus.institution_id,
        metadata={"revision_id": str(proposal.candidate_revision_id)},
    )
    return proposal


def _review_transition(decision: str) -> tuple[str, str]:
    if decision == ReviewDecision.APPROVE.value:
        return ProposalStatus.APPROVED.value, RevisionStatus.APPROVED.value
    if decision == ReviewDecision.REQUEST_CHANGES.value:
        return ProposalStatus.DRAFT.value, RevisionStatus.DRAFT.value
    if decision == ReviewDecision.REJECT.value:
        return ProposalStatus.REJECTED.value, RevisionStatus.DRAFT.value
    raise GovernanceError("Unsupported review decision.", code="review_decision_invalid")


def _create_publication_event(
    *,
    proposal: ChangeProposal,
    publication: Publication,
    superseded_revision: CurriculumRevision | None,
    actor: Any,
) -> PublicationEvent:
    diff = proposal.semantic_diff if isinstance(proposal.semantic_diff, dict) else {}
    semantic_impact = _semantic_impact(diff)
    affected = _affected_enrollment_snapshot(superseded_revision)
    event_id = uuid4()
    now = timezone.now()
    jobs = [
        {
            "job_key": f"curriculum.audit.recompute:{event_id}:{row['enrollment'].pk}",
            "enrollment_id": str(row["enrollment"].pk),
            "previous_revision_id": str(superseded_revision.pk)
            if superseded_revision is not None
            else None,
            "target_revision_id": str(proposal.candidate_revision_id),
            "reason": "curriculum_revision_published",
            "requires_revision_decision": True,
        }
        for row in affected
    ]
    affected_audit_count = sum(1 for row in affected if row["audit_run"] is not None)
    event = PublicationEvent.objects.create(
        id=event_id,
        event_key=f"curriculum.revision.published:{publication.pk}",
        publication=publication,
        revision=publication.revision,
        superseded_revision=superseded_revision,
        created_by=actor if getattr(actor, "pk", None) else None,
        changed_courses=semantic_impact["courses"],
        changed_groups=semantic_impact["groups"],
        changed_requirements=semantic_impact["requirements"],
        impact_summary={
            "changed_courses": len(semantic_impact["courses"]),
            "changed_groups": len(semantic_impact["groups"]),
            "changed_requirements": len(semantic_impact["requirements"]),
            "changed_other": len(semantic_impact["other"]),
            "affected_enrollments": len(affected),
            "affected_audits": affected_audit_count,
            "old_audits_reproducible": True,
        },
        recompute_plan={
            "status": "QUEUED" if jobs else "NOT_REQUIRED",
            "dispatcher": "transactional_publication_outbox",
            "job_type": "degree_audit.recompute",
            "requires_revision_decision": True,
            "jobs": jobs,
        },
        notification_plan={
            "status": "QUEUED" if affected else "NOT_REQUIRED",
            "event_type": "notification.requested",
            "recipient_count": len(affected),
            "after_commit_only": True,
        },
    )
    impacts: list[PublicationImpact] = []
    for row in affected:
        enrollment = row["enrollment"]
        audit_run = row["audit_run"]
        job_key = f"curriculum.audit.recompute:{event.pk}:{enrollment.pk}"
        impact = PublicationImpact.objects.create(
            publication_event=event,
            enrollment=enrollment,
            previous_revision=superseded_revision,
            previous_audit_run=audit_run,
            previous_audit_result_hash=audit_run.result_hash if audit_run else "",
            changed_courses=semantic_impact["courses"],
            changed_groups=semantic_impact["groups"],
            changed_requirements=semantic_impact["requirements"],
            impact_status=PublicationImpactStatus.RECOMPUTE_QUEUED.value,
            recompute_job_key=job_key,
            recompute_requested_at=now,
            requires_revision_decision=True,
        )
        impacts.append(impact)
        NotificationOutbox.objects.create(
            publication_event=event,
            recipient=enrollment.student.user,
            event_type="notification.requested",
            dedupe_key=f"curriculum-publication:{event.pk}:{enrollment.pk}",
            payload={
                "publication_event_id": str(event.pk),
                "publication_id": str(publication.pk),
                "impact_id": str(impact.pk),
                "revision_id": str(publication.revision_id),
                "revision_code": publication.revision.revision_code,
                "superseded_revision_id": str(superseded_revision.pk)
                if superseded_revision is not None
                else None,
                "message_key": "curriculum.revision.published.impact_review",
            },
            status=NotificationDeliveryStatus.QUEUED.value,
            available_at=now,
        )
    record_audit_event(
        None,
        action="CURRICULUM_PUBLICATION_EVENT_RECORDED",
        actor=actor,
        object_type="PublicationEvent",
        object_id=event.pk,
        institution_id=publication.revision.plan.program.faculty.campus.institution_id,
        metadata={
            "publication_id": str(publication.pk),
            "revision_id": str(publication.revision_id),
            "superseded_revision_id": str(superseded_revision.pk)
            if superseded_revision is not None
            else None,
            "affected_enrollments": len(impacts),
            "affected_audits": affected_audit_count,
        },
    )
    return event


@transaction.atomic  # type: ignore[untyped-decorator]
def review_proposal(
    actor: Any,
    proposal_id: UUID | str,
    *,
    decision: str,
    comment: str,
    expected_version: str,
    request: Any | None = None,
) -> ChangeProposal:
    proposal = _proposal_queryset().select_for_update(of=("self",)).get(pk=proposal_id)
    _require_reviewer_access(actor, proposal)
    _require_version(proposal_version(proposal), expected_version)
    if decision == ReviewDecision.APPROVE.value and proposal.created_by_id == getattr(
        actor, "pk", None
    ):
        raise GovernanceError(
            "The submitter cannot approve the same proposal.", code="self_approval_forbidden"
        )
    if proposal.status not in {ProposalStatus.IN_REVIEW.value, ProposalStatus.APPROVED.value}:
        raise GovernanceError(
            "Only a proposal in review can receive a decision.", code="proposal_status_invalid"
        )
    if decision == ReviewDecision.APPROVE.value:
        pending = proposal.extraction_candidates.filter(
            status=ExtractionCandidateStatus.PENDING.value
        ).count()
        if pending:
            raise GovernanceError(
                f"{pending} extraction candidates still require a decision.",
                code="candidates_pending",
            )
        validation = proposal_validation(proposal)
        if not validation.get("ok"):
            raise GovernanceError(
                "The validation report contains publication blockers.", code="validation_failed"
            )
    next_proposal_status, next_revision_status = _review_transition(decision)
    Review.objects.create(
        proposal=proposal,
        reviewer=actor,
        decision=decision,
        comment=comment[:5000],
        proposal_version=proposal_version(proposal),
    )
    proposal.status = next_proposal_status
    proposal.candidate_revision.status = next_revision_status
    proposal.candidate_revision.save(update_fields=["status", "updated_at"])
    proposal.save(update_fields=["status", "updated_at"])
    record_audit_event(
        request,
        action="GOVERNANCE_PROPOSAL_REVIEWED",
        actor=actor,
        object_type="ChangeProposal",
        object_id=proposal.pk,
        institution_id=proposal.candidate_revision.plan.program.faculty.campus.institution_id,
        metadata={"decision": decision, "comment": comment[:500]},
    )
    return proposal


@measure_domain_timing("publication")
@transaction.atomic  # type: ignore[untyped-decorator]
def publish_proposal(
    actor: Any,
    proposal_id: UUID | str,
    *,
    confirmation: str,
    expected_version: str,
    request: Any | None = None,
) -> Publication:
    proposal = _proposal_queryset().select_for_update(of=("self",)).get(pk=proposal_id)
    if not _can_view_proposal(actor, proposal):
        raise GovernanceError(
            "The actor cannot view this editorial proposal.", code="governance_forbidden"
        )
    if proposal.status == ProposalStatus.APPLIED.value:
        try:
            return proposal.publication
        except Publication.DoesNotExist as exc:
            raise GovernanceError(
                "The applied proposal has no publication receipt.", code="publication_missing"
            ) from exc
    _require_reviewer_access(actor, proposal)
    _require_version(proposal_version(proposal), expected_version)
    if proposal.created_by_id == getattr(actor, "pk", None):
        raise GovernanceError(
            "The submitter cannot publish the same proposal.", code="self_approval_forbidden"
        )
    if proposal.status != ProposalStatus.APPROVED.value:
        raise GovernanceError(
            "Only an approved proposal can be published.", code="proposal_not_approved"
        )
    if not confirmation.strip():
        raise GovernanceError(
            "Explicit publication confirmation is required.",
            code="publication_confirmation_required",
        )
    pending = proposal.extraction_candidates.filter(
        status=ExtractionCandidateStatus.PENDING.value
    ).count()
    if pending:
        raise GovernanceError(
            f"{pending} extraction candidates still require a decision.", code="candidates_pending"
        )
    validation = proposal_validation(proposal)
    if not validation.get("ok"):
        raise GovernanceError(
            "The validation report contains publication blockers.", code="validation_failed"
        )
    candidate_revision = (
        CurriculumRevision.objects.select_for_update()
        .select_related("plan__program__faculty__campus")
        .get(pk=proposal.candidate_revision_id)
    )
    superseded_revision = (
        CurriculumRevision.objects.select_for_update()
        .filter(plan_id=candidate_revision.plan_id, status=RevisionStatus.PUBLISHED.value)
        .exclude(pk=candidate_revision.pk)
        .first()
    )
    if superseded_revision is not None and proposal.base_revision_id != superseded_revision.pk:
        raise GovernanceError(
            "The proposal is based on an older published revision; create a new correction proposal.",
            code="publication_base_stale",
        )
    try:
        revision = CurriculumRevisionService.publish(candidate_revision.pk, actor=actor)
    except RevisionTransitionError as error:
        raise GovernanceError(str(error), code="publication_revision_transition_invalid") from error
    now = timezone.now()
    publication = Publication.objects.create(
        proposal=proposal,
        revision=revision,
        published_by=actor,
        published_at=now,
        content_hash=revision.content_hash,
        source_set_hash=revision.source_set_hash,
        validation_report=validation,
        semantic_diff=proposal.semantic_diff,
        confirmation=confirmation[:5000],
    )
    proposal.status = ProposalStatus.APPLIED.value
    proposal.save(update_fields=["status", "updated_at"])
    record_audit_event(
        request,
        action="GOVERNANCE_PUBLICATION_CREATED",
        actor=actor,
        object_type="Publication",
        object_id=publication.pk,
        institution_id=revision.plan.program.faculty.campus.institution_id,
        metadata={
            "proposal_id": str(proposal.pk),
            "revision_id": str(revision.pk),
            "content_hash": revision.content_hash,
        },
    )
    _create_publication_event(
        proposal=proposal,
        publication=publication,
        superseded_revision=superseded_revision,
        actor=actor,
    )
    return publication


def _candidate_or_error(proposal_id: UUID | str, candidate_id: UUID | str) -> ExtractionCandidate:
    try:
        return (
            ExtractionCandidate.objects.select_related(
                "proposal__candidate_revision", "source_snapshot"
            )
            .prefetch_related("evidence__snapshot__document")
            .get(pk=candidate_id, proposal_id=proposal_id)
        )
    except ExtractionCandidate.DoesNotExist as exc:
        raise GovernanceError(
            "The extraction candidate was not found.", code="candidate_not_found"
        ) from exc


def _candidate_status(value: str) -> str:
    if value not in {item.value for item in ExtractionCandidateStatus}:
        raise GovernanceError("Unsupported candidate status.", code="candidate_status_invalid")
    return value


def _evidence_for_snapshot(snapshot_id: UUID, evidence_ids: Iterable[UUID]) -> list[Evidence]:
    requested = list(evidence_ids)
    evidence = list(Evidence.objects.filter(pk__in=requested, snapshot_id=snapshot_id))
    if len(evidence) != len(set(requested)):
        raise GovernanceError(
            "Evidence must belong to the candidate source snapshot.",
            code="evidence_source_mismatch",
        )
    return evidence


@transaction.atomic  # type: ignore[untyped-decorator]
def review_candidate(
    actor: Any,
    proposal_id: UUID | str,
    candidate_id: UUID | str,
    *,
    status: str,
    epistemic_status: str,
    note: str,
    evidence_ids: Iterable[UUID],
    expected_version: str,
    request: Any | None = None,
) -> ExtractionCandidate:
    candidate = _candidate_or_error(proposal_id, candidate_id)
    proposal = candidate.proposal
    _require_editor_access(actor, proposal)
    _require_version(candidate_version(candidate), expected_version)
    status = _candidate_status(status)
    evidence = _evidence_for_snapshot(candidate.source_snapshot_id, evidence_ids)
    if epistemic_status == EpistemicStatus.VERIFIED.value and not evidence:
        raise GovernanceError(
            "A VERIFIED candidate must have at least one evidence link.",
            code="verified_evidence_required",
        )
    if epistemic_status not in {item.value for item in EpistemicStatus}:
        raise GovernanceError("Unsupported epistemic status.", code="epistemic_status_invalid")
    candidate.status = status
    candidate.epistemic_status = epistemic_status
    candidate.note = note[:5000]
    candidate.reviewed_by = actor
    candidate.reviewed_at = timezone.now()
    candidate.save(
        update_fields=[
            "status",
            "epistemic_status",
            "note",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )
    candidate.evidence.set(evidence)
    record_audit_event(
        request,
        action="GOVERNANCE_CANDIDATE_REVIEWED",
        actor=actor,
        object_type="ExtractionCandidate",
        object_id=candidate.pk,
        institution_id=proposal.candidate_revision.plan.program.faculty.campus.institution_id,
        metadata={
            "proposal_id": str(proposal.pk),
            "status": status,
            "epistemic_status": epistemic_status,
            "evidence_count": len(evidence),
        },
    )
    return candidate


def _bulk_token(
    *,
    proposal: ChangeProposal,
    candidates: Iterable[ExtractionCandidate],
    status: str,
    epistemic_status: str,
    evidence_ids: Iterable[UUID],
) -> str:
    payload = {
        "proposal_id": str(proposal.pk),
        "proposal_version": proposal_version(proposal),
        "status": status,
        "epistemic_status": epistemic_status,
        "evidence_ids": sorted(str(item) for item in evidence_ids),
        "candidates": sorted((str(item.pk), candidate_version(item)) for item in candidates),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def preview_candidate_bulk(
    actor: Any,
    proposal_id: UUID | str,
    *,
    candidate_ids: Iterable[UUID],
    status: str,
    epistemic_status: str,
    evidence_ids: Iterable[UUID],
) -> dict[str, Any]:
    candidate_ids = list(candidate_ids)
    evidence_ids = list(evidence_ids)
    proposal = get_proposal(actor, proposal_id)
    _require_editor_access(actor, proposal)
    status = _candidate_status(status)
    candidates = list(
        ExtractionCandidate.objects.filter(
            proposal=proposal, pk__in=list(candidate_ids)
        ).select_related("source_snapshot")
    )
    if len(candidates) != len(set(candidate_ids)):
        raise GovernanceError(
            "Every requested candidate must belong to the proposal.", code="candidate_not_found"
        )
    evidence = (
        _evidence_for_snapshot(candidates[0].source_snapshot_id, evidence_ids) if candidates else []
    )
    blocked: list[dict[str, Any]] = []
    if epistemic_status == EpistemicStatus.VERIFIED.value and not evidence:
        blocked = [
            {"candidate_id": item.pk, "reason": "verified_evidence_required"} for item in candidates
        ]
    token = _bulk_token(
        proposal=proposal,
        candidates=candidates,
        status=status,
        epistemic_status=epistemic_status,
        evidence_ids=[item.pk for item in evidence],
    )
    return {
        "proposal_id": proposal.pk,
        "proposal_version": proposal_version(proposal),
        "preview_token": token,
        "total": len(candidates),
        "allowed": len(candidates) - len(blocked),
        "blocked": blocked,
        "candidate_versions": {str(item.pk): candidate_version(item) for item in candidates},
        "writes_performed": False,
    }


@transaction.atomic  # type: ignore[untyped-decorator]
def apply_candidate_bulk(
    actor: Any,
    proposal_id: UUID | str,
    *,
    candidate_ids: Iterable[UUID],
    status: str,
    epistemic_status: str,
    note: str,
    evidence_ids: Iterable[UUID],
    preview_token: str,
    expected_version: str,
    request: Any | None = None,
) -> list[ExtractionCandidate]:
    candidate_ids = list(candidate_ids)
    evidence_ids = list(evidence_ids)
    proposal = _proposal_queryset().select_for_update(of=("self",)).get(pk=proposal_id)
    _require_editor_access(actor, proposal)
    _require_version(proposal_version(proposal), expected_version)
    candidates = list(
        ExtractionCandidate.objects.select_for_update()
        .filter(proposal=proposal, pk__in=list(candidate_ids))
        .select_related("source_snapshot")
    )
    preview = preview_candidate_bulk(
        actor,
        proposal_id,
        candidate_ids=[item.pk for item in candidates],
        status=status,
        epistemic_status=epistemic_status,
        evidence_ids=evidence_ids,
    )
    if preview["preview_token"] != preview_token or preview["blocked"]:
        raise GovernanceError(
            "The bulk preview is stale or contains blocked candidates.", code="bulk_preview_invalid"
        )
    evidence = (
        _evidence_for_snapshot(candidates[0].source_snapshot_id, evidence_ids) if candidates else []
    )
    for candidate in candidates:
        candidate.status = _candidate_status(status)
        candidate.epistemic_status = epistemic_status
        candidate.note = note[:5000]
        candidate.reviewed_by = actor
        candidate.reviewed_at = timezone.now()
        candidate.save(
            update_fields=[
                "status",
                "epistemic_status",
                "note",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ]
        )
        candidate.evidence.set(evidence)
        record_audit_event(
            request,
            action="GOVERNANCE_CANDIDATE_BULK_REVIEWED",
            actor=actor,
            object_type="ExtractionCandidate",
            object_id=candidate.pk,
            institution_id=proposal.candidate_revision.plan.program.faculty.campus.institution_id,
            metadata={"proposal_id": str(proposal.pk), "preview_token": preview_token},
        )
    return candidates


@transaction.atomic  # type: ignore[untyped-decorator]
def link_requirement_evidence(
    actor: Any,
    requirement_id: UUID | str,
    *,
    evidence_ids: Iterable[UUID],
    expected_version: str,
    request: Any | None = None,
) -> Requirement:
    evidence_ids = list(evidence_ids)
    try:
        requirement = (
            Requirement.objects.select_related("revision__plan__program__faculty__campus")
            .prefetch_related("evidence")
            .select_for_update()
            .get(pk=requirement_id)
        )
    except Requirement.DoesNotExist as exc:
        raise GovernanceError(
            "The requirement was not found.", code="requirement_not_found"
        ) from exc
    if not can_edit_revision(actor, requirement.revision):
        raise GovernanceError(
            "The actor cannot edit this draft requirement.", code="governance_forbidden"
        )
    _require_version(requirement.updated_at.isoformat(), expected_version)
    evidence = list(Evidence.objects.filter(pk__in=list(evidence_ids)))
    if len(evidence) != len(set(evidence_ids)):
        raise GovernanceError(
            "One or more evidence records were not found.", code="evidence_not_found"
        )
    requirement.evidence.set(evidence)
    requirement.updated_at = timezone.now()
    requirement.save(update_fields=["updated_at"])
    record_audit_event(
        request,
        action="GOVERNANCE_REQUIREMENT_EVIDENCE_LINKED",
        actor=actor,
        object_type="Requirement",
        object_id=requirement.pk,
        institution_id=requirement.revision.plan.program.faculty.campus.institution_id,
        metadata={"evidence_count": len(evidence)},
    )
    return requirement
