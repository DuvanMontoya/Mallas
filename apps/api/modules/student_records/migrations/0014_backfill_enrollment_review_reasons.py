from __future__ import annotations

from django.db import migrations


def backfill_review_reasons(apps: object, schema_editor: object) -> None:
    del schema_editor
    enrollment_model = apps.get_model("student_records", "ProgramEnrollment")  # type: ignore[attr-defined]
    enrollment_model.objects.filter(
        status="NEEDS_REVIEW", plan_id__isnull=True, review_reasons=[]
    ).update(review_reasons=["CURRICULUM_ASSIGNMENT"])
    enrollment_model.objects.filter(
        status="NEEDS_REVIEW", plan_id__isnull=False, review_reasons=[]
    ).update(review_reasons=["LEGACY_REVIEW"])


class Migration(migrations.Migration):
    dependencies = [("student_records", "0013_studentonboarding_and_more")]
    operations = [migrations.RunPython(backfill_review_reasons, migrations.RunPython.noop)]
