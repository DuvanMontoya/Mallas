from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import Q
from django.utils import timezone

from domain.enums import (
    AdmissionFactVerificationMethod,
    CurriculumAssignmentContext,
    CurriculumAssignmentDecisionStatus,
    CurriculumAssignmentMethod,
    EnrollmentStatus,
    EpistemicStatus,
    RevisionStatus,
    UserRole,
)
from domain.revision import canonical_content_hash
from modules.curriculum.application.assignment import resolve_assignment_preview
from modules.curriculum.models import (
    CurriculumAssignmentPolicy,
    CurriculumPlan,
    CurriculumRevision,
)
from modules.governance.models import Evidence
from modules.identity.application.audit import digest_identifier, record_audit_event
from modules.identity.application.rate_limit import consume_rate_limit
from modules.identity.models import (
    BirthDatePurpose,
    IdentityDataStatus,
    IdentityVerificationMethod,
    PersonProfile,
    RoleAssignment,
    User,
)
from modules.institutions.models import Institution, Program
from modules.offerings.models import AcademicTerm
from modules.student_records.models import (
    CurriculumAssignmentDecision,
    CurriculumAssignmentOverrideAuthorization,
    ProgramEnrollment,
    StudentOnboarding,
    StudentProfile,
)


class StudentAdministrationError(RuntimeError):
    def __init__(self, message: str, *, code: str = "student_admin_invalid") -> None:
        super().__init__(message)
        self.code = code


OVERRIDE_REASON_CODES = {
    "REENTRY_INSTITUTIONAL_DECISION",
    "TRANSITION_INSTITUTIONAL_DECISION",
    "ADMISSION_POLICY_EXCEPTION",
    "LEGACY_RECORD_VERIFIED",
}


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
                "admission_source_status": (
                    EpistemicStatus.VERIFIED.value
                    if term.source_snapshot_id
                    else EpistemicStatus.UNKNOWN.value
                ),
            }
            for term in terms
        ],
    }


def preview_administered_assignment(
    *,
    actor: Any,
    program_id: UUID,
    admission_term_id: UUID,
    context: str = CurriculumAssignmentContext.ADMISSION.value,
    cohort_code: str = "",
    previous_plan_id: UUID | None = None,
    admission_verification_method: str = AdmissionFactVerificationMethod.SOURCE_SNAPSHOT.value,
    admission_record_reference: str | None = None,
) -> dict[str, Any]:
    if context not in {item.value for item in CurriculumAssignmentContext}:
        raise StudentAdministrationError(
            "Assignment context is not supported.", code="student_admin_validation"
        )
    if admission_verification_method not in {
        item.value for item in AdmissionFactVerificationMethod
    }:
        raise StudentAdministrationError(
            "Admission verification method is not supported.",
            code="student_admin_validation",
        )
    normalized_reference = " ".join((admission_record_reference or "").split())
    reference_hash = (
        digest_identifier(f"admission-record:{normalized_reference}")
        if normalized_reference
        else None
    )
    try:
        program = Program.objects.select_related("faculty__campus").get(pk=program_id)
        term = AcademicTerm.objects.select_related("source_snapshot").get(pk=admission_term_id)
        previous_plan = (
            CurriculumPlan.objects.get(pk=previous_plan_id) if previous_plan_id else None
        )
    except (Program.DoesNotExist, AcademicTerm.DoesNotExist, CurriculumPlan.DoesNotExist) as exc:
        raise StudentAdministrationError(
            "One of the assignment inputs no longer exists.",
            code="student_admin_reference_not_found",
        ) from exc
    institution_id = program.faculty.campus.institution_id
    if not _can_administer(actor, institution_id, program_id=program.pk):
        raise StudentAdministrationError(
            "You cannot administer this program.", code="student_admin_forbidden"
        )
    if term.institution_id != institution_id or (
        term.campus_id is not None and term.campus_id != program.faculty.campus_id
    ):
        raise StudentAdministrationError(
            "Admission term does not belong to the selected program scope.",
            code="student_admin_scope_mismatch",
        )
    if previous_plan and previous_plan.program_id != program.pk:
        raise StudentAdministrationError(
            "Previous plan does not belong to the selected program.",
            code="student_admin_scope_mismatch",
        )
    try:
        admission_date = term.starts_at.astimezone(ZoneInfo(program.faculty.campus.timezone)).date()
    except ZoneInfoNotFoundError as exc:
        raise StudentAdministrationError(
            "The campus timezone is not configured correctly.",
            code="student_admin_configuration_invalid",
        ) from exc
    decision = resolve_assignment_preview(
        program_id=program.pk,
        admission_date=admission_date,
        context=context,
        cohort_code=cohort_code,
        previous_plan_id=previous_plan.pk if previous_plan else None,
        admission_source_snapshot_id=term.source_snapshot_id,
        admission_source_sha256=(term.source_snapshot.sha256 if term.source_snapshot_id else None),
        admission_verification_method=admission_verification_method,
        admission_record_reference_hash=reference_hash,
    )
    decision["admission_term_id"] = str(term.pk)
    decision["admission_term_code"] = term.code
    decision["admission_term_source_status"] = (
        EpistemicStatus.VERIFIED.value if term.source_snapshot_id else EpistemicStatus.UNKNOWN.value
    )
    selected_plan_id = decision.get("selected_plan_id")
    selected_revision_id = decision.get("selected_revision_id")
    selected_plan = (
        CurriculumPlan.objects.filter(pk=selected_plan_id).only("code").first()
        if selected_plan_id
        else None
    )
    selected_revision = (
        CurriculumRevision.objects.filter(pk=selected_revision_id).only("revision_code").first()
        if selected_revision_id
        else None
    )
    decision["selected_plan_code"] = selected_plan.code if selected_plan else None
    decision["selected_revision_code"] = (
        selected_revision.revision_code if selected_revision else None
    )
    return decision


def preview_administered_transition(
    *,
    actor: Any,
    source_enrollment_id: UUID | str,
    admission_term_id: UUID,
    context: str,
    cohort_code: str = "",
    admission_verification_method: str = AdmissionFactVerificationMethod.SOURCE_SNAPSHOT.value,
    admission_record_reference: str | None = None,
) -> dict[str, Any]:
    if context not in {
        CurriculumAssignmentContext.REENTRY.value,
        CurriculumAssignmentContext.PLAN_TRANSITION.value,
    }:
        raise StudentAdministrationError(
            "Existing-student assignment requires reentry or plan transition context.",
            code="student_admin_validation",
        )
    try:
        source = ProgramEnrollment.objects.select_related("student", "program", "plan").get(
            pk=source_enrollment_id
        )
    except ProgramEnrollment.DoesNotExist as exc:
        raise StudentAdministrationError(
            "Source enrollment was not found.", code="student_admin_reference_not_found"
        ) from exc
    if not _can_administer(actor, source.student.institution_id, program_id=source.program_id):
        raise StudentAdministrationError(
            "You cannot administer this enrollment.", code="student_admin_forbidden"
        )
    if source.plan_id is None or source.revision_basis_id is None:
        raise StudentAdministrationError(
            "Resolve the source enrollment curriculum before a transition.",
            code="student_admin_assignment_needs_review",
        )
    decision = preview_administered_assignment(
        actor=actor,
        program_id=source.program_id,
        admission_term_id=admission_term_id,
        context=context,
        cohort_code=cohort_code,
        previous_plan_id=source.plan_id,
        admission_verification_method=admission_verification_method,
        admission_record_reference=admission_record_reference,
    )
    decision["source_enrollment_id"] = str(source.pk)
    return decision


