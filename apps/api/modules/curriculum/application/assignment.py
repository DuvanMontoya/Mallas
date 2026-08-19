from __future__ import annotations

import hashlib
from datetime import date
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from domain.curriculum_assignment import (
    AssignmentInput,
    AssignmentPolicyCandidate,
    resolve_curriculum_assignment,
)
from domain.enums import CurriculumAssignmentPolicyStatus, EpistemicStatus, UserRole
from domain.errors import PublishedAssignmentPolicyImmutableError
from domain.revision import canonical_content_hash
from modules.curriculum.models import CurriculumAssignmentPolicy
from modules.identity.application.audit import record_audit_event
from modules.identity.application.authorization import active_role_assignments


class CurriculumAssignmentPolicyError(ValueError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _policy_candidate(policy: CurriculumAssignmentPolicy) -> AssignmentPolicyCandidate:
    links = tuple(policy.evidence_links.all())
    return AssignmentPolicyCandidate(
        policy_id=str(policy.pk),
        policy_code=policy.policy_code,
        version=policy.version,
        program_id=str(policy.program_id),
        plan_id=str(policy.plan_id),
        revision_id=str(policy.revision_basis_id),
        context=policy.context,
        admission_from=policy.admission_from,
        admission_to=policy.admission_to,
        cohort_code=policy.cohort_code,
        previous_plan_id=str(policy.previous_plan_id) if policy.previous_plan_id else None,
        effective_from=policy.effective_from,
        effective_to=policy.effective_to,
        supersedes_id=str(policy.supersedes_id) if policy.supersedes_id else None,
        status=policy.status,
        epistemic_status=policy.epistemic_status,
        content_hash=policy.content_hash,
        source_set_hash=policy.source_set_hash,
        evidence_ids=tuple(str(item.evidence_id) for item in links),
        revision_status=policy.revision_basis.status,
        revision_content_hash=policy.revision_basis.content_hash,
        revision_source_set_hash=policy.revision_basis.source_set_hash,
        evidence_sealed=bool(links)
        and all(
            link.sealed_snapshot_sha256
            and link.sealed_snapshot_id
            and link.sealed_storage_key_hash
            and link.sealed_excerpt_hash
            and link.sealed_locator_hash
            for link in links
        ),
        allow_retired_revision=policy.allow_retired_revision,
    )


def _lock_assignment_scope(program_id: UUID, context: str) -> None:
    if connection.vendor != "postgresql" or not connection.in_atomic_block:
        return
    raw = hashlib.blake2b(
        f"curriculum-assignment:{program_id}:{context}".encode(), digest_size=8
    ).digest()
    lock_id = int.from_bytes(raw, byteorder="big", signed=True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])


def resolve_assignment_preview(
    *,
    program_id: UUID,
    admission_date: date,
    context: str,
    cohort_code: str = "",
    previous_plan_id: UUID | None = None,
    admission_source_snapshot_id: UUID | None = None,
    admission_source_sha256: str | None = None,
    admission_verification_method: str | None = None,
    admission_record_reference_hash: str | None = None,
) -> dict[str, Any]:
    _lock_assignment_scope(program_id, context)
    policies = (
        CurriculumAssignmentPolicy.objects.filter(
            program_id=program_id,
            context=context,
            status__in=(
                CurriculumAssignmentPolicyStatus.PUBLISHED.value,
                CurriculumAssignmentPolicyStatus.SUPERSEDED.value,
            ),
        )
        .select_related("plan", "revision_basis", "previous_plan")
        .prefetch_related("evidence_links")
    )
    value = AssignmentInput(
        program_id=str(program_id),
        admission_date=admission_date,
        context=context,
        cohort_code=cohort_code.strip(),
        previous_plan_id=str(previous_plan_id) if previous_plan_id else None,
        admission_source_snapshot_id=(
            str(admission_source_snapshot_id) if admission_source_snapshot_id else None
        ),
        admission_source_sha256=admission_source_sha256,
        admission_verification_method=admission_verification_method,
        admission_record_reference_hash=admission_record_reference_hash,
    )
    decision = resolve_curriculum_assignment(
        value, tuple(_policy_candidate(policy) for policy in policies)
    )
    return decision.to_dict(value)


