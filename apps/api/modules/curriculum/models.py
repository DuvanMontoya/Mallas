from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from domain.enums import (
    CountPolicy,
    MembershipRole,
    RequirementGroupKind,
    RevisionStatus,
    enum_choices,
)
from domain.errors import PublishedRevisionImmutableError
from modules.common.models import UUIDTimestampedModel

IMMUTABLE_REVISION_STATUSES = frozenset(
    {
        RevisionStatus.PUBLISHED.value,
        RevisionStatus.SUPERSEDED.value,
        RevisionStatus.RETIRED.value,
    }
)


def _assert_revision_editable(revision_id: object) -> None:
    if not revision_id:
        return
    status = (
        CurriculumRevision.objects.filter(pk=revision_id).values_list("status", flat=True).first()
    )
    if status in IMMUTABLE_REVISION_STATUSES:
        raise PublishedRevisionImmutableError(
            "Curriculum revision contents cannot be edited after publication or retirement."
        )


def _revision_ids_for_write(instance: models.Model, revision_id: object) -> set[object]:
    revision_ids = {revision_id}
    if instance.pk:
        previous_revision_id = (
            type(instance)
            .objects.filter(pk=instance.pk)
            .values_list("revision_id", flat=True)
            .first()
        )
        revision_ids.add(previous_revision_id)
    return {value for value in revision_ids if value}


class CurriculumPlan(UUIDTimestampedModel):
    program = models.ForeignKey(
        "institutions.Program", on_delete=models.PROTECT, related_name="curriculum_plans"
    )
    code = models.CharField(max_length=60)
    title = models.CharField(max_length=240)

    class Meta:
        ordering = ["program__name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["program", "code"], name="plan_program_code_unique")
        ]
        indexes = [models.Index(fields=["program", "code"], name="plan_program_code_idx")]

    def __str__(self) -> str:
        return f"{self.program.name} — {self.code}"


class CurriculumRevision(UUIDTimestampedModel):
    plan = models.ForeignKey(CurriculumPlan, on_delete=models.PROTECT, related_name="revisions")
    revision_code = models.CharField(max_length=80)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=24,
        choices=enum_choices(RevisionStatus),
        default=RevisionStatus.DRAFT.value,
    )
    total_required_credits = models.PositiveIntegerField(default=0)
    source_set_hash = models.CharField(max_length=128, blank=True)
    content_hash = models.CharField(max_length=128, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    supersedes = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="successors",
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-effective_from", "revision_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "revision_code"], name="revision_plan_code_unique"
            ),
            models.UniqueConstraint(
                fields=["plan"],
                condition=Q(status=RevisionStatus.PUBLISHED.value),
                name="revision_one_published_per_plan",
            ),
            models.CheckConstraint(
                condition=Q(effective_to__isnull=True) | Q(effective_to__gt=F("effective_from")),
                name="revision_effective_range_valid",
            ),
            models.CheckConstraint(
                condition=Q(total_required_credits__gte=0),
                name="revision_credits_nonnegative",
            ),
        ]
        indexes = [
            models.Index(fields=["plan", "status"], name="revision_plan_status_idx"),
            models.Index(fields=["effective_from", "effective_to"], name="revision_effective_idx"),
        ]

    def clean(self) -> None:
        if self.supersedes_id and self.supersedes_id == self.id:
            raise ValidationError({"supersedes": "A revision cannot supersede itself."})
        if self.supersedes_id and self.supersedes and self.supersedes.plan_id != self.plan_id:
            raise ValidationError({"supersedes": "A revision can only supersede the same plan."})

    def _published_content_changed(self, previous: CurriculumRevision) -> bool:
        immutable_fields = (
            "plan_id",
            "revision_code",
            "effective_from",
            "effective_to",
            "total_required_credits",
            "source_set_hash",
            "content_hash",
            "supersedes_id",
            "metadata",
        )
        return any(getattr(previous, field) != getattr(self, field) for field in immutable_fields)

    def save(self, *args: object, **kwargs: object) -> None:
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).first()
            if previous and previous.status == RevisionStatus.PUBLISHED.value:
                if self._published_content_changed(previous):
                    raise PublishedRevisionImmutableError(
                        "Published curriculum revision content cannot be edited."
                    )
                if self.status not in {
                    RevisionStatus.PUBLISHED.value,
                    RevisionStatus.SUPERSEDED.value,
                    RevisionStatus.RETIRED.value,
                }:
                    raise PublishedRevisionImmutableError(
                        "A published revision can only transition to superseded or retired."
                    )
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        if self.status == RevisionStatus.PUBLISHED.value:
            raise PublishedRevisionImmutableError(
                "Published curriculum revisions cannot be deleted."
            )
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.plan.code} — {self.revision_code}"


