from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from domain.enums import EnrollmentStatus, RevisionStatus, UserRole
from modules.curriculum.models import CurriculumPlan, CurriculumRevision
from modules.identity.application.audit import record_audit_event
from modules.identity.models import RoleAssignment, User
from modules.institutions.models import Institution, Program
from modules.offerings.models import AcademicTerm
from modules.student_records.models import ProgramEnrollment, StudentProfile


class StudentAdministrationError(RuntimeError):
    def __init__(self, message: str, *, code: str = "student_admin_invalid") -> None:
        super().__init__(message)
        self.code = code


def _admin_assignments(actor: Any) -> list[RoleAssignment]:
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "pk", None):
        return []
    moment = timezone.now()
    return list(
        RoleAssignment.objects.filter(user_id=actor.pk, role=UserRole.ADMIN.value, active=True)
        .filter(Q(valid_from__isnull=True) | Q(valid_from__lte=moment))
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=moment))
        .order_by("institution_id", "program_id", "id")
    )


def _can_administer(
    actor: Any, institution_id: UUID | str, *, program_id: UUID | str | None = None
) -> bool:
    if getattr(actor, "is_superuser", False):
        return True
    for assignment in _admin_assignments(actor):
        if assignment.institution_id not in (None, institution_id):
            continue
        if program_id is None:
            return True
        if assignment.program_id in (None, program_id):
            return True
    return False


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
    assignments = _admin_assignments(actor)
    global_admin = any(
        assignment.institution_id is None and assignment.program_id is None
        for assignment in assignments
    )
    institution_wide_ids = {
        assignment.institution_id for assignment in assignments if assignment.program_id is None
    }
    program_ids = {assignment.program_id for assignment in assignments if assignment.program_id}
    program_scope = Q(faculty__campus__institution_id__in=institution_wide_ids) | Q(
        id__in=program_ids
    )
    if getattr(actor, "is_superuser", False) or global_admin:
        program_scope = Q(faculty__campus__institution_id__in=institution_ids)
    programs = list(
        Program.objects.filter(program_scope)
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
            status__in=(
                RevisionStatus.PUBLISHED.value,
                RevisionStatus.SUPERSEDED.value,
                RevisionStatus.RETIRED.value,
            ),
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
                "effective_from": revision.effective_from,
                "effective_to": revision.effective_to,
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
                "starts_at": term.starts_at,
                "ends_at": term.ends_at,
            }
            for term in terms
        ],
    }


def administered_enrollment_view(enrollment: ProgramEnrollment) -> dict[str, Any]:
    return {
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


def list_administered_enrollments(
    actor: Any,
    *,
    search: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    institutions = _require_admin_scope(actor)
    assignments = _admin_assignments(actor)
    global_admin = any(
        assignment.institution_id is None and assignment.program_id is None
        for assignment in assignments
    )
    institution_wide_ids = {
        assignment.institution_id for assignment in assignments if assignment.program_id is None
    }
    program_ids = {assignment.program_id for assignment in assignments if assignment.program_id}
    scope = Q(student__institution_id__in=institution_wide_ids) | Q(program_id__in=program_ids)
    if getattr(actor, "is_superuser", False) or global_admin:
        scope = Q(student__institution_id__in=[institution.pk for institution in institutions])
    query = ProgramEnrollment.objects.filter(scope).select_related(
        "student__user", "program", "plan", "admission_term"
    )
    normalized_search = search.strip()
    if normalized_search:
        query = query.filter(
            Q(student__user__email__icontains=normalized_search)
            | Q(student__display_name__icontains=normalized_search)
            | Q(student__student_number__icontains=normalized_search)
        )
    safe_limit = min(max(limit, 1), 100)
    safe_offset = max(offset, 0)
    total = query.count()
    ordered = query.order_by("student__display_name", "student__user__email", "id")
    items = [
        administered_enrollment_view(enrollment)
        for enrollment in ordered[safe_offset : safe_offset + safe_limit]
    ]
    return {
        "items": items,
        "total": total,
        "limit": safe_limit,
        "offset": safe_offset,
        "next_offset": safe_offset + safe_limit if safe_offset + safe_limit < total else None,
        "previous_offset": max(0, safe_offset - safe_limit) if safe_offset else None,
    }


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
    if not _can_administer(actor, institution_id, program_id=program_id):
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
    if revision.status not in {
        RevisionStatus.PUBLISHED.value,
        RevisionStatus.SUPERSEDED.value,
        RevisionStatus.RETIRED.value,
    }:
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
    # This scoped administrative action is the institution's identity check.
    # Leaving the value null would make the verification endpoint unreachable,
    # because requesting that verification itself requires a session.
    user.email_verified_at = timezone.now()
    user.must_change_password = True
    user.initial_password_expires_at = timezone.now() + timedelta(hours=72)
    try:
        user.save()
        student = StudentProfile.objects.create(
            user=user,
            institution=institution,
            student_number=student_number.strip(),
            display_name=display_name.strip(),
            metadata={"created_via": "native_student_administration"},
        )
    except IntegrityError as exc:
        raise StudentAdministrationError(
            "An account or student number already exists.",
            code="student_account_exists",
        ) from exc
    admission_date = term.starts_at.date()
    revision_applies = revision.effective_from <= admission_date and (
        revision.effective_to is None or admission_date < revision.effective_to
    )
    enrollment_status = (
        EnrollmentStatus.ACTIVE.value if revision_applies else EnrollmentStatus.NEEDS_REVIEW.value
    )
    enrollment = ProgramEnrollment.objects.create(
        student=student,
        program=program,
        plan=plan,
        revision_basis=revision,
        admission_term=term,
        status=enrollment_status,
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
            "revision_temporally_applicable": revision_applies,
            "enrollment_status": enrollment_status,
        },
    )
    return enrollment
