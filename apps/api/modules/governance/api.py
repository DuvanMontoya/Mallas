from __future__ import annotations

from datetime import date, datetime
from typing import Any, NoReturn
from uuid import UUID

from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from ninja import Header, Router, Schema
from ninja.security import django_auth

from domain.enums import UserRole
from modules.common.api import raise_problem, require_if_match, with_problem_responses
from modules.curriculum.application.assignment import (
    CurriculumAssignmentPolicyError,
    publish_assignment_policy,
    submit_assignment_policy,
)
from modules.curriculum.models import CurriculumAssignmentPolicy
from modules.identity.application.authorization import active_role_assignments

from .application.services import (
    GovernanceError,
    apply_candidate_bulk,
    get_document,
    get_proposal_detail,
    get_publication_impact,
    get_snapshot,
    link_requirement_evidence,
    list_source_inbox,
    preview_candidate_bulk,
    publish_proposal,
    review_candidate,
    review_proposal,
    submit_proposal,
)

router = Router(tags=["Curriculum governance"])


class AssignmentPolicyPublicationView(Schema):
    id: UUID
    status: str
    policy_code: str
    version: int
    content_hash: str
    source_set_hash: str
    prepared_by_id: int
    approved_by_id: int


class AssignmentPolicyEvidenceReviewView(Schema):
    purpose: str
    source_title: str
    locator: str
    excerpt: str
    excerpt_hash: str
    snapshot_sha256: str


class AssignmentPolicySummaryView(Schema):
    id: UUID
    policy_code: str
    version: int
    program_name: str
    plan_code: str
    revision_code: str
    revision_status: str
    revision_content_hash: str
    revision_source_set_hash: str
    context: str
    epistemic_status: str
    status: str
    prepared_by_id: int | None
    approved_by_id: int | None
    admission_from: date | None
    admission_to: date | None
    cohort_code: str
    previous_plan_code: str | None
    normative_published_on: date | None
    effective_from: date | None
    effective_to: date | None
    allow_retired_revision: bool
    review_content_hash: str | None
    source_set_hash: str | None
    evidence: list[AssignmentPolicyEvidenceReviewView]


class AssignmentPolicyCollectionView(Schema):
    items: list[AssignmentPolicySummaryView]


def _assignment_policy_summary(policy: CurriculumAssignmentPolicy) -> dict[str, Any]:
    return {
        "id": policy.pk,
        "policy_code": policy.policy_code,
        "version": policy.version,
        "program_name": policy.program.name,
        "plan_code": policy.plan.code,
        "revision_code": policy.revision_basis.revision_code,
        "revision_status": policy.revision_basis.status,
        "revision_content_hash": policy.revision_basis.content_hash,
        "revision_source_set_hash": policy.revision_basis.source_set_hash,
        "context": policy.context,
        "epistemic_status": policy.epistemic_status,
        "status": policy.status,
        "prepared_by_id": policy.prepared_by_id,
        "approved_by_id": policy.approved_by_id,
        "admission_from": policy.admission_from,
        "admission_to": policy.admission_to,
        "cohort_code": policy.cohort_code,
        "previous_plan_code": policy.previous_plan.code if policy.previous_plan_id else None,
        "normative_published_on": policy.normative_published_on,
        "effective_from": policy.effective_from,
        "effective_to": policy.effective_to,
        "allow_retired_revision": policy.allow_retired_revision,
        "review_content_hash": policy.content_hash or None,
        "source_set_hash": policy.source_set_hash or None,
        "evidence": [
            {
                "purpose": link.purpose,
                "source_title": link.sealed_source_title,
                "locator": link.sealed_locator,
                "excerpt": link.sealed_excerpt,
                "excerpt_hash": link.sealed_excerpt_hash,
                "snapshot_sha256": link.sealed_snapshot_sha256,
            }
            for link in policy.evidence_links.all()
        ],
    }


