from __future__ import annotations

from typing import Any
from uuid import UUID

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from domain.enums import RevisionStatus, UserRole
from modules.curriculum.models import CurriculumPlan, CurriculumRevision
from modules.identity.application.audit import record_audit_event
from modules.identity.application.authorization import has_role
from modules.identity.models import RoleAssignment, User
from modules.institutions.models import Institution, Program
from modules.offerings.models import AcademicTerm
from modules.student_records.models import ProgramEnrollment, StudentProfile


class StudentAdministrationError(RuntimeError):
    def __init__(self, message: str, *, code: str = "student_admin_invalid") -> None:
        super().__init__(message)
        self.code = code


def _can_administer(actor: Any, institution_id: UUID | str) -> bool:
    return bool(
        getattr(actor, "is_superuser", False)
        or has_role(actor, UserRole.ADMIN, institution_id=institution_id)
    )


def _authorized_institutions(actor: Any) -> list[Institution]:
    institutions = list(Institution.objects.order_by("display_name", "id"))
    return [institution for institution in institutions if _can_administer(actor, institution.pk)]


def _require_admin_scope(actor: Any) -> list[Institution]:
    institutions = _authorized_institutions(actor)
    if not institutions:
        raise StudentAdministrationError(
            "An active administrator scope is required.", code="student_admin_forbidden"
        )
    return institutions


def student_admin_catalog(actor: Any) -> dict[str, Any]:
    institutions = _require_admin_scope(actor)
    institution_ids = [institution.pk for institution in institutions]
    programs = list(
        Program.objects.filter(faculty__campus__institution_id__in=institution_ids)
        .select_related("faculty__campus")
        .order_by("name", "id")
    )
    plans = list(
        CurriculumPlan.objects.filter(program_id__in=[program.pk for program in programs]).order_by(
            "code", "id"
        )
    )
    revisions = list(
        CurriculumRevision.objects.filter(
            plan_id__in=[plan.pk for plan in plans],
            status=RevisionStatus.PUBLISHED.value,
        ).order_by("plan_id", "-effective_from", "-created_at")
    )
    terms = list(
        AcademicTerm.objects.filter(institution_id__in=institution_ids)
        .select_related("campus")
        .order_by("-starts_at", "code", "id")
    )
    return {
        "institutions": [
            {"id": institution.pk, "name": institution.display_name} for institution in institutions
        ],
        "programs": [
            {
                "id": program.pk,
                "institution_id": program.faculty.campus.institution_id,
                "campus_id": program.faculty.campus_id,
                "campus_name": program.faculty.campus.name,
                "code": program.code,
                "name": program.name,
            }
            for program in programs
        ],
        "plans": [
            {"id": plan.pk, "program_id": plan.program_id, "code": plan.code, "title": plan.title}
            for plan in plans
        ],
        "revisions": [
            {
                "id": revision.pk,
                "plan_id": revision.plan_id,
                "code": revision.revision_code,
                "status": revision.status,
            }
            for revision in revisions
        ],
        "terms": [
            {
                "id": term.pk,
                "institution_id": term.institution_id,
                "campus_id": term.campus_id,
                "code": term.code,
                "status": term.status,
            }
            for term in terms
        ],
    }


def list_administered_enrollments(actor: Any, *, search: str = "") -> list[dict[str, Any]]:
    institution_ids = [institution.pk for institution in _require_admin_scope(actor)]
    query = ProgramEnrollment.objects.filter(
        student__institution_id__in=institution_ids
    ).select_related("student__user", "program", "plan", "admission_term")
    normalized_search = search.strip()
    if normalized_search:
        query = query.filter(
            Q(student__user__email__icontains=normalized_search)
            | Q(student__display_name__icontains=normalized_search)
            | Q(student__student_number__icontains=normalized_search)
        )
    return [
        {
            "id": enrollment.pk,
            "student_profile_id": enrollment.student_id,
            "email": enrollment.student.user.email,
            "display_name": enrollment.student.display_name,
            "student_number": enrollment.student.student_number,
            "institution_id": enrollment.student.institution_id,
            "program_id": enrollment.program_id,
            "program_name": enrollment.program.name,
            "plan_id": enrollment.plan_id,
            "plan_code": enrollment.plan.code,
            "admission_term_id": enrollment.admission_term_id,
            "admission_term_code": enrollment.admission_term.code,
            "status": enrollment.status,
            "cohort_code": enrollment.cohort_code,
        }
        for enrollment in query.order_by("student__display_name", "student__user__email", "id")[
            :200
        ]
    ]


