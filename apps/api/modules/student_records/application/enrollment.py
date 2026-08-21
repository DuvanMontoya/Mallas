from __future__ import annotations

from typing import Any

from django.db.models import Case, IntegerField, QuerySet, Value, When

from modules.student_records.models import ProgramEnrollment

PREFERRED_ENROLLMENT_STATUSES = (
    "ACTIVE",
    "NEEDS_REVIEW",
    "COMPLETED",
    "SUSPENDED",
    "WITHDRAWN",
    "TRANSITIONED",
)


def preferred_enrollment_queryset(user_id: Any) -> QuerySet[ProgramEnrollment]:
    """Return a user's enrollment candidates in the product's explicit priority order.

    The previous implementation issued one indexed query per status until it
    found a row.  Keeping the priority as a SQL expression preserves the
    observable selection rule while making the read a single database round
    trip, including the no-enrollment case.
    """

    status_priority = Case(
        *(
            When(status=status, then=Value(priority))
            for priority, status in enumerate(PREFERRED_ENROLLMENT_STATUSES)
        ),
        output_field=IntegerField(),
    )
    return (
        ProgramEnrollment.objects.select_related(
            "student__user", "program", "plan", "revision_basis"
        )
        .filter(student__user_id=user_id, status__in=PREFERRED_ENROLLMENT_STATUSES)
        .annotate(_status_priority=status_priority)
        .order_by("_status_priority", "-created_at")
    )


def preferred_enrollment_for_user(user_id: Any) -> ProgramEnrollment | None:
    return preferred_enrollment_queryset(user_id).first()
