from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from domain.enums import RevisionStatus, UserRole
from modules.curriculum.models import CurriculumRevision
from modules.identity.models import RoleAssignment
from modules.student_records.models import (
    ProgramEnrollment,
    StudentAdvisorAssignment,
    StudentProfile,
)


def _is_authenticated(user: Any) -> bool:
    return bool(getattr(user, "is_authenticated", False) and getattr(user, "is_active", False))


def active_role_assignments(user: Any, *, at: Any | None = None) -> list[RoleAssignment]:
    if not _is_authenticated(user) or not getattr(user, "pk", None):
        return []
    moment = at or timezone.now()
    return list(
        RoleAssignment.objects.filter(user_id=user.pk, active=True)
        .filter(Q(valid_from__isnull=True) | Q(valid_from__lte=moment))
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=moment))
        .select_related("institution", "program")
        .order_by("role", "created_at", "id")
    )


def has_role(
    user: Any,
    role: UserRole | str,
    *,
    institution_id: Any | None = None,
    program_id: Any | None = None,
) -> bool:
    if not _is_authenticated(user):
        return False
    role_value = role.value if isinstance(role, UserRole) else role
    if getattr(user, "is_superuser", False) and role_value == UserRole.ADMIN.value:
        return True
    for assignment in active_role_assignments(user):
        if assignment.role != role_value:
            continue
        if institution_id is not None and assignment.institution_id not in (None, institution_id):
            continue
        if program_id is not None and assignment.program_id not in (None, program_id):
            continue
        return True
    return False


def roles_for(user: Any) -> tuple[str, ...]:
    roles = {assignment.role for assignment in active_role_assignments(user)}
    if getattr(user, "is_superuser", False):
        roles.add(UserRole.ADMIN.value)
    return tuple(sorted(roles))


def can_view_student(user: Any, student: StudentProfile) -> bool:
    """Return whether ``user`` may read this student's private records."""

    if not _is_authenticated(user):
        return False
    if student.user_id == user.pk:
        return True
    if has_role(user, UserRole.ADMIN, institution_id=student.institution_id):
        return True
    if not has_role(user, UserRole.ADVISOR, institution_id=student.institution_id):
        return False
    moment = timezone.now()
    return (
        StudentAdvisorAssignment.objects.filter(
            student_id=student.pk,
            advisor_id=user.pk,
            active=True,
        )
        .filter(Q(valid_from__isnull=True) | Q(valid_from__lte=moment))
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=moment))
        .exists()
    )


def can_view_enrollment(user: Any, enrollment: ProgramEnrollment) -> bool:
    return can_view_student(user, enrollment.student)


def can_edit_student_history(user: Any, student: StudentProfile) -> bool:
    if not _is_authenticated(user):
        return False
    if student.user_id == user.pk:
        return True
    return has_role(user, UserRole.ADMIN, institution_id=student.institution_id)


def can_edit_revision(user: Any, revision: CurriculumRevision) -> bool:
    """Editors/reviewers may work on drafts, never on published content."""

    if revision.status in {
        RevisionStatus.PUBLISHED.value,
        RevisionStatus.SUPERSEDED.value,
        RevisionStatus.RETIRED.value,
    }:
        return False
    program_id = revision.plan.program_id
    institution_id = revision.plan.program.faculty.campus.institution_id
    return any(
        has_role(user, role, institution_id=institution_id, program_id=program_id)
        for role in (UserRole.EDITOR, UserRole.REVIEWER, UserRole.ADMIN)
    )


def can_publish_revision(user: Any, revision: CurriculumRevision) -> bool:
    """Publishing is reserved for reviewers/admins, never editor-only users."""

    if revision.status not in {
        RevisionStatus.DRAFT.value,
        RevisionStatus.IN_REVIEW.value,
        RevisionStatus.APPROVED.value,
    }:
        return False
    if settings.PRIVILEGED_MFA_REQUIRED and not getattr(user, "_privileged_mfa_verified", False):
        return False
    program_id = revision.plan.program_id
    institution_id = revision.plan.program.faculty.campus.institution_id
    return has_role(
        user, UserRole.REVIEWER, institution_id=institution_id, program_id=program_id
    ) or has_role(user, UserRole.ADMIN, institution_id=institution_id, program_id=program_id)


def can_manage_revision_lifecycle(user: Any, revision: CurriculumRevision) -> bool:
    """Allow reviewer/admin lifecycle actions without allowing content edits."""

    institution_id = revision.plan.program.faculty.campus.institution_id
    program_id = revision.plan.program_id
    if settings.PRIVILEGED_MFA_REQUIRED and not getattr(user, "_privileged_mfa_verified", False):
        return False
    return has_role(
        user, UserRole.REVIEWER, institution_id=institution_id, program_id=program_id
    ) or has_role(user, UserRole.ADMIN, institution_id=institution_id, program_id=program_id)


def can_view_audit_for_enrollment(user: Any, enrollment: ProgramEnrollment) -> bool:
    return can_view_enrollment(user, enrollment)
