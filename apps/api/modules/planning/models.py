from __future__ import annotations

import uuid
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from domain.enums import ScenarioCourseSource, ScenarioStatus, enum_choices
from modules.common.models import UUIDTimestampedModel


class PlanScenario(UUIDTimestampedModel):
    enrollment = models.ForeignKey(
        "student_records.ProgramEnrollment", on_delete=models.PROTECT, related_name="plan_scenarios"
    )
    created_by = models.ForeignKey(
        "identity.User", on_delete=models.PROTECT, related_name="created_plan_scenarios"
    )
    name = models.CharField(max_length=160)
    status = models.CharField(
        max_length=20,
        choices=enum_choices(ScenarioStatus),
        default=ScenarioStatus.ACTIVE.value,
    )
    version = models.PositiveIntegerField(default=1)
    sharing_enabled = models.BooleanField(default=False)
    share_token = models.UUIDField(default=None, unique=True, editable=False, null=True, blank=True)
    target_term = models.ForeignKey(
        "offerings.AcademicTerm",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="target_scenarios",
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "name"], name="scenario_enrollment_name_unique"
            ),
            models.CheckConstraint(condition=Q(version__gte=1), name="scenario_version_positive"),
        ]
        indexes = [
            models.Index(fields=["enrollment", "status"], name="scenario_enrollment_status_idx"),
            models.Index(fields=["target_term"], name="scenario_target_term_idx"),
        ]

    def clean(self) -> None:
        if (
            self.target_term_id
            and self.target_term.institution_id != self.enrollment.student.institution_id
        ):
            raise ValidationError(
                {"target_term": "Scenario target term must match the student institution."}
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.sharing_enabled and self.share_token is None:
            self.share_token = uuid.uuid4()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.enrollment} — {self.name}"


class PlannedCourse(UUIDTimestampedModel):
    scenario = models.ForeignKey(
        PlanScenario, on_delete=models.PROTECT, related_name="planned_courses"
    )
    course_version = models.ForeignKey(
        "curriculum.CourseVersion", on_delete=models.PROTECT, related_name="planned_courses"
    )
    term = models.ForeignKey(
        "offerings.AcademicTerm", on_delete=models.PROTECT, related_name="planned_courses"
    )
    section = models.ForeignKey(
        "offerings.Section",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="planned_courses",
    )
    priority = models.PositiveIntegerField(default=0)
    is_locked = models.BooleanField(default=False)
    source = models.CharField(
        max_length=16,
        choices=enum_choices(ScenarioCourseSource),
        default=ScenarioCourseSource.USER.value,
    )
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scenario", "course_version", "term"],
                name="planned_course_scenario_term_unique",
            ),
            models.CheckConstraint(
                condition=Q(priority__gte=0), name="planned_course_priority_nonnegative"
            ),
        ]
        indexes = [
            models.Index(fields=["scenario", "term", "priority"], name="planned_scenario_term_idx"),
            models.Index(fields=["course_version", "term"], name="planned_course_course_term_idx"),
        ]

    def clean(self) -> None:
        if (
            self.term_id
            and self.scenario_id
            and self.term.institution_id != self.scenario.enrollment.student.institution_id
        ):
            raise ValidationError("Planned course term and scenario institution must match.")
        if (
            self.course_version_id
            and self.scenario_id
            and self.course_version.course.institution_id
            != self.scenario.enrollment.student.institution_id
        ):
            raise ValidationError("Planned course and scenario institution must match.")
        if self.section_id:
            if self.section.offering.term_id != self.term_id:
                raise ValidationError({"section": "Section must belong to the planned term."})
            if self.section.offering.course_version_id != self.course_version_id:
                raise ValidationError(
                    {"section": "Section must belong to the planned course version."}
                )

    def __str__(self) -> str:
        return f"{self.scenario.name} — {self.course_version.course.code} — {self.term.code}"


class PlanningPreference(UUIDTimestampedModel):
    scenario = models.OneToOneField(
        PlanScenario, on_delete=models.PROTECT, related_name="planning_preferences"
    )
    max_credits_per_term = models.PositiveSmallIntegerField(default=18)
    min_credits_per_term = models.PositiveSmallIntegerField(default=0)
    unavailable_weekdays = models.JSONField(default=list, blank=True)
    preferred_modalities = models.JSONField(default=list, blank=True)
    preferred_area_codes = models.JSONField(default=list, blank=True)
    objective_weights = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(max_credits_per_term__gte=F("min_credits_per_term")),
                name="planning_credit_limits_valid",
            )
        ]

    def clean(self) -> None:
        if self.min_credits_per_term > self.max_credits_per_term:
            raise ValidationError("Minimum credits cannot exceed maximum credits.")
        if not isinstance(self.unavailable_weekdays, list) or any(
            isinstance(day, bool) or not isinstance(day, int) or day not in range(7)
            for day in self.unavailable_weekdays
        ):
            raise ValidationError(
                {"unavailable_weekdays": "Weekdays must be integers from 0 to 6."}
            )


class ScenarioAuditProjection(UUIDTimestampedModel):
    """Projected audit for a scenario; it never becomes an official audit run."""

    scenario = models.OneToOneField(
        PlanScenario, on_delete=models.PROTECT, related_name="audit_projection"
    )
    input_fingerprint = models.CharField(max_length=128)
    revision_hash = models.CharField(max_length=128, blank=True)
    engine_version = models.CharField(max_length=80)
    result_hash = models.CharField(max_length=128)
    generated_at = models.DateTimeField()
    payload = models.JSONField(default=dict)
    unknown_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["result_hash"], name="scenario_projection_hash_idx"),
            models.Index(fields=["generated_at"], name="scenario_projection_time_idx"),
        ]
