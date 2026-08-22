from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from modules.identity.application.audit import record_audit_event
from modules.offerings.models import AcademicTerm
from modules.student_records.models import StudentOnboarding


class StudentOnboardingError(ValueError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _state_for_user(user: Any, *, lock: bool = False) -> StudentOnboarding:
    try:
        _ = user.student_profile.pk
    except ObjectDoesNotExist as exc:
        raise StudentOnboardingError(
            "Se requiere un perfil de estudiante para la configuración inicial.",
            code="onboarding_student_required",
        ) from exc
    query = StudentOnboarding.objects.select_related(
        "enrollment__student",
        "enrollment__program",
        "enrollment__plan",
        "enrollment__revision_basis",
        "enrollment__admission_term",
        "current_term",
    ).filter(enrollment__student__user_id=user.pk)
    if lock:
        # PostgreSQL cannot apply an unrestricted FOR UPDATE to the nullable
        # sides introduced by plan, revision, term and current-term joins.
        # The onboarding row is the concurrency boundary; related academic
        # records are read-only in this transaction.
        query = query.select_for_update(of=("self",))
    state = query.order_by(
        F("completed_at").asc(nulls_first=True),
        "-enrollment__admission_term__starts_at",
        "id",
    ).first()
    if state is None:
        raise StudentOnboardingError(
            "Esta cuenta no tiene un flujo de configuración inicial pendiente.",
            code="onboarding_not_available",
        )
    return state


def _onboarding_state_view(state: StudentOnboarding) -> dict[str, Any]:
    enrollment = state.enrollment
    latest_decision = enrollment.assignment_decisions.order_by("-created_at", "-id").first()
    return {
        "enrollment_id": enrollment.pk,
        "program_name": enrollment.program.name,
        "program_code": enrollment.program.code,
        "admission_term_code": enrollment.admission_term.code,
        "enrollment_status": enrollment.status,
        "plan_code": enrollment.plan.code if enrollment.plan_id else None,
        "revision_code": (
            enrollment.revision_basis.revision_code if enrollment.revision_basis_id else None
        ),
        "assignment_reason_codes": latest_decision.reason_codes if latest_decision else [],
        "identity_confirmed": state.identity_confirmed_at is not None,
        "history_step_status": state.history_step_status,
        "current_term_id": state.current_term_id,
        "planning_load_target": state.planning_load_target,
        "tour_status": state.tour_status,
        "completed": state.is_complete,
        "version": state.updated_at.isoformat(),
    }


def onboarding_view(user: Any) -> dict[str, Any]:
    return _onboarding_state_view(_state_for_user(user))


@transaction.atomic  # type: ignore[untyped-decorator]
def update_onboarding(
    *,
    user: Any,
    expected_version: str | None,
    identity_confirmed: bool,
    history_step_status: str,
    current_term_id: UUID,
    planning_load_target: int,
    tour_status: str,
    complete: bool,
    request: Any | None = None,
) -> dict[str, Any]:
    if expected_version is None:
        raise StudentOnboardingError(
            "If-Match is required to update onboarding.", code="onboarding_precondition_required"
        )
    state = _state_for_user(user, lock=True)
    try:
        expected_updated_at = datetime.fromisoformat(
            expected_version.strip('"').replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise StudentOnboardingError(
            "The onboarding version is invalid.", code="onboarding_stale_resource"
        ) from exc
    if expected_updated_at != state.updated_at:
        raise StudentOnboardingError(
            "Onboarding changed in another session.", code="onboarding_stale_resource"
        )
    if state.completed_at is not None:
        raise StudentOnboardingError(
            "Onboarding is already complete.", code="onboarding_already_complete"
        )
    if history_step_status not in {"IMPORTED", "SKIPPED"}:
        raise StudentOnboardingError(
            "Choose whether history was imported or will be completed later.",
            code="onboarding_history_disposition_required",
        )
    if tour_status not in {"COMPLETED", "SKIPPED"}:
        raise StudentOnboardingError(
            "Complete or skip the interface tour.", code="onboarding_tour_disposition_required"
        )
    if not 1 <= planning_load_target <= 30:
        raise StudentOnboardingError(
            "Planning load must be between 1 and 30 credits.", code="onboarding_load_invalid"
        )
    enrollment = state.enrollment
    try:
        current_term = AcademicTerm.objects.get(pk=current_term_id)
    except AcademicTerm.DoesNotExist as exc:
        raise StudentOnboardingError(
            "The selected academic term no longer exists.", code="onboarding_term_not_found"
        ) from exc
    campus_id = enrollment.program.faculty.campus_id
    if current_term.institution_id != enrollment.student.institution_id or (
        current_term.campus_id is not None and current_term.campus_id != campus_id
    ):
        raise StudentOnboardingError(
            "The selected term is outside the enrollment scope.", code="onboarding_term_scope"
        )
    state.identity_confirmed_at = timezone.now() if identity_confirmed else None
    state.history_step_status = history_step_status
    state.current_term = current_term
    state.planning_load_target = planning_load_target
    state.tour_status = tour_status
    if complete:
        if not identity_confirmed:
            raise StudentOnboardingError(
                "Confirm the identity step before completing onboarding.",
                code="onboarding_identity_required",
            )
        state.completed_at = timezone.now()
    state.save()
    record_audit_event(
        request,
        action="STUDENT_ONBOARDING_UPDATED",
        actor=user,
        object_type="StudentOnboarding",
        object_id=state.pk,
        institution_id=enrollment.student.institution_id,
        metadata={
            "enrollment_id": str(enrollment.pk),
            "history_step_status": state.history_step_status,
            "current_term_id": str(state.current_term_id),
            "planning_load_target": state.planning_load_target,
            "tour_status": state.tour_status,
            "completed": state.is_complete,
        },
    )
    return _onboarding_state_view(state)
