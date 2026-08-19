from __future__ import annotations

from datetime import date, datetime
from typing import Any, NoReturn
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from ninja import Header, Router, Schema, Status
from ninja.security import django_auth

from modules.common.api import raise_problem, with_problem_responses
from modules.student_records.application.administration import (
    StudentAdministrationError,
    administered_enrollment_summary_view,
    administered_enrollment_view,
    create_administered_enrollment,
    create_administered_transition_enrollment,
    get_administered_identity,
    list_administered_enrollments,
    override_administered_enrollment_assignment,
    preview_administered_assignment,
    preview_administered_transition,
    resolve_administered_enrollment_revision,
    student_admin_catalog,
    update_administered_identity,
)

router = Router(tags=["Student administration"])


class AdminInstitutionView(Schema):
    id: UUID
    name: str


class AdminProgramView(Schema):
    id: UUID
    institution_id: UUID
    campus_id: UUID
    campus_name: str
    code: str
    name: str


class AdminPlanView(Schema):
    id: UUID
    program_id: UUID
    code: str
    title: str


class AdminRevisionView(Schema):
    id: UUID
    plan_id: UUID
    code: str
    status: str
    effective_from: date
    effective_to: date | None


class AdminTermView(Schema):
    id: UUID
    institution_id: UUID
    campus_id: UUID | None
    code: str
    status: str
    starts_at: datetime
    ends_at: datetime
    admission_source_status: str


class StudentAdminCatalogView(Schema):
    institutions: list[AdminInstitutionView]
    programs: list[AdminProgramView]
    plans: list[AdminPlanView]
    revisions: list[AdminRevisionView]
    terms: list[AdminTermView]


class AdminEnrollmentView(Schema):
    id: UUID
    student_profile_id: UUID
    email: str
    display_name: str
    first_name: str
    middle_names: str
    first_surname: str
    second_surname: str
    preferred_name: str
    birth_date: date | None
    age: int | None
    identity_data_status: str
    identity_verification_method: str
    identity_version: str
    student_number: str
    institution_id: UUID
    program_id: UUID
    program_name: str
    plan_id: UUID | None
    plan_code: str | None
    revision_basis_id: UUID | None
    admission_term_id: UUID
    admission_term_code: str
    status: str
    cohort_code: str
    review_reasons: list[str]
    version: str


class AdminEnrollmentSummaryView(Schema):
    id: UUID
    student_profile_id: UUID
    email: str
    display_name: str
    identity_data_status: str
    student_number: str
    institution_id: UUID
    program_id: UUID
    program_name: str
    plan_id: UUID | None
    plan_code: str | None
    revision_basis_id: UUID | None
    admission_term_id: UUID
    admission_term_code: str
    status: str
    cohort_code: str
    review_reasons: list[str]
    version: str


class AdminEnrollmentCollectionView(Schema):
    items: list[AdminEnrollmentSummaryView]
    total: int
    limit: int
    offset: int
    next_offset: int | None
    previous_offset: int | None


class AdminEnrollmentCreatePayload(Schema):
    email: str
    temporary_password: str
    display_name: str | None = None
    first_name: str | None = None
    middle_names: str | None = None
    first_surname: str | None = None
    second_surname: str | None = None
    preferred_name: str | None = None
    birth_date: date | None = None
    student_number: str
    institution_id: UUID
    program_id: UUID
    plan_id: UUID | None = None
    revision_basis_id: UUID | None = None
    admission_term_id: UUID
    cohort_code: str | None = None
    assignment_context: str = "ADMISSION"
    expected_assignment_hash: str | None = None
    previous_plan_id: UUID | None = None
    admission_verification_method: str = "SOURCE_SNAPSHOT"
    admission_record_reference: str | None = None


class AdminAssignmentPreviewPayload(Schema):
    program_id: UUID
    admission_term_id: UUID
    context: str = "ADMISSION"
    cohort_code: str = ""
    previous_plan_id: UUID | None = None
    admission_verification_method: str = "SOURCE_SNAPSHOT"
    admission_record_reference: str | None = None


