from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("student_records", "0014_backfill_enrollment_review_reasons")]

    operations = [
        migrations.AddConstraint(
            model_name="programenrollment",
            constraint=models.CheckConstraint(
                condition=(models.Q(status="NEEDS_REVIEW") & ~models.Q(review_reasons=[]))
                | (~models.Q(status="NEEDS_REVIEW") & models.Q(review_reasons=[])),
                name="enrollment_review_status_matches_reasons",
            ),
        )
    ]