@transaction.atomic  # type: ignore[untyped-decorator]
def create_administered_transition_enrollment(
    *,
    actor: Any,
    source_enrollment_id: UUID | str,
    admission_term_id: UUID,
    context: str,
    expected_assignment_hash: str,
    cohort_code: str = "",
    admission_verification_method: str = AdmissionFactVerificationMethod.SOURCE_SNAPSHOT.value,
    admission_record_reference: str | None = None,
    request: Any | None = None,
) -> ProgramEnrollment:
    if not expected_assignment_hash:
        raise StudentAdministrationError(
            "Preview the transition assignment before creating the enrollment.",
            code="student_admin_precondition_required",
        )
    try:
        source = (
            ProgramEnrollment.objects.select_for_update()
            .select_related("student__institution", "program", "plan", "revision_basis")
            .get(pk=source_enrollment_id)
        )
    except ProgramEnrollment.DoesNotExist as exc:
        raise StudentAdministrationError(
            "Source enrollment was not found.", code="student_admin_reference_not_found"
        ) from exc
    if not _can_administer(actor, source.student.institution_id, program_id=source.program_id):
        raise StudentAdministrationError(
            "You cannot administer this enrollment.", code="student_admin_forbidden"
        )
    if settings.PRIVILEGED_MFA_REQUIRED and not getattr(actor, "_privileged_mfa_verified", False):
        raise StudentAdministrationError(
            "Privileged authentication is required to create a transition.",
            code="student_admin_step_up_required",
        )
    decision = preview_administered_transition(
        actor=actor,
        source_enrollment_id=source.pk,
        admission_term_id=admission_term_id,
        context=context,
        cohort_code=cohort_code,
        admission_verification_method=admission_verification_method,
        admission_record_reference=admission_record_reference,
    )
    if decision["decision_hash"] != expected_assignment_hash:
        raise StudentAdministrationError(
            "Curriculum assignment changed after preview; review it again.",
            code="student_admin_stale_resource",
        )
    automatic_assignment = decision["status"] == CurriculumAssignmentDecisionStatus.RESOLVED.value
    plan = None
    revision = None
    policy_id = None
    if automatic_assignment:
        try:
            plan = CurriculumPlan.objects.get(
                pk=decision["selected_plan_id"], program_id=source.program_id
            )
            revision = CurriculumRevision.objects.get(
                pk=decision["selected_revision_id"], plan=plan
            )
        except (CurriculumPlan.DoesNotExist, CurriculumRevision.DoesNotExist) as exc:
            raise StudentAdministrationError(
                "The resolved curriculum target no longer exists.",
                code="student_admin_reference_not_found",
            ) from exc
        policy_id = decision["selected_policy_id"]
    review_reasons = [] if automatic_assignment else ["CURRICULUM_ASSIGNMENT"]
    if "IDENTITY_REVIEW" in source.review_reasons:
        review_reasons.append("IDENTITY_REVIEW")
    status = (
        EnrollmentStatus.NEEDS_REVIEW.value if review_reasons else EnrollmentStatus.ACTIVE.value
    )
    try:
        enrollment = ProgramEnrollment.objects.create(
            student=source.student,
            program=source.program,
            plan=plan,
            revision_basis=revision,
            admission_term_id=admission_term_id,
            status=status,
            cohort_code=cohort_code.strip(),
            review_reasons=review_reasons,
            transition_events=[
                {
                    "context": context,
                    "source_enrollment_id": str(source.pk),
                    "previous_plan_id": str(source.plan_id),
                    "decision_hash": decision["decision_hash"],
                }
            ],
        )
    except IntegrityError as exc:
        raise StudentAdministrationError(
            "This student already has an enrollment for that program and term.",
            code="student_enrollment_exists",
        ) from exc
    StudentOnboarding.objects.create(enrollment=enrollment)
    CurriculumAssignmentDecision.objects.create(
        enrollment=enrollment,
        policy_id=policy_id,
        status=decision["status"],
        method=(
            CurriculumAssignmentMethod.AUTOMATIC.value
            if automatic_assignment
            else CurriculumAssignmentMethod.POLICY_EVALUATION.value
        ),
        resolver_version=decision["resolver_version"],
        input_data=decision["input"],
        reason_codes=decision["reason_codes"],
        candidates=decision["candidates"],
        selected_plan=plan,
        selected_revision=revision,
        decision_hash=decision["decision_hash"],
        decided_by=actor,
    )
    record_audit_event(
        request,
        action="STUDENT_ENROLLMENT_TRANSITION_CREATED",
        actor=actor,
        object_type="ProgramEnrollment",
        object_id=enrollment.pk,
        institution_id=source.student.institution_id,
        metadata={
            "source_enrollment_id": str(source.pk),
            "context": context,
            "previous_plan_id": str(source.plan_id),
            "selected_plan_id": str(plan.pk) if plan else None,
            "decision_hash": decision["decision_hash"],
            "assignment_status": decision["status"],
        },
    )
    return enrollment


def administered_enrollment_view(enrollment: ProgramEnrollment) -> dict[str, Any]:
    try:
        person = enrollment.student.user.person_profile
    except ObjectDoesNotExist:
        person = None
    return {
        "id": enrollment.pk,
        "student_profile_id": enrollment.student_id,
        "email": enrollment.student.user.email,
        "display_name": enrollment.student.display_name,
        "first_name": person.first_name if person else "",
        "middle_names": person.middle_names if person else "",
        "first_surname": person.first_surname if person else "",
        "second_surname": person.second_surname if person else "",
        "preferred_name": person.preferred_name if person else "",
        "birth_date": person.birth_date if person else None,
        "age": person.age_on() if person else None,
        "identity_data_status": person.data_status if person else IdentityDataStatus.NEEDS_REVIEW,
        "identity_verification_method": (
            person.verification_method if person else IdentityVerificationMethod.LEGACY_UNKNOWN
        ),
        "identity_version": (
            person.updated_at if person else enrollment.student.updated_at
        ).isoformat(),
        "student_number": enrollment.student.student_number,
        "institution_id": enrollment.student.institution_id,
        "program_id": enrollment.program_id,
        "program_name": enrollment.program.name,
        "plan_id": enrollment.plan_id,
        "plan_code": enrollment.plan.code if enrollment.plan_id else None,
        "revision_basis_id": enrollment.revision_basis_id,
        "admission_term_id": enrollment.admission_term_id,
        "admission_term_code": enrollment.admission_term.code,
        "status": enrollment.status,
        "cohort_code": enrollment.cohort_code,
        "review_reasons": enrollment.review_reasons,
        "version": enrollment.updated_at.isoformat(),
    }


