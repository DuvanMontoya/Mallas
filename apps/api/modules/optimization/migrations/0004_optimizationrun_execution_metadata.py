from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("optimization", "0003_rename_optimization_scenario_status_idx_opt_scenario_status_idx"),
        ("planning", "0004_plannedcourse_is_locked_plannedcourse_section_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="optimizationrun",
            name="cancel_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="optimizationrun",
            name="input_snapshot",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="optimizationrun",
            name="output_hash",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="optimizationrun",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
