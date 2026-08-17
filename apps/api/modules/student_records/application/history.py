from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from domain.enums import AttemptOrigin, AttemptStatus
from modules.audit.application.services import run_degree_audit
from modules.curriculum.models import CourseVersion
from modules.identity.application.audit import record_audit_event
from modules.identity.application.authorization import (
    can_edit_student_history,
    can_view_enrollment,
)
from modules.offerings.models import AcademicTerm
from modules.student_records.models import CourseAttempt, ProgramEnrollment


class HistoryMutationError(RuntimeError):
    """Explainable failure for an authorized history mutation."""

    def __init__(self, message: str, *, code: str = "history_invalid") -> None:
        super().__init__(message)
        self.code = code


def get_enrollment_for_view(actor: Any, enrollment_id: UUID | str) -> ProgramEnrollment:
    try:
        enrollment = ProgramEnrollment.objects.select_related(
            "student",
            "student__user",
            "program__faculty__campus",
            "revision_basis",
        ).get(pk=enrollment_id)
    except ProgramEnrollment.DoesNotExist as exc:
        raise HistoryMutationError(
            "Enrollment was not found.", code="enrollment_not_found"
        ) from exc
    if not can_view_enrollment(actor, enrollment):
        raise HistoryMutationError(
            "You cannot view this student's history.", code="history_forbidden"
        )
    return enrollment


def get_attempt_for_view(actor: Any, attempt_id: UUID | str) -> CourseAttempt:
    try:
        attempt = CourseAttempt.objects.select_related(
            "enrollment__student", "course_version__course", "term", "import_batch"
        ).get(pk=attempt_id)
    except CourseAttempt.DoesNotExist as exc:
        raise HistoryMutationError("Attempt was not found.", code="attempt_not_found") from exc
    if not can_view_enrollment(actor, attempt.enrollment):
        raise HistoryMutationError("You cannot view this attempt.", code="history_forbidden")
    return attempt


def _editable_enrollment(actor: Any, enrollment_id: UUID | str) -> ProgramEnrollment:
    enrollment = get_enrollment_for_view(actor, enrollment_id)
    if not can_edit_student_history(actor, enrollment.student):
        raise HistoryMutationError(
            "You cannot edit this student's history.", code="history_forbidden"
        )
    return enrollment


def _course_version(
    enrollment: ProgramEnrollment,
    *,
    course_version_id: UUID | str | None = None,
    course_code: str = "",
) -> CourseVersion:
    query = CourseVersion.objects.filter(course__institution_id=enrollment.student.institution_id)
    if course_version_id is not None:
        query = query.filter(pk=course_version_id)
    elif course_code:
        query = query.filter(course__code__iexact=course_code.strip())
    else:
        raise HistoryMutationError(
            "course_version_id or course_code is required.", code="course_required"
        )
    course_version = query.select_related("course").order_by("-valid_from", "-created_at").first()
    if course_version is None:
        raise HistoryMutationError(
            "Course does not belong to the student's institution.", code="course_forbidden"
        )
    return course_version


def _term(
    enrollment: ProgramEnrollment,
    *,
    term_id: UUID | str | None = None,
    term_code: str = "",
) -> AcademicTerm:
    query = AcademicTerm.objects.filter(institution_id=enrollment.student.institution_id)
    if term_id is not None:
        query = query.filter(pk=term_id)
    elif term_code:
        query = query.filter(code=term_code.strip())
    else:
        raise HistoryMutationError("term_id or term_code is required.", code="term_required")
    term = query.first()
    if term is None:
        raise HistoryMutationError(
            "Academic term does not belong to the student's institution.", code="term_forbidden"
        )
    return term