def administered_enrollment_summary_view(enrollment: ProgramEnrollment) -> dict[str, Any]:
    try:
        person = enrollment.student.user.person_profile
    except ObjectDoesNotExist:
        person = None
    return {
        "id": enrollment.pk,
        "student_profile_id": enrollment.student_id,
        "email": enrollment.student.user.email,
        "display_name": enrollment.student.display_name,
        "identity_data_status": (person.data_status if person else IdentityDataStatus.NEEDS_REVIEW),
        "student_number": enrollment.student.student_number,
        "institution_id": enrollment.student.institution_id,
        "program_id": enrollment.program_id,
        "program_name": enrollment.program.name,
        "plan_id": enrollment.plan_id,
        "plan_code": enrollment.plan.code if enrollment.plan_id else None,
        "revision_basis_id": enrollment.revision_basis_id,
        "admission_term_id": enrollment.admission_term_id,
        "admission_term_code": enrollment.admission_term.code,
        "status": enrollment.status,
        "cohort_code": enrollment.cohort_code,
        "review_reasons": enrollment.review_reasons,
        "version": enrollment.updated_at.isoformat(),
    }


def get_administered_identity(
    *, actor: Any, enrollment_id: UUID | str, request: Any | None = None
) -> ProgramEnrollment:
    try:
        enrollment = ProgramEnrollment.objects.select_related(
            "student__user__person_profile", "program", "plan", "admission_term"
        ).get(pk=enrollment_id)
    except ProgramEnrollment.DoesNotExist as exc:
        raise StudentAdministrationError(
            "Enrollment was not found.", code="student_admin_reference_not_found"
        ) from exc
    if not _can_administer(
        actor, enrollment.student.institution_id, program_id=enrollment.program_id
    ):
        raise StudentAdministrationError(
            "You cannot view this identity.", code="student_admin_forbidden"
        )
    if settings.PRIVILEGED_MFA_REQUIRED and not getattr(actor, "_privileged_mfa_verified", False):
        raise StudentAdministrationError(
            "A recent privileged authentication is required to view birth date.",
            code="student_admin_step_up_required",
        )
    if not consume_rate_limit(
        key=f"user:{actor.pk}",
        action="identity:admin-detail-read",
        limit=settings.SENSITIVE_IDENTITY_READ_RATE_LIMIT_PER_MINUTE,
    ):
        raise StudentAdministrationError(
            "Too many private identity reads.", code="student_admin_rate_limited"
        )
    try:
        person_id = enrollment.student.user.person_profile.pk
    except ObjectDoesNotExist:
        person_id = ""
    record_audit_event(
        request,
        action="PERSON_IDENTITY_VIEWED",
        actor=actor,
        object_type="PersonProfile",
        object_id=person_id,
        institution_id=enrollment.student.institution_id,
        metadata={"student_profile_id": str(enrollment.student_id)},
    )
    return enrollment