class AdminAssignmentInputView(Schema):
    program_id: str
    admission_date: date
    context: str
    cohort_code: str
    previous_plan_id: str | None
    admission_source_snapshot_id: str | None
    admission_source_sha256: str | None
    admission_verification_method: str | None
    admission_record_reference_hash: str | None


class AdminAssignmentCandidateView(Schema):
    policy_id: str
    policy_code: str
    version: int
    plan_id: str
    revision_id: str
    status: str
    epistemic_status: str
    content_hash: str
    source_set_hash: str
    evidence_ids: list[str]
    revision_status: str
    revision_content_hash: str
    revision_source_set_hash: str
    evidence_sealed: bool
    effective_from: date | None
    effective_to: date | None
    supersedes_id: str | None
    allow_retired_revision: bool


class AdminAssignmentPreviewView(Schema):
    resolver_version: str
    input: AdminAssignmentInputView
    status: str
    reason_codes: list[str]
    candidates: list[AdminAssignmentCandidateView]
    selected_policy_id: str | None
    selected_plan_id: str | None
    selected_revision_id: str | None
    decision_hash: str
    admission_term_id: str
    admission_term_code: str
    admission_term_source_status: str
    selected_plan_code: str | None
    selected_revision_code: str | None
    source_enrollment_id: str | None = None


class AdminTransitionPayload(Schema):
    admission_term_id: UUID
    context: str
    cohort_code: str = ""
    admission_verification_method: str = "SOURCE_SNAPSHOT"
    admission_record_reference: str | None = None


class AdminTransitionCreatePayload(AdminTransitionPayload):
    expected_assignment_hash: str


class AdminEnrollmentRevisionPayload(Schema):
    pass


class AdminEnrollmentOverridePayload(Schema):
    plan_id: UUID
    revision_basis_id: UUID
    evidence_id: UUID
    exception_id: UUID
    reason_code: str


class AdminIdentityUpdatePayload(Schema):
    first_name: str
    middle_names: str = ""
    first_surname: str
    second_surname: str = ""
    preferred_name: str = ""
    birth_date: date
    rationale: str


def _error(error: StudentAdministrationError) -> NoReturn:
    status = (
        403
        if error.code in {"student_admin_forbidden", "student_admin_step_up_required"}
        else 404
        if error.code == "student_admin_reference_not_found"
        else 428
        if error.code == "student_admin_precondition_required"
        else 409
        if error.code in {"student_account_exists", "student_admin_stale_resource"}
        else 429
        if error.code == "student_admin_rate_limited"
        else 422
    )
    raise_problem(
        status=status,
        code=error.code.upper(),
        title="Student administration request failed",
        detail=str(error),
    )


@router.get("/catalog", auth=django_auth, response=with_problem_responses(StudentAdminCatalogView))
def admin_catalog(request: HttpRequest) -> dict[str, Any]:
    try:
        return student_admin_catalog(request.auth)
    except StudentAdministrationError as error:
        _error(error)


@router.post(
    "/assignment-preview",
    auth=django_auth,
    response=with_problem_responses(AdminAssignmentPreviewView),
)
def admin_assignment_preview(
    request: HttpRequest, response: HttpResponse, payload: AdminAssignmentPreviewPayload
) -> dict[str, Any]:
    try:
        result = preview_administered_assignment(actor=request.auth, **payload.model_dump())
    except StudentAdministrationError as error:
        _error(error)
    response["Cache-Control"] = "private, no-store"
    return result


@router.post(
    "/enrollments/{source_enrollment_id}/transition-preview",
    auth=django_auth,
    response=with_problem_responses(AdminAssignmentPreviewView),
)
def admin_transition_preview(
    request: HttpRequest,
    response: HttpResponse,
    source_enrollment_id: UUID,
    payload: AdminTransitionPayload,
) -> dict[str, Any]:
    try:
        result = preview_administered_transition(
            actor=request.auth,
            source_enrollment_id=source_enrollment_id,
            **payload.model_dump(),
        )
    except StudentAdministrationError as error:
        _error(error)
    response["Cache-Control"] = "private, no-store"
    return result