def _status(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in {member.value for member in AttemptStatus}:
        raise HistoryMutationError("Unsupported attempt status.", code="status_invalid")
    return normalized


def _grade(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise HistoryMutationError("Grade must be a decimal number.", code="grade_invalid") from exc
    if not result.is_finite() or result < 0 or result > 5:
        raise HistoryMutationError("Grade must be between 0 and 5.", code="grade_invalid")
    return result


def _credits(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise HistoryMutationError(
            "credits_earned must be an integer.", code="credits_invalid"
        ) from exc
    if result < 0:
        raise HistoryMutationError("credits_earned cannot be negative.", code="credits_invalid")
    return result


def _audit(enrollment: ProgramEnrollment) -> str:
    _, run, _ = run_degree_audit(enrollment.pk)
    return str(run.pk)


def _version_token(attempt: CourseAttempt) -> str:
    return attempt.updated_at.isoformat()


@transaction.atomic  # type: ignore[untyped-decorator]
def create_manual_attempt(
    *,
    actor: Any,
    enrollment_id: UUID | str,
    course_version_id: UUID | str | None = None,
    course_code: str = "",
    term_id: UUID | str | None = None,
    term_code: str = "",
    status: str,
    grade: Any = None,
    credits_earned: Any = None,
    attempt_number: int | None = None,
    notes: str = "",
    request: Any | None = None,
) -> tuple[CourseAttempt, str]:
    enrollment = _editable_enrollment(actor, enrollment_id)
    course_version = _course_version(
        enrollment, course_version_id=course_version_id, course_code=course_code
    )
    term = _term(enrollment, term_id=term_id, term_code=term_code)
    normalized_status = _status(status)
    if normalized_status == AttemptStatus.ANNULLED.value:
        raise HistoryMutationError(
            "Use the dedicated annul operation to preserve audit semantics.",
            code="annul_operation_required",
        )
    requested_number = attempt_number or 1
    if requested_number < 1:
        raise HistoryMutationError(
            "attempt_number must be positive.", code="attempt_number_invalid"
        )
    if CourseAttempt.objects.filter(
        enrollment=enrollment, course_version=course_version, attempt_number=requested_number
    ).exists():
        raise HistoryMutationError(
            "An attempt with this course and attempt_number already exists; edit or use a new number.",
            code="attempt_duplicate",
        )
    attempt = CourseAttempt(
        enrollment=enrollment,
        course_version=course_version,
        term=term,
        attempt_number=requested_number,
        status=normalized_status,
        grade=_grade(grade),
        credits_earned=_credits(credits_earned),
        origin=AttemptOrigin.MANUAL.value,
        entered_by=actor,
        notes=notes.strip()[:2_000],
    )
    attempt.full_clean()
    attempt.save()
    audit_run_id = _audit(enrollment)
    record_audit_event(
        request,
        action="HISTORY_ATTEMPT_CREATED",
        actor=actor,
        object_type="CourseAttempt",
        object_id=attempt.pk,
        institution_id=enrollment.student.institution_id,
        metadata={"enrollment_id": str(enrollment.pk), "audit_run_id": audit_run_id},
    )
    return attempt, audit_run_id


@transaction.atomic  # type: ignore[untyped-decorator]
def update_attempt(
    *,
    actor: Any,
    attempt_id: UUID | str,
    changes: dict[str, Any],
    expected_version: str | None = None,
    request: Any | None = None,
) -> tuple[CourseAttempt, str]:
    # Lock only the base row; ``import_batch`` is nullable and PostgreSQL rejects
    # a FOR UPDATE that implicitly includes the nullable side of a join.
    try:
        locked = CourseAttempt.objects.select_for_update().get(pk=attempt_id)
    except CourseAttempt.DoesNotExist as exc:
        raise HistoryMutationError("Attempt was not found.", code="attempt_not_found") from exc
    attempt = get_attempt_for_view(actor, locked.pk)
    if not can_edit_student_history(actor, attempt.enrollment.student):
        raise HistoryMutationError(
            "You cannot edit this student's history.", code="history_forbidden"
        )
    if expected_version is not None and expected_version.strip('"') != _version_token(attempt):
        raise HistoryMutationError(
            "The attempt changed since it was read; reload it before editing.",
            code="stale_resource",
        )
    if not changes:
        raise HistoryMutationError("At least one editable field is required.", code="no_changes")
    allowed = {
        "status",
        "grade",
        "credits_earned",
        "notes",
        "term_id",
        "term_code",
        "course_version_id",
    }
    unknown = sorted(set(changes) - allowed)
    if unknown:
        raise HistoryMutationError(
            f"Unsupported fields: {', '.join(unknown)}", code="mass_assignment_blocked"
        )
    if "status" in changes:
        next_status = _status(str(changes["status"]))
        if next_status == AttemptStatus.ANNULLED.value:
            raise HistoryMutationError(
                "Use the dedicated annul operation to preserve audit semantics.",
                code="annul_operation_required",
            )
        attempt.status = next_status
    if "grade" in changes:
        attempt.grade = _grade(changes["grade"])
    if "credits_earned" in changes:
        attempt.credits_earned = _credits(changes["credits_earned"])
    if "notes" in changes:
        attempt.notes = str(changes["notes"])[:2_000]
    if "course_version_id" in changes:
        attempt.course_version = _course_version(
            attempt.enrollment, course_version_id=changes["course_version_id"]
        )
    if "term_id" in changes or "term_code" in changes:
        attempt.term = _term(
            attempt.enrollment,
            term_id=changes.get("term_id"),
            term_code=str(changes.get("term_code", "")),
        )
    attempt.full_clean()
    update_fields: list[str] = [
        field
        for field in ("status", "grade", "credits_earned", "notes", "course_version", "term")
        if field in changes
        or (field == "course_version" and "course_version_id" in changes)
        or (field == "term" and ("term_id" in changes or "term_code" in changes))
    ]
    update_fields.append("updated_at")
    attempt.save(update_fields=update_fields)
    audit_run_id = _audit(attempt.enrollment)
    record_audit_event(
        request,
        action="HISTORY_ATTEMPT_UPDATED",
        actor=actor,
        object_type="CourseAttempt",
        object_id=attempt.pk,
        institution_id=attempt.enrollment.student.institution_id,
        metadata={"changed_fields": sorted(changes), "audit_run_id": audit_run_id},
    )
    return attempt, audit_run_id


@transaction.atomic  # type: ignore[untyped-decorator]
def annul_attempt(
    *,
    actor: Any,
    attempt_id: UUID | str,
    expected_version: str | None = None,
    request: Any | None = None,
) -> tuple[CourseAttempt, str]:
    try:
        locked = CourseAttempt.objects.select_for_update().get(pk=attempt_id)
    except CourseAttempt.DoesNotExist as exc:
        raise HistoryMutationError("Attempt was not found.", code="attempt_not_found") from exc
    attempt = get_attempt_for_view(actor, locked.pk)
    if not can_edit_student_history(actor, attempt.enrollment.student):
        raise HistoryMutationError(
            "You cannot edit this student's history.", code="history_forbidden"
        )
    if expected_version is not None and expected_version.strip('"') != _version_token(attempt):
        raise HistoryMutationError(
            "The attempt changed since it was read; reload it before editing.",
            code="stale_resource",
        )
    if attempt.status == AttemptStatus.ANNULLED.value:
        return attempt, _audit(attempt.enrollment)
    attempt.status = AttemptStatus.ANNULLED.value
    attempt.notes = (attempt.notes + "\nAnnulled by owner/admin at " + timezone.now().isoformat())[
        :2_000
    ]
    attempt.save(update_fields=["status", "notes", "updated_at"])
    audit_run_id = _audit(attempt.enrollment)
    record_audit_event(
        request,
        action="HISTORY_ATTEMPT_ANNULLED",
        actor=actor,
        object_type="CourseAttempt",
        object_id=attempt.pk,
        institution_id=attempt.enrollment.student.institution_id,
        metadata={"audit_run_id": audit_run_id},
    )
    return attempt, audit_run_id