@router.get(
    "/governance/assignment-policies",
    auth=django_auth,
    response=with_problem_responses(AssignmentPolicyCollectionView),
)
def assignment_policies(request: HttpRequest, response: HttpResponse) -> dict[str, Any]:
    assignments = [
        assignment
        for assignment in active_role_assignments(request.auth)
        if assignment.role in {UserRole.EDITOR.value, UserRole.REVIEWER.value, UserRole.ADMIN.value}
    ]
    if not assignments and not getattr(request.auth, "is_superuser", False):
        raise_problem(
            status=403,
            code="ASSIGNMENT_POLICY_FORBIDDEN",
            title="Assignment policy access denied",
            detail="An active governance role is required.",
        )
    query = CurriculumAssignmentPolicy.objects.select_related(
        "program", "plan", "revision_basis", "previous_plan"
    ).prefetch_related("evidence_links")
    if not getattr(request.auth, "is_superuser", False):
        scope = Q(pk__in=[])
        for assignment in assignments:
            if assignment.program_id:
                scope |= Q(program_id=assignment.program_id)
            elif assignment.institution_id:
                scope |= Q(program__faculty__campus__institution_id=assignment.institution_id)
            else:
                scope = Q()
                break
        query = query.filter(scope)
    response["Cache-Control"] = "private, no-store"
    return {
        "items": [
            _assignment_policy_summary(policy)
            for policy in query.order_by("program__name", "policy_code", "-version")[:500]
        ]
    }


@router.post(
    "/governance/assignment-policies/{policy_id}/submit",
    auth=django_auth,
    response=with_problem_responses(AssignmentPolicySummaryView),
)
def assignment_policy_submit(
    request: HttpRequest, response: HttpResponse, policy_id: UUID
) -> dict[str, Any]:
    try:
        policy = submit_assignment_policy(policy_id, actor=request.auth, request=request)
    except CurriculumAssignmentPolicy.DoesNotExist:
        raise_problem(
            status=404,
            code="ASSIGNMENT_POLICY_NOT_FOUND",
            title="Assignment policy not found",
            detail="The assignment policy does not exist or is outside the governed scope.",
        )
    except CurriculumAssignmentPolicyError as error:
        raise_problem(
            status=403 if error.code == "assignment_policy_forbidden" else 409,
            code=error.code.upper(),
            title="Assignment policy submission failed",
            detail=str(error),
        )
    response["Cache-Control"] = "private, no-store"
    return _assignment_policy_summary(policy)


@router.post(
    "/governance/assignment-policies/{policy_id}/publish",
    auth=django_auth,
    response=with_problem_responses(AssignmentPolicyPublicationView),
)
def assignment_policy_publish(
    request: HttpRequest, response: HttpResponse, policy_id: UUID
) -> dict[str, Any]:
    try:
        policy = publish_assignment_policy(policy_id, actor=request.auth, request=request)
    except CurriculumAssignmentPolicy.DoesNotExist:
        raise_problem(
            status=404,
            code="ASSIGNMENT_POLICY_NOT_FOUND",
            title="Assignment policy not found",
            detail="The assignment policy does not exist or is outside the governed scope.",
        )
    except CurriculumAssignmentPolicyError as error:
        status = (
            403
            if error.code
            in {
                "assignment_policy_forbidden",
                "assignment_policy_step_up_required",
            }
            else 409
        )
        raise_problem(
            status=status,
            code=error.code.upper(),
            title="Assignment policy publication failed",
            detail=str(error),
        )
    response["Cache-Control"] = "private, no-store"
    return {
        "id": policy.pk,
        "status": policy.status,
        "policy_code": policy.policy_code,
        "version": policy.version,
        "content_hash": policy.content_hash,
        "source_set_hash": policy.source_set_hash,
        "prepared_by_id": policy.prepared_by_id,
        "approved_by_id": policy.approved_by_id,
    }


class SourceDocumentView(Schema):
    id: UUID
    issuer: str
    document_type: str
    number: str
    year: int
    title: str
    publication_date: date | None
    canonical_url: str | None
    status: str
    metadata: dict[str, Any]
    snapshot_count: int
    version: str


class SourceSnapshotView(Schema):
    id: UUID
    document_id: UUID
    document_title: str
    captured_at: datetime
    sha256: str
    mime_type: str
    storage_key: str
    source_url: str | None
    metadata: dict[str, Any]
    evidence_count: int
    version: str


