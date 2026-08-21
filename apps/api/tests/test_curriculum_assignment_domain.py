from __future__ import annotations

import datetime

from domain.curriculum_assignment import (
    AssignmentInput,
    AssignmentPolicyCandidate,
    AssignmentReason,
    resolve_curriculum_assignment,
)
from domain.enums import (
    CurriculumAssignmentDecisionStatus,
    CurriculumAssignmentPolicyStatus,
    EpistemicStatus,
)


def candidate(**overrides: object) -> AssignmentPolicyCandidate:
    values: dict[str, object] = {
        "policy_id": "policy-1",
        "policy_code": "STAT-ADMISSION",
        "version": 1,
        "program_id": "program-1",
        "plan_id": "plan-2514",
        "revision_id": "revision-2023",
        "context": "ADMISSION",
        "admission_from": datetime.date(2023, 5, 20),
        "admission_to": None,
        "cohort_code": "",
        "previous_plan_id": None,
        "effective_from": datetime.date(2023, 5, 20),
        "effective_to": None,
        "supersedes_id": None,
        "status": CurriculumAssignmentPolicyStatus.PUBLISHED.value,
        "epistemic_status": EpistemicStatus.VERIFIED.value,
        "content_hash": "a" * 64,
        "source_set_hash": "b" * 64,
        "evidence_ids": ("evidence-1",),
        "revision_status": "PUBLISHED",
        "revision_content_hash": "c" * 64,
        "revision_source_set_hash": "d" * 64,
        "evidence_sealed": True,
        "evidence_purposes_valid": True,
        "allow_retired_revision": False,
    }
    values.update(overrides)
    return AssignmentPolicyCandidate(**values)  # type: ignore[arg-type]


def assignment_input(**overrides: object) -> AssignmentInput:
    values: dict[str, object] = {
        "program_id": "program-1",
        "admission_date": datetime.date(2026, 1, 15),
        "context": "ADMISSION",
        "cohort_code": "2026-1",
        "previous_plan_id": None,
        "admission_source_snapshot_id": "admission-snapshot-1",
        "admission_source_sha256": "e" * 64,
        "admission_verification_method": "VERIFIED_ADMISSION_FACT",
        "admission_record_reference_hash": None,
        "admission_fact_id": "admission-fact-1",
        "admission_fact_content_hash": "f" * 64,
    }
    values.update(overrides)
    return AssignmentInput(**values)  # type: ignore[arg-type]


def test_exact_verified_policy_resolves_reproducibly() -> None:
    value = assignment_input()
    decision = resolve_curriculum_assignment(value, (candidate(),))
    assert decision.status == CurriculumAssignmentDecisionStatus.RESOLVED.value
    assert decision.selected_plan_id == "plan-2514"
    assert decision.reason_codes == (AssignmentReason.EXACT_VERIFIED_POLICY.value,)
    assert decision.to_dict(value) == decision.to_dict(value)


def test_missing_policy_is_unknown_instead_of_first_revision_fallback() -> None:
    decision = resolve_curriculum_assignment(assignment_input(), ())
    assert decision.status == CurriculumAssignmentDecisionStatus.UNKNOWN.value
    assert decision.selected_revision_id is None
    assert decision.reason_codes == (AssignmentReason.NO_APPLICABLE_POLICY.value,)


def test_unverified_or_unhashed_policy_requires_review() -> None:
    policies = (
        candidate(epistemic_status=EpistemicStatus.UNKNOWN.value),
        candidate(policy_id="policy-2", content_hash=""),
    )
    decision = resolve_curriculum_assignment(assignment_input(), policies)
    assert decision.status == CurriculumAssignmentDecisionStatus.NEEDS_REVIEW.value
    assert decision.reason_codes == (AssignmentReason.EVIDENCE_INSUFFICIENT.value,)


def test_verified_policy_cannot_resolve_an_unverified_admission_fact() -> None:
    value = assignment_input(
        admission_verification_method=None,
        admission_record_reference_hash=None,
    )
    decision = resolve_curriculum_assignment(value, (candidate(),))
    assert decision.status == CurriculumAssignmentDecisionStatus.NEEDS_REVIEW.value
    assert decision.reason_codes == (AssignmentReason.ADMISSION_FACT_UNVERIFIED.value,)


def test_overlapping_verified_policies_never_resolve_by_order_or_priority() -> None:
    policies = (candidate(), candidate(policy_id="policy-2", version=2))
    decision = resolve_curriculum_assignment(assignment_input(), policies)
    assert decision.status == CurriculumAssignmentDecisionStatus.NEEDS_REVIEW.value
    assert decision.selected_policy_id is None
    assert decision.reason_codes == (AssignmentReason.MULTIPLE_APPLICABLE_POLICIES.value,)


def test_context_cohort_prior_plan_and_half_open_dates_are_exact() -> None:
    policy = candidate(
        context="REENTRY",
        cohort_code="2026-1",
        previous_plan_id="plan-old",
        admission_to=datetime.date(2026, 2, 1),
    )
    matching = assignment_input(
        context="REENTRY",
        previous_plan_id="plan-old",
        admission_date=datetime.date(2026, 1, 31),
    )
    assert resolve_curriculum_assignment(matching, (policy,)).status == "RESOLVED"
    boundary = assignment_input(
        context="REENTRY",
        previous_plan_id="plan-old",
        admission_date=datetime.date(2026, 2, 1),
    )
    assert resolve_curriculum_assignment(boundary, (policy,)).status == "UNKNOWN"


def test_explicit_successor_dominates_only_when_both_policies_apply() -> None:
    old = candidate(policy_id="policy-old", version=1)
    successor = candidate(
        policy_id="policy-new",
        version=2,
        admission_from=datetime.date(2026, 1, 1),
        effective_from=datetime.date(2026, 1, 1),
        supersedes_id="policy-old",
    )
    decision = resolve_curriculum_assignment(assignment_input(), (old, successor))
    assert decision.status == "RESOLVED"
    assert decision.selected_policy_id == "policy-new"
