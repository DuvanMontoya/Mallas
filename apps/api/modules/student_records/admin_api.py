from __future__ import annotations

from typing import Any, NoReturn
from uuid import UUID

from django.http import HttpRequest
from ninja import Router, Schema, Status
from ninja.security import django_auth

from modules.common.api import raise_problem, with_problem_responses
from modules.student_records.application.administration import (
    StudentAdministrationError,
    create_administered_enrollment,
    list_administered_enrollments,
    student_admin_catalog,
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


class AdminTermView(Schema):
    id: UUID
    institution_id: UUID
    campus_id: UUID | None
    code: str
    status: str


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
    student_number: str
    institution_id: UUID
    program_id: UUID
    program_name: str
    plan_id: UUID
    plan_code: str
    admission_term_id: UUID
    admission_term_code: str
    status: str
    cohort_code: str


class AdminEnrollmentCollectionView(Schema):
    items: list[AdminEnrollmentView]


class AdminEnrollmentCreatePayload(Schema):
    email: str
    temporary_password: str
    display_name: str
    student_number: str
    institution_id: UUID
    program_id: UUID
    plan_id: UUID
    revision_basis_id: UUID
    admission_term_id: UUID
    cohort_code: str = ""


def _error(error: StudentAdministrationError) -> NoReturn:
    status = (
        403
        if error.code == "student_admin_forbidden"
        else 404
        if error.code == "student_admin_reference_not_found"
        else 409
        if error.code == "student_account_exists"
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


@router.get(
    "/enrollments",
    auth=django_auth,
    response=with_problem_responses(AdminEnrollmentCollectionView),
)
def admin_enrollments(request: HttpRequest, search: str = "") -> dict[str, Any]:
    try:
        return {"items": list_administered_enrollments(request.auth, search=search)}
    except StudentAdministrationError as error:
        _error(error)


@router.post(
    "/enrollments",
    auth=django_auth,
    response=with_problem_responses({201: AdminEnrollmentView}),
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
    row = next(
        item for item in list_administered_enrollments(request.auth) if item["id"] == enrollment.pk
    )
    return Status(201, row)