class ProposalSummaryView(Schema):
    id: UUID
    proposal_key: str
    title: str
    status: str
    base_revision_id: UUID | None
    candidate_revision_id: UUID
    candidate_revision_code: str
    source_snapshot_id: UUID
    source_title: str
    content_fingerprint: str
    semantic_has_changes: bool
    created_by: str | None
    updated_at: datetime
    version: str
    pending_candidates: int


class SourceInboxView(Schema):
    documents: list[SourceDocumentView]
    snapshots: list[SourceSnapshotView]
    proposals: list[ProposalSummaryView]
    workflow: list[str]


class GovernanceEvidenceView(Schema):
    id: UUID
    reference: str
    snapshot_id: UUID
    snapshot_sha256: str
    locator: str
    page: int | None
    section: str
    excerpt: str
    annotation: str
    source_title: str
    source_url: str | None


class SourceDocumentDetailView(SourceDocumentView):
    snapshots: list[SourceSnapshotView]


class SourceSnapshotDetailView(SourceSnapshotView):
    document: SourceDocumentView
    evidence: list[GovernanceEvidenceView]
    archived_content: dict[str, Any]


class RevisionView(Schema):
    id: UUID
    plan_code: str
    revision_code: str
    status: str
    effective_from: date
    effective_to: date | None
    total_required_credits: int
    source_set_hash: str
    content_hash: str
    published_at: datetime | None
    version: str


class GovernanceRequirementView(Schema):
    id: UUID
    code: str
    owner_type: str
    owner_id: UUID
    purpose: str
    ast: dict[str, Any]
    ast_schema_version: str
    ast_hash: str
    epistemic_status: str
    explanation_key: str
    human_explanation: str
    metadata: dict[str, Any]
    evidence: list[GovernanceEvidenceView]
    version: str


class GovernanceCandidateView(Schema):
    id: UUID
    entity: str
    entity_key: str
    operation: str
    before: Any
    after: Any
    status: str
    epistemic_status: str
    evidence: list[GovernanceEvidenceView]
    reviewed_by: str | None
    reviewed_at: datetime | None
    note: str
    version: str


class ValidationReportView(Schema):
    ok: bool
    errors: list[str]
    warnings: list[str]
    unknowns: list[dict[str, Any]]
    counts: dict[str, int]
    totals: dict[str, int]
    verified_rules_without_evidence: list[str] = []


class ImpactAnalysisView(Schema):
    audits_affected: int
    students_potentially_affected: int
    affected_enrollment_ids: list[UUID]
    affected_audit_ids: list[UUID]
    changed_semantic_items: int
    changed_courses: list[dict[str, Any]]
    changed_groups: list[dict[str, Any]]
    changed_requirements: list[dict[str, Any]]
    new_unknowns: int
    cycles_detected: int
    totals_inconsistent: bool
    publish_blockers: list[str]


class ProposalDetailView(ProposalSummaryView):
    rationale: str
    base_revision: RevisionView | None
    candidate_revision: RevisionView
    source_snapshot: SourceSnapshotView
    semantic_diff: dict[str, Any]
    validation_report: ValidationReportView
    impact_analysis: ImpactAnalysisView
    requirements: list[GovernanceRequirementView]
    candidates: list[GovernanceCandidateView]
    reviews: list[dict[str, Any]]
    publication: dict[str, Any] | None
    audit_events: list[dict[str, Any]]


class DocumentDetailEnvelope(Schema):
    item: SourceDocumentDetailView


class SnapshotDetailEnvelope(Schema):
    item: SourceSnapshotDetailView


class SubmitPayload(Schema):
    comment: str = ""


class ReviewPayload(Schema):
    decision: str
    comment: str = ""


class PublishPayload(Schema):
    confirmation: str


class CandidateReviewPayload(Schema):
    status: str
    epistemic_status: str
    note: str = ""
    evidence_ids: list[UUID] = []


class EvidenceLinkPayload(Schema):
    evidence_ids: list[UUID] = []


class BulkCandidatePayload(CandidateReviewPayload):
    candidate_ids: list[UUID]
    preview_token: str | None = None


class BulkPreviewView(Schema):
    proposal_id: UUID
    proposal_version: str
    preview_token: str
    total: int
    allowed: int
    blocked: list[dict[str, Any]]
    candidate_versions: dict[str, str]
    writes_performed: bool


class CandidateEnvelope(Schema):
    item: GovernanceCandidateView