@transaction.atomic  # type: ignore[untyped-decorator]
def publish_assignment_policy(
    policy_id: UUID, *, actor: Any, request: Any | None = None
) -> CurriculumAssignmentPolicy:
    policy = (
        CurriculumAssignmentPolicy.objects.select_for_update()
        .select_related(
            "program__faculty__campus", "plan", "revision_basis", "previous_plan"
        )
        .get(pk=policy_id)
    )
    _lock_assignment_scope(policy.program_id, policy.context)
    authorized = getattr(actor, "is_superuser", False) or any(
        assignment.role in {UserRole.ADMIN.value, UserRole.REVIEWER.value}
        and assignment.institution_id
        in (None, policy.program.faculty.campus.institution_id)
        and assignment.program_id in (None, policy.program_id)
        for assignment in active_role_assignments(actor)
    )
    if not authorized:
        raise CurriculumAssignmentPolicyError(
            "You cannot publish assignment policies for this program.",
            code="assignment_policy_forbidden",
        )
    if settings.PRIVILEGED_MFA_REQUIRED and not getattr(
        actor, "_privileged_mfa_verified", False
    ):
        raise CurriculumAssignmentPolicyError(
            "Privileged authentication is required to publish an assignment policy.",
            code="assignment_policy_step_up_required",
        )
    if policy.status not in {
        CurriculumAssignmentPolicyStatus.DRAFT.value,
        CurriculumAssignmentPolicyStatus.IN_REVIEW.value,
    }:
        raise CurriculumAssignmentPolicyError(
            "Only a draft or reviewed assignment policy can be published.",
            code="assignment_policy_transition_invalid",
        )
    if policy.prepared_by_id is None or policy.prepared_by_id == actor.pk:
        raise CurriculumAssignmentPolicyError(
            "Policy publication requires an approver different from the preparer.",
            code="assignment_policy_separation_required",
        )
    links = list(
        policy.evidence_links.select_for_update()
        .select_related("evidence__snapshot")
        .order_by("evidence_id")
    )
    if not links:
        raise CurriculumAssignmentPolicyError(
            "An assignment policy requires archived evidence before publication.",
            code="assignment_policy_evidence_required",
        )
    if policy.epistemic_status == EpistemicStatus.VERIFIED.value:
        if policy.normative_published_on is None:
            raise CurriculumAssignmentPolicyError(
                "A verified assignment policy requires the normative publication date.",
                code="assignment_policy_publication_date_required",
            )
        if policy.admission_from is None and not policy.cohort_code:
            raise CurriculumAssignmentPolicyError(
                "A verified policy requires an admission boundary or exact cohort.",
                code="assignment_policy_scope_required",
            )
    if policy.revision_basis.status not in {
        "PUBLISHED",
        "SUPERSEDED",
        "RETIRED",
    } or not (policy.revision_basis.content_hash and policy.revision_basis.source_set_hash):
        raise CurriculumAssignmentPolicyError(
            "The target revision must be immutable and fully hashed before policy publication.",
            code="assignment_policy_revision_not_publishable",
        )
    if policy.revision_basis.status == "RETIRED" and not policy.allow_retired_revision:
        raise CurriculumAssignmentPolicyError(
            "A retired revision requires an explicit historical-assignment permission.",
            code="assignment_policy_retired_revision_not_allowed",
        )
    for link in links:
        link.sealed_snapshot_sha256 = link.evidence.snapshot.sha256
        link.sealed_snapshot_id = link.evidence.snapshot_id
        link.sealed_storage_key_hash = canonical_content_hash(
            {"storage_key": link.evidence.snapshot.storage_key}
        )
        link.sealed_excerpt_hash = link.evidence.excerpt_hash
        link.sealed_locator_hash = canonical_content_hash(
            {
                "page": link.evidence.page,
                "section": link.evidence.section,
                "line_locator": link.evidence.line_locator,
            }
        )
        link.save(
            update_fields=(
                "sealed_snapshot_sha256",
                "sealed_snapshot_id",
                "sealed_storage_key_hash",
                "sealed_excerpt_hash",
                "sealed_locator_hash",
                "updated_at",
            )
        )
    source_payload = [
        {
            "evidence_id": str(link.evidence_id),
            "snapshot_sha256": link.sealed_snapshot_sha256,
            "snapshot_id": str(link.sealed_snapshot_id),
            "storage_key_hash": link.sealed_storage_key_hash,
            "excerpt_hash": link.sealed_excerpt_hash,
            "locator_hash": link.sealed_locator_hash,
            "purpose": link.purpose,
        }
        for link in links
    ]
    policy.source_set_hash = canonical_content_hash({"evidence": source_payload})
    policy.content_hash = canonical_content_hash(
        {
            "policy_code": policy.policy_code,
            "version": policy.version,
            "program_id": str(policy.program_id),
            "plan_id": str(policy.plan_id),
            "revision_basis_id": str(policy.revision_basis_id),
            "context": policy.context,
            "admission_from": policy.admission_from.isoformat()
            if policy.admission_from
            else None,
            "admission_to": policy.admission_to.isoformat() if policy.admission_to else None,
            "cohort_code": policy.cohort_code,
            "previous_plan_id": str(policy.previous_plan_id)
            if policy.previous_plan_id
            else None,
            "normative_published_on": policy.normative_published_on.isoformat()
            if policy.normative_published_on
            else None,
            "effective_from": policy.effective_from.isoformat()
            if policy.effective_from
            else None,
            "effective_to": policy.effective_to.isoformat() if policy.effective_to else None,
            "allow_retired_revision": policy.allow_retired_revision,
            "epistemic_status": policy.epistemic_status,
            "source_set_hash": policy.source_set_hash,
            "revision_status": policy.revision_basis.status,
            "revision_content_hash": policy.revision_basis.content_hash,
            "revision_source_set_hash": policy.revision_basis.source_set_hash,
            "supersedes_id": str(policy.supersedes_id) if policy.supersedes_id else None,
            "metadata": policy.metadata,
            "prepared_by_id": policy.prepared_by_id,
            "approved_by_id": actor.pk,
        }
    )
    policy.published_at = timezone.now()
    policy.approved_by = actor
    policy.status = CurriculumAssignmentPolicyStatus.PUBLISHED.value
    policy._publication_service_authorized = True
    try:
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.assignment_policy_publication = 'allowed'")
        policy.save(
            update_fields=(
                "source_set_hash",
                "content_hash",
                "published_at",
                "approved_by",
                "status",
                "updated_at",
            )
        )
    except PublishedAssignmentPolicyImmutableError as error:
        raise CurriculumAssignmentPolicyError(
            str(error), code="assignment_policy_immutable"
        ) from error
    record_audit_event(
        request,
        action="CURRICULUM_ASSIGNMENT_POLICY_PUBLISHED",
        actor=actor,
        object_type="CurriculumAssignmentPolicy",
        object_id=policy.pk,
        institution_id=policy.program.faculty.campus.institution_id,
        metadata={
            "program_id": str(policy.program_id),
            "plan_id": str(policy.plan_id),
            "revision_id": str(policy.revision_basis_id),
            "policy_code": policy.policy_code,
            "version": policy.version,
            "content_hash": policy.content_hash,
            "source_set_hash": policy.source_set_hash,
        },
    )
    return policy
