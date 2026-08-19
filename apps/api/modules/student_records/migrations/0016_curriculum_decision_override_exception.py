from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("student_records", "0015_enrollment_review_status_constraint")]

    operations = [
        migrations.AddField(
            model_name="curriculumassignmentdecision",
            name="override_exception",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="curriculum_assignment_decisions",
                to="student_records.academicexception",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="curriculumassignmentdecision",
            name="assignment_resolved_has_policy_target",
        ),
        migrations.RemoveConstraint(
            model_name="curriculumassignmentdecision",
            name="assignment_override_has_actor_reason_target",
        ),
        migrations.AddConstraint(
            model_name="curriculumassignmentdecision",
            constraint=models.CheckConstraint(
                condition=(
                    ~models.Q(status="RESOLVED")
                    | (
                        models.Q(selected_plan__isnull=False)
                        & models.Q(selected_revision__isnull=False)
                        & (
                            models.Q(policy__isnull=False)
                            | (
                                models.Q(method="ADMIN_OVERRIDE")
                                & models.Q(override_evidence__isnull=False)
                                & models.Q(override_exception__isnull=False)
                            )
                        )
                    )
                ),
                name="assignment_resolved_has_policy_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="curriculumassignmentdecision",
            constraint=models.CheckConstraint(
                condition=(
                    ~models.Q(method="ADMIN_OVERRIDE")
                    | (
                        models.Q(decided_by__isnull=False)
                        & ~models.Q(override_reason_code="")
                        & models.Q(override_evidence__isnull=False)
                        & models.Q(override_exception__isnull=False)
                        & models.Q(selected_plan__isnull=False)
                        & models.Q(selected_revision__isnull=False)
                    )
                ),
                name="assignment_override_has_actor_reason_target",
            ),
        ),
    ]