class RequirementEnvelope(Schema):
    item: GovernanceRequirementView


class PublicationImpactView(Schema):
    publication_id: UUID
    event: dict[str, Any]


def _error(error: GovernanceError) -> NoReturn:
    status = (
        403
        if error.code in {"governance_forbidden", "governance_reviewer_required"}
        else 404
        if error.code.endswith("_not_found")
        else 428
        if error.code == "precondition_required"
        else 409
        if error.code
        in {
            "governance_concurrency_conflict",
            "self_approval_forbidden",
            "proposal_status_invalid",
            "proposal_not_approved",
            "candidates_pending",
            "validation_failed",
            "bulk_preview_invalid",
            "publication_missing",
            "publication_base_stale",
            "publication_revision_transition_invalid",
            "publication_event_missing",
        }
        else 422
    )
    raise_problem(
        status=status,
        code=error.code.upper(),
        title="Governance operation cannot be completed",
        detail=str(error),
    )


def _set_etag(response: HttpResponse, version: str) -> None:
    response["ETag"] = f'"{version}"'


@router.get("/governance/inbox", auth=django_auth, response=with_problem_responses(SourceInboxView))
def source_inbox(request: HttpRequest) -> dict[str, Any]:
    try:
        return list_source_inbox(request.auth)
    except GovernanceError as error:
        _error(error)


@router.get(
    "/governance/documents/{document_id}",
    auth=django_auth,
    response=with_problem_responses(SourceDocumentDetailView),
)
def document_detail(request: HttpRequest, document_id: UUID) -> dict[str, Any]:
    try:
        return get_document(request.auth, document_id)
    except GovernanceError as error:
        _error(error)


@router.get(
    "/governance/snapshots/{snapshot_id}",
    auth=django_auth,
    response=with_problem_responses(SourceSnapshotDetailView),
)
def snapshot_detail(request: HttpRequest, snapshot_id: UUID) -> dict[str, Any]:
    try:
        return get_snapshot(request.auth, snapshot_id)
    except GovernanceError as error:
        _error(error)


@router.get(
    "/governance/proposals/{proposal_id}",
    auth=django_auth,
    response=with_problem_responses(ProposalDetailView),
)
def proposal_detail(
    request: HttpRequest, response: HttpResponse, proposal_id: UUID
) -> dict[str, Any]:
    try:
        result = get_proposal_detail(request.auth, proposal_id)
    except GovernanceError as error:
        _error(error)
    _set_etag(response, str(result["version"]))
    return result