@transaction.atomic  # type: ignore[untyped-decorator]
def resolve_administered_enrollment_revision(
    *,
    actor: Any,
    enrollment_id: UUID | str,
    expected_version: str | None,
    request: Any | None = None,
) -> ProgramEnrollment:
    if expected_version is None:
        raise StudentAdministrationError(
            "If-Match is required to confirm the reviewed enrollment.",
            code="student_admin_precondition_required",
        )
    try:
        enrollment = (
            ProgramEnrollment.objects.select_for_update()
            .select_related(
                "student__user",
                "student__institution",
                "program",
                "plan",
                "admission_term",
            )
            .get(pk=enrollment_id)
        )
    except ProgramEnrollment.DoesNotExist as exc:
        raise StudentAdministrationError(
            "Enrollment was not found.", code="student_admin_reference_not_found"
        ) from exc
    if not _can_administer(
        actor, enrollment.student.institution_id, program_id=enrollment.program_id
    ):
        raise StudentAdministrationError(
            "You cannot administer this enrollment.", code="student_admin_forbidden"
        )
    if settings.PRIVILEGED_MFA_REQUIRED and not getattr(actor, "_privileged_mfa_verified", False):
        raise StudentAdministrationError(
            "Privileged authentication is required to activate a curriculum assignment.",
            code="student_admin_step_up_required",
        )
    if expected_version.strip('"') != enrollment.updated_at.isoformat():
        raise StudentAdministrationError(
            "The enrollment changed since it was reviewed.", code="student_admin_stale_resource"
        )
    if enrollment.status != EnrollmentStatus.NEEDS_REVIEW.value:
        raise StudentAdministrationError(
            "Only an enrollment requiring review can use this resolution.",
            code="student_admin_status_invalid",
        )
    curriculum_review_pending = "CURRICULUM_ASSIGNMENT" in enrollment.review_reasons or (
        not enrollment.review_reasons and enrollment.plan_id is None
    )
    if not curriculum_review_pending:
        raise StudentAdministrationError(
            "This enrollment has no pending curriculum-assignment hold.",
            code="student_admin_status_invalid",
        )
    previous_decision = enrollment.assignment_decisions.order_by("-created_at", "-id").first()
    if previous_decision is None:
        raise StudentAdministrationError(
            "The enrollment has no assignment decision to reevaluate.",
            code="student_admin_assignment_needs_review",
        )
    input_data = previous_decision.input_data
    try:
        assignment = resolve_assignment_preview(
            program_id=enrollment.program_id,
            admission_date=date.fromisoformat(str(input_data["admission_date"])),
            context=str(input_data["context"]),
            cohort_code=str(input_data.get("cohort_code") or ""),
            previous_plan_id=(
                UUID(str(input_data["previous_plan_id"]))
                if input_data.get("previous_plan_id")
                else None
            ),
            admission_source_snapshot_id=(
                UUID(str(input_data["admission_source_snapshot_id"]))
                if input_data.get("admission_source_snapshot_id")
                else None
            ),
            admission_source_sha256=input_data.get("admission_source_sha256"),
            admission_verification_method=input_data.get("admission_verification_method"),
            admission_record_reference_hash=input_data.get("admission_record_reference_hash"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise StudentAdministrationError(
            "The stored assignment input cannot be reproduced.",
            code="student_admin_assignment_input_invalid",
        ) from exc
    if assignment["status"] != CurriculumAssignmentDecisionStatus.RESOLVED.value:
        raise StudentAdministrationError(
            "No unique verified assignment policy is available yet.",
            code="student_admin_assignment_needs_review",
        )
    try:
        plan = CurriculumPlan.objects.get(pk=assignment["selected_plan_id"])
        revision = CurriculumRevision.objects.get(pk=assignment["selected_revision_id"])
        policy = CurriculumAssignmentPolicy.objects.get(pk=assignment["selected_policy_id"])
    except (
        CurriculumPlan.DoesNotExist,
        CurriculumRevision.DoesNotExist,
        CurriculumAssignmentPolicy.DoesNotExist,
    ) as exc:
        raise StudentAdministrationError(
            "The resolved curriculum target no longer exists.",
            code="student_admin_reference_not_found",
        ) from exc
    if plan.program_id != enrollment.program_id or revision.plan_id != plan.pk:
        raise StudentAdministrationError(
            "The resolved curriculum target is outside this enrollment.",
            code="student_admin_scope_mismatch",
        )
    remaining_review_reasons = [
        reason for reason in enrollment.review_reasons if reason != "CURRICULUM_ASSIGNMENT"
    ]
    enrollment.plan = plan
    enrollment.revision_basis = revision
    enrollment.review_reasons = remaining_review_reasons
    enrollment.status = (
        EnrollmentStatus.NEEDS_REVIEW.value
        if remaining_review_reasons
        else EnrollmentStatus.ACTIVE.value
    )
    enrollment.save(
        update_fields=["plan", "revision_basis", "review_reasons", "status", "updated_at"]
    )
    CurriculumAssignmentDecision.objects.create(
        enrollment=enrollment,
        policy=policy,
        status=CurriculumAssignmentDecisionStatus.RESOLVED.value,
        method=CurriculumAssignmentMethod.AUTOMATIC.value,
        resolver_version=assignment["resolver_version"],
        input_data=assignment["input"],
        reason_codes=assignment["reason_codes"],
        candidates=assignment["candidates"],
        selected_plan=plan,
        selected_revision=revision,
        decision_hash=assignment["decision_hash"],
        decided_by=actor,
    )
    record_audit_event(
        request,
        action="STUDENT_ENROLLMENT_REVISION_CONFIRMED",
        actor=actor,
        object_type="ProgramEnrollment",
        object_id=enrollment.pk,
        institution_id=enrollment.student.institution_id,
        metadata={
            "previous_decision_hash": previous_decision.decision_hash,
            "decision_hash": assignment["decision_hash"],
            "confirmed_plan_id": str(plan.pk),
            "confirmed_revision_id": str(revision.pk),
        },
    )
    return enrollment


def assignment_override_authorization_view(
    authorization: CurriculumAssignmentOverrideAuthorization,
) -> dict[str, Any]:
    return {
        "id": authorization.pk,
        "enrollment_id": authorization.enrollment_id,
        "plan_id": authorization.plan_id,
        "plan_code": authorization.plan.code,
        "revision_basis_id": authorization.revision_basis_id,
        "revision_code": authorization.revision_basis.revision_code,
        "reason_code": authorization.reason_code,
        "evidence_id": authorization.evidence_id,
        "status": authorization.status,
        "prepared_by_id": authorization.prepared_by_id,
        "approved_by_id": authorization.approved_by_id,
        "content_hash": authorization.content_hash or None,
        "version": authorization.updated_at.isoformat(),
    }


def list_assignment_override_authorizations(
    *, actor: Any, enrollment_id: UUID | str
) -> list[CurriculumAssignmentOverrideAuthorization]:
    enrollment = (
        ProgramEnrollment.objects.select_related("student").filter(pk=enrollment_id).first()
    )
    if enrollment is None:
        raise StudentAdministrationError(
            "Enrollment was not found.", code="student_admin_reference_not_found"
        )
    if not _can_administer(
        actor, enrollment.student.institution_id, program_id=enrollment.program_id
    ):
        raise StudentAdministrationError(
            "You cannot view override authorizations.", code="student_admin_forbidden"
        )
    return list(
        CurriculumAssignmentOverrideAuthorization.objects.filter(enrollment=enrollment)
        .select_related("plan", "revision_basis", "evidence")
        .order_by("-created_at", "-id")
    )


@transaction.atomic  # type: ignore[untyped-decorator]
def create_assignment_override_authorization(
    *,
    actor: Any,
    enrollment_id: UUID | str,
    plan_id: UUID,
    revision_basis_id: UUID,
    evidence_id: UUID,
    reason_code: str,
    request: Any | None = None,
) -> CurriculumAssignmentOverrideAuthorization:
    if reason_code not in OVERRIDE_REASON_CODES:
        raise StudentAdministrationError(
            "Select a governed curriculum-override reason.",
            code="student_admin_override_reason_invalid",
        )
    enrollment = (
        ProgramEnrollment.objects.select_for_update()
        .select_related("student__institution", "program")
        .filter(pk=enrollment_id)
        .first()
    )
    if enrollment is None:
        raise StudentAdministrationError(
            "Enrollment was not found.", code="student_admin_reference_not_found"
        )
    if not _can_administer(
        actor, enrollment.student.institution_id, program_id=enrollment.program_id
    ):
        raise StudentAdministrationError(
            "You cannot prepare this authorization.", code="student_admin_forbidden"
        )
    if settings.PRIVILEGED_MFA_REQUIRED and not getattr(actor, "_privileged_mfa_verified", False):
        raise StudentAdministrationError(
            "Privileged authentication is required to prepare an override.",
            code="student_admin_step_up_required",
        )
    if enrollment.status != EnrollmentStatus.NEEDS_REVIEW.value or (
        "CURRICULUM_ASSIGNMENT" not in enrollment.review_reasons
        and not (not enrollment.review_reasons and enrollment.plan_id is None)
    ):
        raise StudentAdministrationError(
            "Only a pending curriculum assignment can be overridden.",
            code="student_admin_status_invalid",
        )
    try:
        plan = CurriculumPlan.objects.get(pk=plan_id, program_id=enrollment.program_id)
        revision = CurriculumRevision.objects.get(
            pk=revision_basis_id,
            plan=plan,
            status__in=(
                RevisionStatus.PUBLISHED.value,
                RevisionStatus.SUPERSEDED.value,
                RevisionStatus.RETIRED.value,
            ),
        )
        evidence = Evidence.objects.get(pk=evidence_id)
    except (
        CurriculumPlan.DoesNotExist,
        CurriculumRevision.DoesNotExist,
        Evidence.DoesNotExist,
    ) as exc:
        raise StudentAdministrationError(
            "The override target or evidence does not exist.",
            code="student_admin_reference_not_found",
        ) from exc
    if not revision.content_hash or not revision.source_set_hash:
        raise StudentAdministrationError(
            "The override target must be an immutable, fully hashed revision.",
            code="student_admin_revision_not_published",
        )
    authorization = CurriculumAssignmentOverrideAuthorization.objects.create(
        enrollment=enrollment,
        plan=plan,
        revision_basis=revision,
        reason_code=reason_code,
        evidence=evidence,
        prepared_by=actor,
    )
    record_audit_event(
        request,
        action="CURRICULUM_ASSIGNMENT_OVERRIDE_PREPARED",
        actor=actor,
        object_type="CurriculumAssignmentOverrideAuthorization",
        object_id=authorization.pk,
        institution_id=enrollment.student.institution_id,
        metadata={
            "enrollment_id": str(enrollment.pk),
            "plan_id": str(plan.pk),
            "revision_id": str(revision.pk),
            "reason_code": reason_code,
            "evidence_id": str(evidence.pk),
        },
    )
    return authorization


@transaction.atomic  # type: ignore[untyped-decorator]
def approve_assignment_override_authorization(
    *,
    actor: Any,
    authorization_id: UUID | str,
    expected_version: str | None,
    request: Any | None = None,
) -> CurriculumAssignmentOverrideAuthorization:
    if expected_version is None:
        raise StudentAdministrationError(
            "If-Match is required to approve an override.",
            code="student_admin_precondition_required",
        )
    authorization = (
        CurriculumAssignmentOverrideAuthorization.objects.select_for_update()
        .select_related(
            "enrollment__student",
            "plan",
            "revision_basis",
            "evidence__snapshot",
            "prepared_by",
        )
        .filter(pk=authorization_id)
        .first()
    )
    if authorization is None:
        raise StudentAdministrationError(
            "Override authorization was not found.", code="student_admin_reference_not_found"
        )
    enrollment = authorization.enrollment
    if not _can_administer(
        actor, enrollment.student.institution_id, program_id=enrollment.program_id
    ):
        raise StudentAdministrationError(
            "You cannot approve this authorization.", code="student_admin_forbidden"
        )
    if settings.PRIVILEGED_MFA_REQUIRED and not getattr(actor, "_privileged_mfa_verified", False):
        raise StudentAdministrationError(
            "Privileged authentication is required to approve an override.",
            code="student_admin_step_up_required",
        )
    if expected_version.strip('"') != authorization.updated_at.isoformat():
        raise StudentAdministrationError(
            "The authorization changed since it was reviewed.", code="student_admin_stale_resource"
        )
    if authorization.status != CurriculumAssignmentOverrideAuthorization.Status.DRAFT:
        raise StudentAdministrationError(
            "Only a draft authorization can be approved.", code="student_admin_status_invalid"
        )
    if authorization.prepared_by_id == actor.pk:
        raise StudentAdministrationError(
            "A different administrator must approve this override.",
            code="student_admin_separation_required",
        )
    revision = authorization.revision_basis
    evidence = authorization.evidence
    snapshot = evidence.snapshot
    if (
        revision.status
        not in {
            RevisionStatus.PUBLISHED.value,
            RevisionStatus.SUPERSEDED.value,
            RevisionStatus.RETIRED.value,
        }
        or not revision.content_hash
        or not revision.source_set_hash
        or not snapshot.sha256
        or not evidence.excerpt_hash
    ):
        raise StudentAdministrationError(
            "The authorization cannot be sealed from incomplete governance material.",
            code="student_admin_override_authorization_invalid",
        )
    sealed = {
        "authorization_id": str(authorization.pk),
        "enrollment_id": str(enrollment.pk),
        "plan_id": str(authorization.plan_id),
        "revision_id": str(revision.pk),
        "reason_code": authorization.reason_code,
        "evidence_id": str(evidence.pk),
        "revision_content_hash": revision.content_hash,
        "revision_source_set_hash": revision.source_set_hash,
        "snapshot_id": str(snapshot.pk),
        "snapshot_sha256": snapshot.sha256,
        "storage_key_hash": canonical_content_hash({"storage_key": snapshot.storage_key}),
        "excerpt_hash": evidence.excerpt_hash,
        "prepared_by_id": str(authorization.prepared_by_id),
        "approved_by_id": str(actor.pk),
    }
    authorization.status = CurriculumAssignmentOverrideAuthorization.Status.APPROVED
    authorization.approved_by = actor
    authorization.approved_at = timezone.now()
    authorization.revision_content_hash = revision.content_hash
    authorization.revision_source_set_hash = revision.source_set_hash
    authorization.sealed_snapshot_id = snapshot.pk
    authorization.sealed_snapshot_sha256 = snapshot.sha256
    authorization.sealed_storage_key_hash = sealed["storage_key_hash"]
    authorization.sealed_excerpt_hash = evidence.excerpt_hash
    authorization.content_hash = canonical_content_hash(sealed)
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL app.assignment_override_approval = 'allowed'")
    authorization.save()
    record_audit_event(
        request,
        action="CURRICULUM_ASSIGNMENT_OVERRIDE_APPROVED",
        actor=actor,
        object_type="CurriculumAssignmentOverrideAuthorization",
        object_id=authorization.pk,
        institution_id=enrollment.student.institution_id,
        metadata={"content_hash": authorization.content_hash},
    )
    return authorization


@transaction.atomic  # type: ignore[untyped-decorator]
def override_administered_enrollment_assignment(
    *,
    actor: Any,
    enrollment_id: UUID | str,
    authorization_id: UUID,
    expected_version: str | None,
    request: Any | None = None,
) -> ProgramEnrollment:
    if expected_version is None:
        raise StudentAdministrationError(
            "If-Match is required for a curriculum override.",
            code="student_admin_precondition_required",
        )
    enrollment = (
        ProgramEnrollment.objects.select_for_update()
        .select_related("student__institution", "program", "admission_term")
        .filter(pk=enrollment_id)
        .first()
    )
    if enrollment is None:
        raise StudentAdministrationError(
            "Enrollment was not found.", code="student_admin_reference_not_found"
        )
    if not _can_administer(
        actor, enrollment.student.institution_id, program_id=enrollment.program_id
    ):
        raise StudentAdministrationError(
            "You cannot override this enrollment.", code="student_admin_forbidden"
        )
    if settings.PRIVILEGED_MFA_REQUIRED and not getattr(actor, "_privileged_mfa_verified", False):
        raise StudentAdministrationError(
            "Privileged authentication is required for a curriculum override.",
            code="student_admin_step_up_required",
        )
    if expected_version.strip('"') != enrollment.updated_at.isoformat():
        raise StudentAdministrationError(
            "The enrollment changed since it was reviewed.", code="student_admin_stale_resource"
        )
    if enrollment.status != EnrollmentStatus.NEEDS_REVIEW.value or (
        "CURRICULUM_ASSIGNMENT" not in enrollment.review_reasons
        and not (not enrollment.review_reasons and enrollment.plan_id is None)
    ):
        raise StudentAdministrationError(
            "Only a pending curriculum assignment can be overridden.",
            code="student_admin_status_invalid",
        )
    authorization = (
        CurriculumAssignmentOverrideAuthorization.objects.select_for_update()
        .select_related("plan", "revision_basis", "evidence")
        .filter(
            pk=authorization_id,
            enrollment=enrollment,
            status=CurriculumAssignmentOverrideAuthorization.Status.APPROVED,
        )
        .first()
    )
    if authorization is None or not authorization.content_hash:
        raise StudentAdministrationError(
            "A sealed approved authorization is required.",
            code="student_admin_override_authorization_invalid",
        )
    plan = authorization.plan
    revision = authorization.revision_basis
    evidence = authorization.evidence
    reason_code = authorization.reason_code
    previous = enrollment.assignment_decisions.order_by("-created_at", "-id").first()
    input_data = (
        previous.input_data
        if previous
        else {
            "program_id": str(enrollment.program_id),
            "admission_date": enrollment.admission_term.starts_at.date().isoformat(),
            "context": CurriculumAssignmentContext.ADMISSION.value,
        }
    )
    envelope = {
        "method": CurriculumAssignmentMethod.ADMIN_OVERRIDE.value,
        "input": input_data,
        "previous_decision_hash": previous.decision_hash if previous else None,
        "selected_plan_id": str(plan.pk),
        "selected_revision_id": str(revision.pk),
        "authorization_id": str(authorization.pk),
        "authorization_content_hash": authorization.content_hash,
        "revision_content_hash": authorization.revision_content_hash,
        "revision_source_set_hash": authorization.revision_source_set_hash,
        "evidence_id": str(evidence.pk),
        "evidence_snapshot_id": str(authorization.sealed_snapshot_id),
        "evidence_snapshot_sha256": authorization.sealed_snapshot_sha256,
        "evidence_excerpt_hash": authorization.sealed_excerpt_hash,
        "reason_code": reason_code,
        "decided_by": actor.pk,
    }
    decision_hash = canonical_content_hash(envelope)
    remaining_review_reasons = [
        reason for reason in enrollment.review_reasons if reason != "CURRICULUM_ASSIGNMENT"
    ]
    enrollment.plan = plan
    enrollment.revision_basis = revision
    enrollment.review_reasons = remaining_review_reasons
    enrollment.status = (
        EnrollmentStatus.NEEDS_REVIEW.value
        if remaining_review_reasons
        else EnrollmentStatus.ACTIVE.value
    )
    enrollment.save(
        update_fields=("plan", "revision_basis", "review_reasons", "status", "updated_at")
    )
    CurriculumAssignmentDecision.objects.create(
        enrollment=enrollment,
        status=CurriculumAssignmentDecisionStatus.RESOLVED.value,
        method=CurriculumAssignmentMethod.ADMIN_OVERRIDE.value,
        resolver_version="admin-override-v1",
        input_data=input_data,
        reason_codes=["GOVERNED_ADMIN_OVERRIDE"],
        candidates=[],
        selected_plan=plan,
        selected_revision=revision,
        decision_hash=decision_hash,
        override_reason_code=reason_code,
        override_evidence=evidence,
        override_authorization=authorization,
        decided_by=actor,
    )
    record_audit_event(
        request,
        action="CURRICULUM_ASSIGNMENT_OVERRIDDEN",
        actor=actor,
        object_type="ProgramEnrollment",
        object_id=enrollment.pk,
        institution_id=enrollment.student.institution_id,
        metadata={
            "decision_hash": decision_hash,
            "reason_code": reason_code,
            "evidence_id": str(evidence.pk),
            "authorization_id": str(authorization.pk),
            "plan_id": str(plan.pk),
            "revision_id": str(revision.pk),
        },
    )
    return enrollment


@transaction.atomic  # type: ignore[untyped-decorator]
def update_administered_identity(
    *,
    actor: Any,
    enrollment_id: UUID | str,
    first_name: str,
    middle_names: str,
    first_surname: str,
    second_surname: str,
    preferred_name: str,
    birth_date: date,
    rationale: str,
    expected_version: str | None,
    request: Any | None = None,
) -> ProgramEnrollment:
    if expected_version is None:
        raise StudentAdministrationError(
            "If-Match is required to rectify identity data.",
            code="student_admin_precondition_required",
        )
    try:
        enrollment = (
            ProgramEnrollment.objects.select_for_update()
            .select_related(
                "student__user",
                "student__institution",
                "program",
                "plan",
                "admission_term",
            )
            .get(pk=enrollment_id)
        )
    except ProgramEnrollment.DoesNotExist as exc:
        raise StudentAdministrationError(
            "Enrollment was not found.", code="student_admin_reference_not_found"
        ) from exc
    if not _can_administer(
        actor, enrollment.student.institution_id, program_id=enrollment.program_id
    ):
        raise StudentAdministrationError(
            "You cannot administer this identity.", code="student_admin_forbidden"
        )
    if settings.PRIVILEGED_MFA_REQUIRED and not getattr(actor, "_privileged_mfa_verified", False):
        raise StudentAdministrationError(
            "A recent privileged authentication is required to rectify identity.",
            code="student_admin_step_up_required",
        )
    User.objects.select_for_update().get(pk=enrollment.student.user_id)
    person_existed = True
    try:
        person = PersonProfile.objects.select_for_update().get(user_id=enrollment.student.user_id)
    except PersonProfile.DoesNotExist:
        person_existed = False
        if expected_version.strip('"') != enrollment.student.updated_at.isoformat():
            raise StudentAdministrationError(
                "Identity data changed since it was reviewed.",
                code="student_admin_stale_resource",
            ) from None
        person = PersonProfile.objects.create(
            user=enrollment.student.user,
            data_status=IdentityDataStatus.LEGACY_UNSTRUCTURED,
            metadata={
                "created_for_legacy_student_profile": str(enrollment.student_id),
            },
        )
    if person_existed and expected_version.strip('"') != person.updated_at.isoformat():
        raise StudentAdministrationError(
            "Identity data changed since it was reviewed.",
            code="student_admin_stale_resource",
        )
    note = rationale.strip()
    if len(note) < 3:
        raise StudentAdministrationError(
            "Select the verified basis for this identity rectification.",
            code="student_admin_rationale_required",
        )
    allowed_reason_codes = {
        "AUTHORIZED_SOURCE_VERIFIED",
        "DATA_ENTRY_CORRECTION",
        "STUDENT_REQUEST_VERIFIED",
        "OTHER_VERIFIED",
    }
    reason_code = note if note in allowed_reason_codes else "OTHER_VERIFIED"
    previous = {
        "first_name": person.first_name,
        "middle_names": person.middle_names,
        "first_surname": person.first_surname,
        "second_surname": person.second_surname,
        "preferred_name": person.preferred_name,
        "birth_date": person.birth_date,
    }
    person.first_name = first_name
    person.middle_names = middle_names
    person.first_surname = first_surname
    person.second_surname = second_surname
    person.preferred_name = preferred_name
    person.birth_date = birth_date
    person.birth_date_purpose = BirthDatePurpose.ACADEMIC_ADMINISTRATION
    person.data_status = IdentityDataStatus.CONFIRMED
    person.verification_method = IdentityVerificationMethod.INSTITUTION_VERIFIED
    person.confirmed_at = timezone.now()
    try:
        person.save()
    except ValidationError as exc:
        raise StudentAdministrationError(
            "; ".join(exc.messages), code="student_admin_validation"
        ) from exc
    current = {
        "first_name": person.first_name,
        "middle_names": person.middle_names,
        "first_surname": person.first_surname,
        "second_surname": person.second_surname,
        "preferred_name": person.preferred_name,
        "birth_date": person.birth_date,
    }
    changed_fields = sorted(field for field in previous if previous[field] != current[field])
    remaining_review_reasons = [
        reason for reason in enrollment.review_reasons if reason != "IDENTITY_REVIEW"
    ]
    if remaining_review_reasons != enrollment.review_reasons:
        enrollment.review_reasons = remaining_review_reasons
        enrollment.status = (
            EnrollmentStatus.NEEDS_REVIEW.value
            if remaining_review_reasons
            else EnrollmentStatus.ACTIVE.value
        )
        enrollment.save(update_fields=("review_reasons", "status", "updated_at"))
    record_audit_event(
        request,
        action="PERSON_IDENTITY_RECTIFIED",
        actor=actor,
        object_type="PersonProfile",
        object_id=person.pk,
        institution_id=enrollment.student.institution_id,
        metadata={
            "student_profile_id": str(enrollment.student_id),
            "changed_fields": changed_fields,
            "reason_code": reason_code,
        },
    )
    return enrollment


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
        "student__user__person_profile", "program", "plan", "admission_term"
    )
    normalized_search = search.strip()
    if normalized_search:
        query = query.filter(
            Q(student__user__email__icontains=normalized_search)
            | Q(student__legacy_display_name__icontains=normalized_search)
            | Q(student__user__person_profile__first_name__icontains=normalized_search)
            | Q(student__user__person_profile__middle_names__icontains=normalized_search)
            | Q(student__user__person_profile__first_surname__icontains=normalized_search)
            | Q(student__user__person_profile__second_surname__icontains=normalized_search)
            | Q(student__user__person_profile__preferred_name__icontains=normalized_search)
            | Q(student__student_number__icontains=normalized_search)
        )
    safe_limit = min(max(limit, 1), 100)
    safe_offset = max(offset, 0)
    total = query.count()
    ordered = query.order_by(
        "student__user__person_profile__first_surname",
        "student__user__person_profile__second_surname",
        "student__user__person_profile__first_name",
        "student__legacy_display_name",
        "student__user__email",
        "id",
    )
    items = [
        administered_enrollment_summary_view(enrollment)
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
    first_name: str | None,
    middle_names: str | None,
    first_surname: str | None,
    second_surname: str | None,
    preferred_name: str | None,
    birth_date: date | None,
    display_name: str | None = None,
    student_number: str,
    institution_id: UUID,
    program_id: UUID,
    plan_id: UUID | None,
    revision_basis_id: UUID | None,
    admission_term_id: UUID,
    cohort_code: str | None = None,
    assignment_context: str = CurriculumAssignmentContext.ADMISSION.value,
    expected_assignment_hash: str | None = None,
    previous_plan_id: UUID | None = None,
    admission_verification_method: str = AdmissionFactVerificationMethod.SOURCE_SNAPSHOT.value,
    admission_record_reference: str | None = None,
    request: Any | None = None,
) -> ProgramEnrollment:
    if not _can_administer(actor, institution_id, program_id=program_id):
        raise StudentAdministrationError(
            "You cannot administer students for this institution.",
            code="student_admin_forbidden",
        )
    if settings.PRIVILEGED_MFA_REQUIRED and not getattr(actor, "_privileged_mfa_verified", False):
        raise StudentAdministrationError(
            "Privileged authentication is required to create a verified identity.",
            code="student_admin_step_up_required",
        )
    if (
        assignment_context != CurriculumAssignmentContext.ADMISSION.value
        or previous_plan_id is not None
    ):
        raise StudentAdministrationError(
            "New accounts support admission only; use the existing-student workflow for later contexts.",
            code="student_admin_validation",
        )
    if admission_verification_method not in {
        item.value for item in AdmissionFactVerificationMethod
    }:
        raise StudentAdministrationError(
            "Admission verification method is not supported.",
            code="student_admin_validation",
        )
    normalized_email = User.objects.normalize_email(email.strip()).lower()
    if User.objects.filter(email__iexact=normalized_email).exists():
        raise StudentAdministrationError(
            "An account already exists for this email.", code="student_account_exists"
        )
    try:
        institution = Institution.objects.get(pk=institution_id)
        program = Program.objects.select_related("faculty__campus").get(pk=program_id)
        term = AcademicTerm.objects.select_related("source_snapshot").get(pk=admission_term_id)
    except (
        Institution.DoesNotExist,
        Program.DoesNotExist,
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
    if term.institution_id != institution.pk or (
        term.campus_id is not None and term.campus_id != campus.pk
    ):
        raise StudentAdministrationError(
            "Admission term does not belong to the selected institution and campus.",
            code="student_admin_scope_mismatch",
        )
    if (
        previous_plan_id
        and not CurriculumPlan.objects.filter(pk=previous_plan_id, program=program).exists()
    ):
        raise StudentAdministrationError(
            "Previous plan does not belong to the selected program.",
            code="student_admin_scope_mismatch",
        )
    try:
        admission_date = term.starts_at.astimezone(ZoneInfo(campus.timezone)).date()
    except ZoneInfoNotFoundError as exc:
        raise StudentAdministrationError(
            "The campus timezone is not configured correctly.",
            code="student_admin_configuration_invalid",
        ) from exc
    assignment = resolve_assignment_preview(
        program_id=program.pk,
        admission_date=admission_date,
        context=assignment_context,
        cohort_code=(cohort_code or "").strip(),
        previous_plan_id=previous_plan_id,
        admission_source_snapshot_id=term.source_snapshot_id,
        admission_source_sha256=(term.source_snapshot.sha256 if term.source_snapshot_id else None),
        admission_verification_method=admission_verification_method,
        admission_record_reference_hash=(
            digest_identifier(
                "admission-record:" + " ".join((admission_record_reference or "").split())
            )
            if (admission_record_reference or "").strip()
            else None
        ),
    )
    if expected_assignment_hash and assignment["decision_hash"] != expected_assignment_hash:
        raise StudentAdministrationError(
            "Curriculum assignment changed after preview; review it again.",
            code="student_admin_stale_resource",
        )
    automatic_assignment = assignment["status"] == "RESOLVED"
    if automatic_assignment and expected_assignment_hash is None:
        raise StudentAdministrationError(
            "Preview the curriculum assignment before creating the enrollment.",
            code="student_admin_precondition_required",
        )
    if automatic_assignment:
        resolved_plan_id = UUID(str(assignment["selected_plan_id"]))
        resolved_revision_id = UUID(str(assignment["selected_revision_id"]))
        if plan_id and plan_id != resolved_plan_id:
            raise StudentAdministrationError(
                "Selected plan conflicts with the verified assignment policy.",
                code="student_admin_scope_mismatch",
            )
        if revision_basis_id and revision_basis_id != resolved_revision_id:
            raise StudentAdministrationError(
                "Selected revision conflicts with the verified assignment policy.",
                code="student_admin_scope_mismatch",
            )
        plan_id = resolved_plan_id
        revision_basis_id = resolved_revision_id
    else:
        # Compatibility fields are deliberately ignored for unresolved cases. A caller cannot
        # turn an unverified proposal into enrollment state through this endpoint.
        plan_id = None
        revision_basis_id = None
    plan = None
    revision = None
    if automatic_assignment:
        try:
            plan = CurriculumPlan.objects.get(pk=plan_id)
            revision = CurriculumRevision.objects.get(pk=revision_basis_id)
        except (CurriculumPlan.DoesNotExist, CurriculumRevision.DoesNotExist) as exc:
            raise StudentAdministrationError(
                "The assigned plan or revision no longer exists.",
                code="student_admin_reference_not_found",
            ) from exc
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
    first_name = first_name or ""
    middle_names = middle_names or ""
    first_surname = first_surname or ""
    second_surname = second_surname or ""
    preferred_name = preferred_name or ""
    normalized_legacy_name = " ".join((display_name or "").split())
    structured_values_supplied = (
        any(
            value.strip()
            for value in (first_name, middle_names, first_surname, second_surname, preferred_name)
        )
        or birth_date is not None
    )
    structured_identity_complete = bool(
        first_name.strip() and first_surname.strip() and birth_date is not None
    )
    if structured_values_supplied and not structured_identity_complete:
        raise StudentAdministrationError(
            "Structured identity requires first name, first surname and birth date.",
            code="student_admin_validation",
        )
    if not structured_identity_complete and not normalized_legacy_name:
        raise StudentAdministrationError(
            "Provide the structured identity fields.", code="student_admin_validation"
        )

    user = User(email=normalized_email, is_active=True)
    person = PersonProfile(
        user=user,
        first_name=first_name if structured_identity_complete else "",
        middle_names=middle_names if structured_identity_complete else "",
        first_surname=first_surname if structured_identity_complete else "",
        second_surname=second_surname if structured_identity_complete else "",
        preferred_name=preferred_name if structured_identity_complete else "",
        birth_date=birth_date if structured_identity_complete else None,
        birth_date_purpose=(
            BirthDatePurpose.ACADEMIC_ADMINISTRATION if structured_identity_complete else ""
        ),
        data_status=(
            IdentityDataStatus.CONFIRMED
            if structured_identity_complete
            else IdentityDataStatus.LEGACY_UNSTRUCTURED
        ),
        verification_method=(
            IdentityVerificationMethod.INSTITUTION_VERIFIED
            if structured_identity_complete
            else IdentityVerificationMethod.LEGACY_UNKNOWN
        ),
        confirmed_at=timezone.now() if structured_identity_complete else None,
        metadata={
            "created_via": "native_student_administration",
            "legacy_contract_compatibility": not structured_identity_complete,
        },
    )
    try:
        user.full_clean(exclude=["password"])
        validate_password(temporary_password, user)
        person.full_clean(exclude=["user"])
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
        person.user = user
        person.save()
        student = StudentProfile.objects.create(
            user=user,
            institution=institution,
            student_number=student_number.strip(),
            legacy_display_name=normalized_legacy_name,
            metadata={"created_via": "native_student_administration"},
        )
    except IntegrityError as exc:
        raise StudentAdministrationError(
            "An account or student number already exists.",
            code="student_account_exists",
        ) from exc
    review_reasons = []
    if not automatic_assignment:
        review_reasons.append("CURRICULUM_ASSIGNMENT")
    if not structured_identity_complete:
        review_reasons.append("IDENTITY_REVIEW")
    enrollment_status = (
        EnrollmentStatus.NEEDS_REVIEW.value if review_reasons else EnrollmentStatus.ACTIVE.value
    )
    enrollment = ProgramEnrollment.objects.create(
        student=student,
        program=program,
        plan=plan if automatic_assignment else None,
        revision_basis=revision if automatic_assignment else None,
        admission_term=term,
        status=enrollment_status,
        cohort_code=(cohort_code or "").strip(),
        review_reasons=review_reasons,
    )
    StudentOnboarding.objects.create(enrollment=enrollment)
    CurriculumAssignmentDecision.objects.create(
        enrollment=enrollment,
        policy_id=assignment["selected_policy_id"] if automatic_assignment else None,
        status=assignment["status"],
        method=(
            CurriculumAssignmentMethod.AUTOMATIC.value
            if automatic_assignment
            else CurriculumAssignmentMethod.POLICY_EVALUATION.value
        ),
        resolver_version=assignment["resolver_version"],
        input_data=assignment["input"],
        reason_codes=assignment["reason_codes"],
        candidates=assignment["candidates"],
        selected_plan=plan if automatic_assignment else None,
        selected_revision=revision if automatic_assignment else None,
        decision_hash=assignment["decision_hash"],
        override_reason_code="",
        decided_by=actor,
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
            "plan_id": str(plan.pk) if plan else None,
            "admission_term_id": str(term.pk),
            "assignment_status": assignment["status"],
            "assignment_reason_codes": assignment["reason_codes"],
            "assignment_decision_hash": assignment["decision_hash"],
            "assignment_method": (
                CurriculumAssignmentMethod.AUTOMATIC.value
                if automatic_assignment
                else CurriculumAssignmentMethod.POLICY_EVALUATION.value
            ),
            "enrollment_status": enrollment_status,
        },
    )
    return enrollment