class Course(UUIDTimestampedModel):
    institution = models.ForeignKey(
        "institutions.Institution", on_delete=models.PROTECT, related_name="courses"
    )
    code = models.CharField(max_length=40)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["institution__display_name", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"], name="course_institution_code_unique"
            )
        ]
        indexes = [models.Index(fields=["institution", "active"], name="course_inst_active_idx")]

    def __str__(self) -> str:
        return self.code


class CourseVersion(UUIDTimestampedModel):
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="versions")
    name = models.CharField(max_length=240)
    credits = models.PositiveSmallIntegerField(null=True, blank=True)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["course__code", "-valid_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "valid_from"], name="course_version_start_unique"
            ),
            models.CheckConstraint(
                condition=Q(valid_to__isnull=True) | Q(valid_to__gt=F("valid_from")),
                name="course_version_effective_range_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["course", "valid_from", "valid_to"], name="course_version_temporal_idx"
            )
        ]

    def clean(self) -> None:
        if self.credits is not None and self.credits < 0:
            raise ValidationError({"credits": "Credits cannot be negative."})

    def __str__(self) -> str:
        return f"{self.course.code} — {self.name}"


class RequirementGroup(UUIDTimestampedModel):
    revision = models.ForeignKey(
        CurriculumRevision, on_delete=models.PROTECT, related_name="requirement_groups"
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    code = models.CharField(max_length=100)
    label = models.CharField(max_length=240)
    kind = models.CharField(max_length=20, choices=enum_choices(RequirementGroupKind))
    required_credits = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["revision", "sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "code"], name="requirement_group_revision_code_unique"
            ),
            models.CheckConstraint(
                condition=Q(required_credits__gte=0), name="requirement_group_credits_nonnegative"
            ),
        ]
        indexes = [
            models.Index(fields=["revision", "kind"], name="req_group_revision_kind_idx"),
            models.Index(fields=["parent", "sort_order"], name="req_group_parent_order_idx"),
        ]

    def clean(self) -> None:
        if self.parent_id and self.parent_id == self.id:
            raise ValidationError({"parent": "A requirement group cannot parent itself."})
        if self.parent_id and self.parent and self.parent.revision_id != self.revision_id:
            raise ValidationError({"parent": "A group parent must belong to the same revision."})

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        for revision_id in _revision_ids_for_write(self, self.revision_id):
            _assert_revision_editable(revision_id)
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        _assert_revision_editable(self.revision_id)
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.revision.revision_code} — {self.code}"


class PlanMembership(UUIDTimestampedModel):
    revision = models.ForeignKey(
        CurriculumRevision, on_delete=models.PROTECT, related_name="memberships"
    )
    course_version = models.ForeignKey(
        CourseVersion, on_delete=models.PROTECT, related_name="plan_memberships"
    )
    group = models.ForeignKey(
        RequirementGroup, on_delete=models.PROTECT, related_name="memberships"
    )
    role = models.CharField(max_length=32, choices=enum_choices(MembershipRole))
    count_policy = models.CharField(
        max_length=16,
        choices=enum_choices(CountPolicy),
        default=CountPolicy.CREDITS.value,
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "course_version", "group"],
                name="membership_revision_course_group_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["revision", "role"], name="membership_revision_role_idx"),
            models.Index(fields=["group", "course_version"], name="membership_group_course_idx"),
        ]

    def clean(self) -> None:
        if self.group_id and self.group.revision_id != self.revision_id:
            raise ValidationError({"group": "The group must belong to the membership revision."})
        if self.course_version_id and self.revision_id:
            plan_institution_id = self.revision.plan.program.faculty.campus.institution_id
            course_institution_id = self.course_version.course.institution_id
            if course_institution_id != plan_institution_id:
                raise ValidationError(
                    "Plan membership course and program must belong to the same institution."
                )

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        for revision_id in _revision_ids_for_write(self, self.revision_id):
            _assert_revision_editable(revision_id)
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        _assert_revision_editable(self.revision_id)
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.revision.revision_code} — {self.course_version.course.code}"
