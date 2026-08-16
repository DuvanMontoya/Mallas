from __future__ import annotations

from django.db import models
from django.db.models import Q

from modules.common.models import UUIDTimestampedModel


class DegreeAuditRun(UUIDTimestampedModel):
    enrollment = models.ForeignKey(
        "student_records.ProgramEnrollment", on_delete=models.PROTECT, related_name="audit_runs"
    )
    revision = models.ForeignKey(
        "curriculum.CurriculumRevision", on_delete=models.PROTECT, related_name="audit_runs"
    )
    history_fingerprint = models.CharField(max_length=128)
    exception_fingerprint = models.CharField(max_length=128)
    engine_version = models.CharField(max_length=80)
    result_hash = models.CharField(max_length=128)
    generated_at = models.DateTimeField()
    input_snapshot = models.JSONField(default=dict)

    class Meta:
        ordering = ["-generated_at"]
        indexes = [
            models.Index(
                fields=["enrollment", "-generated_at"], name="audit_run_enrollment_time_idx"
            ),
            models.Index(
                fields=["revision", "engine_version"], name="audit_run_revision_engine_idx"
            ),
            models.Index(fields=["result_hash"], name="audit_run_result_hash_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.enrollment} — {self.generated_at:%Y-%m-%d %H:%M}"


class DegreeAuditResult(UUIDTimestampedModel):
    run = models.OneToOneField(DegreeAuditRun, on_delete=models.PROTECT, related_name="result")
    status = models.CharField(max_length=32)
    total_approved_credits = models.PositiveIntegerField(default=0)
    total_applied_credits = models.PositiveIntegerField(default=0)
    total_excess_credits = models.PositiveIntegerField(default=0)
    payload = models.JSONField(default=dict)
    unknown_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["status", "unknown_count"], name="audit_result_status_idx")]


class CreditAllocation(UUIDTimestampedModel):
    result = models.ForeignKey(
        DegreeAuditResult, on_delete=models.PROTECT, related_name="credit_allocations"
    )
    course_attempt = models.ForeignKey(
        "student_records.CourseAttempt",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="credit_allocations",
    )
    course_version = models.ForeignKey(
        "curriculum.CourseVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="credit_allocations",
    )
    requirement_code = models.CharField(max_length=160)
    allocated_credits = models.PositiveIntegerField(default=0)
    allocation_order = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(allocated_credits__gte=0), name="credit_allocation_nonnegative"
            ),
        ]
        indexes = [
            models.Index(fields=["result", "requirement_code"], name="alloc_result_req_idx"),
            models.Index(fields=["course_attempt"], name="allocation_attempt_idx"),
        ]
