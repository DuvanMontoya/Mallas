from __future__ import annotations

from django.db import migrations
from django.utils import timezone


def normalize_historical_onboarding(apps: object, schema_editor: object) -> None:
    del schema_editor
    enrollment_model = apps.get_model("student_records", "ProgramEnrollment")  # type: ignore[attr-defined]
    onboarding_model = apps.get_model("student_records", "StudentOnboarding")  # type: ignore[attr-defined]
    completed_at = timezone.now()
    student_ids = enrollment_model.objects.values_list("student_id", flat=True).distinct()
    for student_id in student_ids.iterator():
        preferred_id = (
            enrollment_model.objects.filter(
                student_id=student_id,
                status__in=("ACTIVE", "NEEDS_REVIEW"),
            )
            .order_by("-admission_term__starts_at", "-created_at", "id")
            .values_list("id", flat=True)
            .first()
        )
        pending = onboarding_model.objects.filter(
            enrollment__student_id=student_id,
            completed_at__isnull=True,
        )
        if preferred_id is not None:
            pending = pending.exclude(enrollment_id=preferred_id)
        pending.update(completed_at=completed_at, updated_at=completed_at)


class Migration(migrations.Migration):
    dependencies = [("student_records", "0019_prepared_override_authorization_guard")]

    operations = [migrations.RunPython(normalize_historical_onboarding, migrations.RunPython.noop)]
