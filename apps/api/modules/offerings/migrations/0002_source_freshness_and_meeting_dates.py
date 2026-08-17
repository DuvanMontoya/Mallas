import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ("governance", "0001_initial"),
        ("offerings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="academicterm",
            name="source_snapshot",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="academic_terms",
                to="governance.sourcesnapshot",
            ),
        ),
        migrations.AddField(
            model_name="meeting",
            name="ends_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="meeting",
            name="is_alternate",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="meeting",
            name="session_code",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="meeting",
            name="starts_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="section",
            name="enrolled_count",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="academicterm",
            index=models.Index(
                fields=["source_snapshot", "starts_at"], name="term_source_start_idx"
            ),
        ),
        migrations.RemoveConstraint(
            model_name="section",
            name="section_enrollment_within_capacity",
        ),
        migrations.AddConstraint(
            model_name="section",
            constraint=models.CheckConstraint(
                condition=Q(capacity__isnull=True)
                | Q(enrolled_count__isnull=True)
                | Q(enrolled_count__lte=F("capacity")),
                name="section_enrollment_within_capacity",
            ),
        ),
        migrations.AddConstraint(
            model_name="meeting",
            constraint=models.CheckConstraint(
                condition=Q(ends_on__isnull=True)
                | Q(starts_on__isnull=True)
                | Q(ends_on__gte=F("starts_on")),
                name="meeting_date_range_valid",
            ),
        ),
    ]
