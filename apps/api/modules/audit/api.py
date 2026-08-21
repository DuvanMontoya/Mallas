from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from ninja import Router, Schema
from ninja.security import django_auth

from modules.audit.application.overview import AcademicOverviewError, build_academic_overview
from modules.common.api import raise_problem, with_problem_responses


class CourseLinkView(Schema):
    code: str
    name: str
    credits: int | None
    href: str


class EvidenceView(Schema):
    reference: str
    snapshot_sha256: str
    locator: str
    page: int | None
    section: str
    excerpt: str
    annotation: str
    source_title: str
    source_url: str | None


class ProgressView(Schema):
    current: int
    required: int
    unit: str


class RequirementReasonView(Schema):
    code: str
    purpose: str
    status: str
    progress: ProgressView
    explanation_key: str
    facts_used: list[str]
    evidence_refs: list[str]
    evidence: list[EvidenceView]
    epistemic_status: str
    note: str
    source_url: str | None


class RequirementView(RequirementReasonView):
    owner_course_code: str | None
    href: str


class EnrollmentView(Schema):
    id: UUID
    student_name: str
    student_number: str | None
    program_code: str
    program_name: str
    plan_code: str
    plan_title: str
    revision_code: str
    revision_hash: str
    status: str


class AuditMetadataView(Schema):
    run_id: UUID | None
    generated_at: datetime | None
    engine_version: str | None
    result_hash: str | None
    input_fingerprint: str | None
    revision_hash: str
    source: str


class AuditOverallView(Schema):
    status: str
    required_credits: int
    earned_credits: int
    applied_credits: int
    unapplied_credits: int
    credit_progress_percent: int


class LedgerAllocationView(Schema):
    course_code: str
    attempt_id: str
    group_code: str | None
    earned_credits: int
    applied_credits: int
    unapplied_credits: int
    requirement_code: str
    explanation_key: str


class LedgerView(Schema):
    allocations: list[LedgerAllocationView]
    total_earned_credits: int
    total_applied_credits: int
    total_unapplied_credits: int
    group_applied_credits: dict[str, int]
    unknowns: list[str]
    warnings: list[str]


class AuditView(Schema):
    metadata: AuditMetadataView
    overall: AuditOverallView
    ledger: LedgerView


class ComponentView(Schema):
    code: str
    label: str
    required_credits: int
    applied_credits: int
    remaining_credits: int
    progress_percent: int
    status: str
    explanation_key: str
    href: str


class GroupView(Schema):
    code: str
    label: str
    component: str
    required_credits: int
    applied_credits: int
    remaining_credits: int
    mandatory_missing: list[CourseLinkView]
    options_available: list[CourseLinkView]
    status: str
    explanation_key: str
    waived: bool
    href: str


class UnknownView(Schema):
    kind: str
    code: str
    detail: str
    material: bool
    href: str


class WarningView(Schema):
    code: str
    severity: str
    title: str
    detail: str
    href: str


class CourseOptionView(CourseLinkView):
    eligibility: str
    group_codes: list[str]
    reasons: list[RequirementReasonView]
    selected_attempt_id: UUID | None


class NextUnlockView(CourseLinkView):
    status: str
    reason: RequirementReasonView


class HistorySummaryView(Schema):
    has_records: bool
    attempt_count: int
    passed_count: int
    in_progress_count: int
    recognition_count: int


class LinkSetView(Schema):
    self: str
    history: str
    curriculum: str


class AcademicOverviewView(Schema):
    state: str
    enrollment: EnrollmentView
    audit: AuditView
    components: list[ComponentView]
    groups: list[GroupView]
    graduation_requirements: list[RequirementView]
    external_graduation_requirements: list[RequirementView]
    requirements: list[RequirementView]
    mandatory_missing: list[CourseLinkView]
    unknowns: list[UnknownView]
    warnings: list[WarningView]
    eligible_courses: list[CourseOptionView]
    blocked_courses: list[CourseOptionView]
    unknown_courses: list[CourseOptionView]
    course_options: list[CourseOptionView]
    next_unlocks: list[NextUnlockView]
    history: HistorySummaryView
    links: LinkSetView


router = Router(tags=["Academic overview"])


@router.get(
    "/academic-overview",
    auth=django_auth,
    response=with_problem_responses(AcademicOverviewView),
)
def academic_overview(
    request: HttpRequest,
    response: HttpResponse,
    enrollment_id: UUID | None = None,
) -> dict[str, Any]:
    try:
        overview = build_academic_overview(request.auth, enrollment_id=enrollment_id)
    except AcademicOverviewError as error:
        status = (
            403
            if error.code == "overview_forbidden"
            else 409
            if error.code in {"enrollment_needs_review", "audit_input_inconsistent"}
            else 404
        )
        raise_problem(
            status=status,
            code=error.code.upper(),
            title="Academic overview unavailable",
            detail=str(error),
        )
    metadata = overview["audit"]["metadata"]
    etag = metadata.get("result_hash") or metadata.get("revision_hash")
    if etag:
        response["ETag"] = f'"{etag}"'
    return overview