@router.post(
    "/governance/proposals/{proposal_id}/submit",
    auth=django_auth,
    response=with_problem_responses(ProposalDetailView),
)
def submit(
    request: HttpRequest,
    response: HttpResponse,
    proposal_id: UUID,
    payload: SubmitPayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        proposal = submit_proposal(
            request.auth, proposal_id, expected_version=require_if_match(if_match), request=request
        )
        result = get_proposal_detail(request.auth, proposal.pk)
    except GovernanceError as error:
        _error(error)
    _set_etag(response, str(result["version"]))
    return result


@router.post(
    "/governance/proposals/{proposal_id}/review",
    auth=django_auth,
    response=with_problem_responses(ProposalDetailView),
)
def review(
    request: HttpRequest,
    response: HttpResponse,
    proposal_id: UUID,
    payload: ReviewPayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        review_proposal(
            request.auth,
            proposal_id,
            decision=payload.decision,
            comment=payload.comment,
            expected_version=require_if_match(if_match),
            request=request,
        )
        result = get_proposal_detail(request.auth, proposal_id)
    except GovernanceError as error:
        _error(error)
    _set_etag(response, str(result["version"]))
    return result


@router.post(
    "/governance/proposals/{proposal_id}/publish",
    auth=django_auth,
    response=with_problem_responses(ProposalDetailView),
)
def publish(
    request: HttpRequest,
    response: HttpResponse,
    proposal_id: UUID,
    payload: PublishPayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        publish_proposal(
            request.auth,
            proposal_id,
            confirmation=payload.confirmation,
            expected_version=require_if_match(if_match),
            request=request,
        )
        result = get_proposal_detail(request.auth, proposal_id)
    except GovernanceError as error:
        _error(error)
    _set_etag(response, str(result["version"]))
    return result


@router.get(
    "/governance/publications/{publication_id}/impact",
    auth=django_auth,
    response=with_problem_responses(PublicationImpactView),
)
def publication_impact(request: HttpRequest, publication_id: UUID) -> dict[str, Any]:
    try:
        return get_publication_impact(request.auth, publication_id)
    except GovernanceError as error:
        _error(error)


@router.post(
    "/governance/proposals/{proposal_id}/candidates/{candidate_id}/review",
    auth=django_auth,
    response=with_problem_responses(GovernanceCandidateView),
)
def candidate_review(
    request: HttpRequest,
    response: HttpResponse,
    proposal_id: UUID,
    candidate_id: UUID,
    payload: CandidateReviewPayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        candidate = review_candidate(
            request.auth,
            proposal_id,
            candidate_id,
            status=payload.status,
            epistemic_status=payload.epistemic_status,
            note=payload.note,
            evidence_ids=payload.evidence_ids,
            expected_version=require_if_match(if_match),
            request=request,
        )
        detail = get_proposal_detail(request.auth, proposal_id)
        candidate_view = next(item for item in detail["candidates"] if item["id"] == candidate.pk)
    except GovernanceError as error:
        _error(error)
    _set_etag(response, str(candidate_view["version"]))
    return candidate_view


@router.post(
    "/governance/proposals/{proposal_id}/candidates/bulk-preview",
    auth=django_auth,
    response=with_problem_responses(BulkPreviewView),
)
def candidate_bulk_preview(
    request: HttpRequest, proposal_id: UUID, payload: BulkCandidatePayload
) -> dict[str, Any]:
    try:
        return preview_candidate_bulk(
            request.auth,
            proposal_id,
            candidate_ids=payload.candidate_ids,
            status=payload.status,
            epistemic_status=payload.epistemic_status,
            evidence_ids=payload.evidence_ids,
        )
    except GovernanceError as error:
        _error(error)


@router.post(
    "/governance/proposals/{proposal_id}/candidates/bulk-review",
    auth=django_auth,
    response=with_problem_responses(ProposalDetailView),
)
def candidate_bulk_review(
    request: HttpRequest,
    response: HttpResponse,
    proposal_id: UUID,
    payload: BulkCandidatePayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    if payload.preview_token is None:
        raise_problem(
            status=428,
            code="BULK_PREVIEW_REQUIRED",
            title="Bulk preview required",
            detail="Preview the bulk operation before applying it.",
        )
    try:
        apply_candidate_bulk(
            request.auth,
            proposal_id,
            candidate_ids=payload.candidate_ids,
            status=payload.status,
            epistemic_status=payload.epistemic_status,
            note=payload.note,
            evidence_ids=payload.evidence_ids,
            preview_token=payload.preview_token,
            expected_version=require_if_match(if_match),
            request=request,
        )
        result = get_proposal_detail(request.auth, proposal_id)
    except GovernanceError as error:
        _error(error)
    _set_etag(response, str(result["version"]))
    return result


@router.post(
    "/governance/requirements/{requirement_id}/evidence",
    auth=django_auth,
    response=with_problem_responses(GovernanceRequirementView),
)
def requirement_evidence(
    request: HttpRequest,
    response: HttpResponse,
    requirement_id: UUID,
    payload: EvidenceLinkPayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        requirement = link_requirement_evidence(
            request.auth,
            requirement_id,
            evidence_ids=payload.evidence_ids,
            expected_version=require_if_match(if_match),
            request=request,
        )
        detail = (
            get_proposal_detail(
                request.auth,
                requirement.revision.change_proposals_as_candidate.order_by("-updated_at")
                .values_list("pk", flat=True)
                .first(),
            )
            if requirement.revision.change_proposals_as_candidate.exists()
            else None
        )
        result = (
            next(item for item in detail["requirements"] if item["id"] == requirement.pk)
            if detail
            else {
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
                "human_explanation": "La regla fue actualizada; recarga el inspector para ver la explicación.",
                "metadata": requirement.metadata,
                "evidence": [],
                "version": requirement.updated_at.isoformat(),
            }
        )
    except GovernanceError as error:
        _error(error)
    _set_etag(response, str(result["version"]))
    return result
