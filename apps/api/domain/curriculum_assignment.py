from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from domain.enums import (
    AdmissionFactVerificationMethod,
    CurriculumAssignmentDecisionStatus,
    CurriculumAssignmentPolicyStatus,
    EpistemicStatus,
)
from domain.revision import canonical_content_hash

RESOLVER_VERSION = "1.0.0"


class AssignmentReason(StrEnum):
    EXACT_VERIFIED_POLICY = "EXACT_VERIFIED_POLICY"
    NO_APPLICABLE_POLICY = "NO_APPLICABLE_POLICY"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    MULTIPLE_APPLICABLE_POLICIES = "MULTIPLE_APPLICABLE_POLICIES"
    ADMISSION_FACT_UNVERIFIED = "ADMISSION_FACT_UNVERIFIED"


@dataclass(frozen=True, slots=True)
class AssignmentInput:
    program_id: str
    admission_date: date
    context: str
    cohort_code: str = ""
    previous_plan_id: str | None = None
    admission_source_snapshot_id: str | None = None
    admission_source_sha256: str | None = None
    admission_verification_method: str | None = None
    admission_record_reference_hash: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "program_id": self.program_id,
            "admission_date": self.admission_date.isoformat(),
            "context": self.context,
            "cohort_code": self.cohort_code,
            "previous_plan_id": self.previous_plan_id,
            "admission_source_snapshot_id": self.admission_source_snapshot_id,
            "admission_source_sha256": self.admission_source_sha256,
            "admission_verification_method": self.admission_verification_method,
            "admission_record_reference_hash": self.admission_record_reference_hash,
        }


@dataclass(frozen=True, slots=True)
class AssignmentPolicyCandidate:
    policy_id: str
    policy_code: str
    version: int
    program_id: str
    plan_id: str
    revision_id: str
    context: str
    admission_from: date | None
    admission_to: date | None
    cohort_code: str
    previous_plan_id: str | None
    effective_from: date | None
    effective_to: date | None
    supersedes_id: str | None
    status: str
    epistemic_status: str
    content_hash: str
    source_set_hash: str
    evidence_ids: tuple[str, ...]
    revision_status: str
    revision_content_hash: str
    revision_source_set_hash: str
    evidence_sealed: bool
    allow_retired_revision: bool

    def applies_to(self, value: AssignmentInput) -> bool:
        return (
            self.program_id == value.program_id
            and self.context == value.context
            and (self.admission_from is None or self.admission_from <= value.admission_date)
            and (self.admission_to is None or value.admission_date < self.admission_to)
            and (not self.cohort_code or self.cohort_code == value.cohort_code)
            and (self.effective_from is None or self.effective_from <= value.admission_date)
            and (self.effective_to is None or value.admission_date < self.effective_to)
            and (
                self.previous_plan_id is None
                or self.previous_plan_id == value.previous_plan_id
            )
        )

    @property
    def can_resolve(self) -> bool:
        return (
            self.status
            in {
                CurriculumAssignmentPolicyStatus.PUBLISHED.value,
                CurriculumAssignmentPolicyStatus.SUPERSEDED.value,
            }
            and self.epistemic_status == EpistemicStatus.VERIFIED.value
            and bool(self.content_hash)
            and bool(self.source_set_hash)
            and bool(self.evidence_ids)
            and self.revision_status in {"PUBLISHED", "SUPERSEDED", "RETIRED"}
            and (self.revision_status != "RETIRED" or self.allow_retired_revision)
            and bool(self.revision_content_hash)
            and bool(self.revision_source_set_hash)
            and self.evidence_sealed
        )

    def trace(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "policy_code": self.policy_code,
            "version": self.version,
            "plan_id": self.plan_id,
            "revision_id": self.revision_id,
            "status": self.status,
            "epistemic_status": self.epistemic_status,
            "content_hash": self.content_hash,
            "source_set_hash": self.source_set_hash,
            "evidence_ids": list(self.evidence_ids),
            "revision_status": self.revision_status,
            "revision_content_hash": self.revision_content_hash,
            "revision_source_set_hash": self.revision_source_set_hash,
            "evidence_sealed": self.evidence_sealed,
            "allow_retired_revision": self.allow_retired_revision,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "supersedes_id": self.supersedes_id,
        }


@dataclass(frozen=True, slots=True)
class AssignmentDecision:
    status: str
    reason_codes: tuple[str, ...]
    candidates: tuple[AssignmentPolicyCandidate, ...]
    selected_policy_id: str | None = None
    selected_plan_id: str | None = None
    selected_revision_id: str | None = None

    def to_dict(self, value: AssignmentInput) -> dict[str, object]:
        payload: dict[str, object] = {
            "resolver_version": RESOLVER_VERSION,
            "input": value.to_dict(),
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "candidates": [candidate.trace() for candidate in self.candidates],
            "selected_policy_id": self.selected_policy_id,
            "selected_plan_id": self.selected_plan_id,
            "selected_revision_id": self.selected_revision_id,
        }
        payload["decision_hash"] = canonical_content_hash(payload)
        return payload


def resolve_curriculum_assignment(
    value: AssignmentInput,
    policies: tuple[AssignmentPolicyCandidate, ...],
) -> AssignmentDecision:
    applicable = tuple(
        sorted(
            (candidate for candidate in policies if candidate.applies_to(value)),
            key=lambda candidate: (candidate.policy_code, candidate.version, candidate.policy_id),
        )
    )
    if not applicable:
        return AssignmentDecision(
            status=CurriculumAssignmentDecisionStatus.UNKNOWN.value,
            reason_codes=(AssignmentReason.NO_APPLICABLE_POLICY.value,),
            candidates=(),
        )
    superseded_ids = {candidate.supersedes_id for candidate in applicable if candidate.supersedes_id}
    effective_applicable = tuple(
        candidate for candidate in applicable if candidate.policy_id not in superseded_ids
    )
    resolvable = tuple(candidate for candidate in effective_applicable if candidate.can_resolve)
    if not resolvable:
        return AssignmentDecision(
            status=CurriculumAssignmentDecisionStatus.NEEDS_REVIEW.value,
            reason_codes=(AssignmentReason.EVIDENCE_INSUFFICIENT.value,),
            candidates=effective_applicable,
        )
    if len(resolvable) != 1:
        return AssignmentDecision(
            status=CurriculumAssignmentDecisionStatus.NEEDS_REVIEW.value,
            reason_codes=(AssignmentReason.MULTIPLE_APPLICABLE_POLICIES.value,),
            candidates=effective_applicable,
        )
    # A caller-supplied record reference is only a correlation hint. Until an
    # institutional adapter resolves it to an archived fact, it cannot prove admission.
    admission_fact_verified = (
        value.admission_verification_method
        == AdmissionFactVerificationMethod.SOURCE_SNAPSHOT.value
        and bool(value.admission_source_snapshot_id)
        and bool(value.admission_source_sha256)
    )
    if not admission_fact_verified:
        return AssignmentDecision(
            status=CurriculumAssignmentDecisionStatus.NEEDS_REVIEW.value,
            reason_codes=(AssignmentReason.ADMISSION_FACT_UNVERIFIED.value,),
            candidates=effective_applicable,
        )
    selected = resolvable[0]
    return AssignmentDecision(
        status=CurriculumAssignmentDecisionStatus.RESOLVED.value,
        reason_codes=(AssignmentReason.EXACT_VERIFIED_POLICY.value,),
        candidates=effective_applicable,
        selected_policy_id=selected.policy_id,
        selected_plan_id=selected.plan_id,
        selected_revision_id=selected.revision_id,
    )