@router.get(
    "/enrollments",
    auth=django_auth,
    response=with_problem_responses(AdminEnrollmentCollectionView),
)
def admin_enrollments(
    request: HttpRequest, search: str = "", limit: int = 50, offset: int = 0
) -> dict[str, Any]:
    try:
        return list_administered_enrollments(
            request.auth, search=search, limit=limit, offset=offset
        )
    except StudentAdministrationError as error:
        _error(error)


@router.get(
    "/enrollments/{enrollment_id}/identity",
    auth=django_auth,
    response=with_problem_responses(AdminEnrollmentView),
)
def admin_enrollment_identity(
    request: HttpRequest, response: HttpResponse, enrollment_id: UUID
) -> dict[str, Any]:
    try:
        enrollment = get_administered_identity(
            actor=request.auth, enrollment_id=enrollment_id, request=request
        )
    except StudentAdministrationError as error:
        _error(error)
    response["Cache-Control"] = "private, no-store"
    return administered_enrollment_view(enrollment)


@router.post(
    "/enrollments",
    auth=django_auth,
    response=with_problem_responses({201: AdminEnrollmentSummaryView}),
)
def admin_enrollment_create(
    request: HttpRequest, payload: AdminEnrollmentCreatePayload
) -> Status[dict[str, Any]]:
    try:
        enrollment = create_administered_enrollment(
            actor=request.auth,
            request=request,
            **payload.model_dump(),
        )
    except StudentAdministrationError as error:
        _error(error)
    return Status(201, administered_enrollment_summary_view(enrollment))


@router.post(
    "/enrollments/{source_enrollment_id}/transitions",
    auth=django_auth,
    response=with_problem_responses({201: AdminEnrollmentSummaryView}),
)
def admin_transition_create(
    request: HttpRequest,
    source_enrollment_id: UUID,
    payload: AdminTransitionCreatePayload,
) -> Status[dict[str, Any]]:
    try:
        enrollment = create_administered_transition_enrollment(
            actor=request.auth,
            source_enrollment_id=source_enrollment_id,
            request=request,
            **payload.model_dump(),
        )
    except StudentAdministrationError as error:
        _error(error)
    return Status(201, administered_enrollment_summary_view(enrollment))


@router.patch(
    "/enrollments/{enrollment_id}/revision",
    auth=django_auth,
    response=with_problem_responses(AdminEnrollmentSummaryView),
)
def admin_enrollment_revision_confirm(
    request: HttpRequest,
    enrollment_id: UUID,
    payload: AdminEnrollmentRevisionPayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        enrollment = resolve_administered_enrollment_revision(
            actor=request.auth,
            enrollment_id=enrollment_id,
            expected_version=if_match,
            request=request,
        )
    except StudentAdministrationError as error:
        _error(error)
    return administered_enrollment_summary_view(enrollment)


@router.post(
    "/enrollments/{enrollment_id}/assignment-override",
    auth=django_auth,
    response=with_problem_responses(AdminEnrollmentSummaryView),
)
def admin_enrollment_assignment_override(
    request: HttpRequest,
    enrollment_id: UUID,
    payload: AdminEnrollmentOverridePayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        enrollment = override_administered_enrollment_assignment(
            actor=request.auth,
            enrollment_id=enrollment_id,
            expected_version=if_match,
            request=request,
            **payload.model_dump(),
        )
    except StudentAdministrationError as error:
        _error(error)
    return administered_enrollment_summary_view(enrollment)


@router.patch(
    "/enrollments/{enrollment_id}/identity",
    auth=django_auth,
    response=with_problem_responses(AdminEnrollmentView),
)
def admin_enrollment_identity_update(
    request: HttpRequest,
    enrollment_id: UUID,
    payload: AdminIdentityUpdatePayload,
    if_match: str | None = Header(None, alias="If-Match"),  # type: ignore[type-arg]
) -> dict[str, Any]:
    try:
        enrollment = update_administered_identity(
            actor=request.auth,
            enrollment_id=enrollment_id,
            expected_version=if_match,
            request=request,
            **payload.model_dump(),
        )
    except StudentAdministrationError as error:
        _error(error)
    return administered_enrollment_view(enrollment)