@transaction.atomic  # type: ignore[untyped-decorator]
def create_administered_enrollment(
    *,
    actor: Any,
    email: str,
    temporary_password: str,
    display_name: str,
    student_number: str,
    institution_id: UUID,
    program_id: UUID,
    plan_id: UUID,
    revision_basis_id: UUID,
    admission_term_id: UUID,
    cohort_code: str = "",
    request: Any | None = None,
) -> ProgramEnrollment:
    if not _can_administer(actor, institution_id):
        raise StudentAdministrationError(
            "You cannot administer students for this institution.",
            code="student_admin_forbidden",
        )
    normalized_email = User.objects.normalize_email(email.strip()).lower()
    if User.objects.filter(email__iexact=normalized_email).exists():
        raise StudentAdministrationError(
            "An account already exists for this email.", code="student_account_exists"
        )
    try:
        institution = Institution.objects.get(pk=institution_id)
        program = Program.objects.select_related("faculty__campus").get(pk=program_id)
        plan = CurriculumPlan.objects.get(pk=plan_id)
        revision = CurriculumRevision.objects.get(pk=revision_basis_id)
        term = AcademicTerm.objects.get(pk=admission_term_id)
    except (
        Institution.DoesNotExist,
        Program.DoesNotExist,
        CurriculumPlan.DoesNotExist,
        CurriculumRevision.DoesNotExist,
        AcademicTerm.DoesNotExist,
    ) as exc:
        raise StudentAdministrationError(
            "One of the selected academic records no longer exists.",
            code="student_admin_reference_not_found",
        ) from exc
    campus = program.faculty.campus
    if campus.institution_id != institution.pk:
        raise StudentAdministrationError(
            "Program and institution do not match.", code="student_admin_scope_mismatch"
        )
    if plan.program_id != program.pk or revision.plan_id != plan.pk:
        raise StudentAdministrationError(
            "Plan, revision and program do not match.", code="student_admin_scope_mismatch"
        )
    if revision.status != RevisionStatus.PUBLISHED.value:
        raise StudentAdministrationError(
            "New enrollments require a published curriculum revision.",
            code="student_admin_revision_not_published",
        )
    if term.institution_id != institution.pk or (
        term.campus_id is not None and term.campus_id != campus.pk
    ):
        raise StudentAdministrationError(
            "Admission term does not belong to the selected institution and campus.",
            code="student_admin_scope_mismatch",
        )
    user = User(email=normalized_email, is_active=True)
    try:
        user.full_clean(exclude=["password"])
        validate_password(temporary_password, user)
    except ValidationError as exc:
        raise StudentAdministrationError(
            "; ".join(exc.messages), code="student_admin_validation"
        ) from exc
    user.set_password(temporary_password)
    user.save()
    student = StudentProfile.objects.create(
        user=user,
        institution=institution,
        student_number=student_number.strip(),
        display_name=display_name.strip(),
        metadata={"created_via": "native_student_administration"},
    )
    enrollment = ProgramEnrollment.objects.create(
        student=student,
        program=program,
        plan=plan,
        revision_basis=revision,
        admission_term=term,
        cohort_code=cohort_code.strip(),
    )
    RoleAssignment.objects.create(
        user=user,
        role=UserRole.STUDENT.value,
        institution=institution,
        program=program,
        assigned_by=actor,
        rationale="Created with the native student administration workflow.",
    )
    record_audit_event(
        request,
        action="STUDENT_ENROLLMENT_CREATED",
        actor=actor,
        object_type="ProgramEnrollment",
        object_id=enrollment.pk,
        institution_id=institution.pk,
        metadata={
            "student_profile_id": str(student.pk),
            "program_id": str(program.pk),
            "plan_id": str(plan.pk),
            "admission_term_id": str(term.pk),
        },
    )
    return enrollment
