from __future__ import annotations

from django.db import models

from modules.common.models import UUIDTimestampedModel


class OptimizationRun(UUIDTimestampedModel):
    scenario = models.ForeignKey(
        "planning.PlanScenario", on_delete=models.PROTECT, related_name="optimization_runs"
    )
    input_hash = models.CharField(max_length=128)
    input_snapshot = models.JSONField(default=dict)
    solver_version = models.CharField(max_length=80)
    status = models.CharField(max_length=24)
    output_hash = models.CharField(max_length=128, blank=True)
    objective_values = models.JSONField(default=dict)
    solution = models.JSONField(default=dict)
    explanation = models.JSONField(default=dict)
    time_limit_seconds = models.PositiveIntegerField(default=60)
    started_at = models.DateTimeField(null=True, blank=True)
    cancel_requested_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["scenario", "status"], name="opt_scenario_status_idx"),
            models.Index(fields=["input_hash"], name="optimization_input_hash_idx"),
        ]
