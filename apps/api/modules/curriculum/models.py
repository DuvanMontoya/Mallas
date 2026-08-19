from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from domain.enums import (
    CountPolicy,
    CurriculumAssignmentContext,
    CurriculumAssignmentPolicyStatus,
    EpistemicStatus,
    MembershipRole,
    RequirementGroupKind,
    RevisionStatus,
    enum_choices,
)
from domain.errors import (
    PublishedAssignmentPolicyImmutableError,
    PublishedRevisionImmutableError,
)
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


IMMUTABLE_ASSIGNMENT_POLICY_STATUSES = frozenset(
    {
        CurriculumAssignmentPolicyStatus.PUBLISHED.value,
        CurriculumAssignmentPolicyStatus.SUPERSEDED.value,
        CurriculumAssignmentPolicyStatus.RETIRED.value,
    }
)


class CurriculumAssignmentPolicy(UUIDTimestampedModel):
    policy_code = models.CharField(max_length=120)
    version = models.PositiveIntegerField(default=1)
    program = models.ForeignKey(
        "institutions.Program",
        on_delete=models.PROTECT,
        related_name="curriculum_assignment_policies",
    )
    plan = models.ForeignKey(
        CurriculumPlan, on_delete=models.PROTECT, related_name="assignment_policies"
    )
    revision_basis = models.ForeignKey(
        CurriculumRevision,
        on_delete=models.PROTECT,
        related_name="assignment_policies",
    )
    context = models.CharField(max_length=24, choices=enum_choices(CurriculumAssignmentContext))
    admission_from = models.DateField(null=True, blank=True)
    admission_to = models.DateField(null=True, blank=True)
    cohort_code = models.CharField(max_length=80, blank=True)
    previous_plan = models.ForeignKey(
        CurriculumPlan,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="transition_assignment_policies",
    )
    normative_published_on = models.DateField(null=True, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    allow_retired_revision = models.BooleanField(default=False)
    status = models.CharField(
        max_length=24,
        choices=enum_choices(CurriculumAssignmentPolicyStatus),
        default=CurriculumAssignmentPolicyStatus.DRAFT.value,
    )
    epistemic_status = models.CharField(
        max_length=32,
        choices=enum_choices(EpistemicStatus),
        default=EpistemicStatus.UNKNOWN.value,
    )
    source_set_hash = models.CharField(max_length=64, blank=True)
    content_hash = models.CharField(max_length=64, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    supersedes = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="successors",
    )
    evidence = models.ManyToManyField(
        "governance.Evidence",
        through="CurriculumAssignmentPolicyEvidence",
        related_name="curriculum_assignment_policies",
    )
    metadata = models.JSONField(default=dict, blank=True)
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="prepared_curriculum_assignment_policies",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approved_curriculum_assignment_policies",
    )

    class Meta:
        ordering = ["program__name", "policy_code", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["policy_code", "version"], name="assignment_policy_code_version_unique"
            ),
            models.CheckConstraint(
                condition=Q(admission_to__isnull=True)
                | Q(admission_from__isnull=True)
                | Q(admission_to__gt=F("admission_from")),
                name="assignment_policy_admission_range_valid",
            ),
            models.CheckConstraint(
                condition=Q(effective_to__isnull=True)
                | Q(effective_from__isnull=True)
                | Q(effective_to__gt=F("effective_from")),
                name="assignment_policy_effective_range_valid",
            ),
            models.CheckConstraint(
                condition=Q(version__gte=1), name="assignment_policy_version_positive"
            ),
        ]
        indexes = [
            models.Index(
                fields=["program", "context", "status"], name="assign_policy_scope_status_idx"
            ),
            models.Index(
                fields=["admission_from", "admission_to"], name="assign_policy_admission_idx"
            ),
        ]

    def clean(self) -> None:
        errors: dict[str, str] = {}
        if self.plan_id and self.plan.program_id != self.program_id:
            errors["plan"] = "Assignment policy plan must belong to the selected program."
        if self.revision_basis_id and self.revision_basis.plan_id != self.plan_id:
            errors["revision_basis"] = "Assignment policy revision must belong to its target plan."
        if self.previous_plan_id and self.previous_plan.program_id != self.program_id:
            errors["previous_plan"] = "Previous plan must belong to the selected program."
        if self.supersedes_id and self.supersedes_id == self.pk:
            errors["supersedes"] = "An assignment policy cannot supersede itself."
        if self.supersedes_id and self.supersedes.policy_code != self.policy_code:
            errors["supersedes"] = "A policy can only supersede the same policy code."
        if self.supersedes_id and (
            self.supersedes.program_id != self.program_id
            or self.supersedes.context != self.context
        ):
            errors["supersedes"] = "A policy successor must preserve program and context."
        if self.supersedes_id and self.version <= self.supersedes.version:
            errors["version"] = "A policy successor must have a greater version."
        seen = {self.pk} if self.pk else set()
        ancestor = self.supersedes if self.supersedes_id else None
        while ancestor is not None:
            if ancestor.pk in seen:
                errors["supersedes"] = "Assignment policy succession cannot contain a cycle."
                break
            seen.add(ancestor.pk)
            ancestor = ancestor.supersedes if ancestor.supersedes_id else None
        if errors:
            raise ValidationError(errors)

    def _immutable_content_changed(self, previous: CurriculumAssignmentPolicy) -> bool:
        fields = (
            "policy_code",
            "version",
            "program_id",
            "plan_id",
            "revision_basis_id",
            "context",
            "admission_from",
            "admission_to",
            "cohort_code",
            "previous_plan_id",
            "normative_published_on",
            "effective_from",
            "effective_to",
            "allow_retired_revision",
            "epistemic_status",
            "source_set_hash",
            "content_hash",
            "published_at",
            "supersedes_id",
            "metadata",
            "prepared_by_id",
            "approved_by_id",
        )
        return any(getattr(previous, field) != getattr(self, field) for field in fields)

    def save(self, *args: object, **kwargs: object) -> None:
        publication_authorized = bool(
            getattr(self, "_publication_service_authorized", False)
        )
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).first()
            if (
                previous
                and previous.status not in IMMUTABLE_ASSIGNMENT_POLICY_STATUSES
                and self.status == CurriculumAssignmentPolicyStatus.PUBLISHED.value
                and not publication_authorized
            ):
                raise PublishedAssignmentPolicyImmutableError(
                    "Assignment policies can only be published through the governance service."
                )
            if previous and previous.status in IMMUTABLE_ASSIGNMENT_POLICY_STATUSES:
                if self._immutable_content_changed(previous):
                    raise PublishedAssignmentPolicyImmutableError(
                        "Published assignment policy content cannot be edited."
                    )
                allowed = {
                    CurriculumAssignmentPolicyStatus.PUBLISHED.value: {
                        CurriculumAssignmentPolicyStatus.PUBLISHED.value,
                        CurriculumAssignmentPolicyStatus.SUPERSEDED.value,
                        CurriculumAssignmentPolicyStatus.RETIRED.value,
                    },
                    CurriculumAssignmentPolicyStatus.SUPERSEDED.value: {
                        CurriculumAssignmentPolicyStatus.SUPERSEDED.value,
                    },
                    CurriculumAssignmentPolicyStatus.RETIRED.value: {
                        CurriculumAssignmentPolicyStatus.RETIRED.value,
                    },
                }
                if self.status not in allowed[previous.status]:
                    raise PublishedAssignmentPolicyImmutableError(
                        "Assignment policy lifecycle cannot move backwards."
                    )
        elif (
            self.status == CurriculumAssignmentPolicyStatus.PUBLISHED.value
            and not publication_authorized
        ):
            raise PublishedAssignmentPolicyImmutableError(
                "Assignment policies cannot be created directly as published."
            )
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        if self.status in IMMUTABLE_ASSIGNMENT_POLICY_STATUSES:
            raise PublishedAssignmentPolicyImmutableError(
                "Published assignment policies cannot be deleted."
            )
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.policy_code} v{self.version} — {self.program.code}"


class CurriculumAssignmentPolicyEvidence(UUIDTimestampedModel):
    policy = models.ForeignKey(
        CurriculumAssignmentPolicy,
        on_delete=models.PROTECT,
        related_name="evidence_links",
    )
    evidence = models.ForeignKey(
        "governance.Evidence",
        on_delete=models.PROTECT,
        related_name="assignment_policy_links",
    )
    purpose = models.CharField(max_length=120, blank=True)
    sealed_snapshot_sha256 = models.CharField(max_length=64, blank=True)
    sealed_snapshot_id = models.UUIDField(null=True, blank=True)
    sealed_storage_key_hash = models.CharField(max_length=64, blank=True)
    sealed_excerpt_hash = models.CharField(max_length=128, blank=True)
    sealed_locator_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["policy", "evidence"]
        constraints = [
            models.UniqueConstraint(
                fields=["policy", "evidence"], name="assignment_policy_evidence_unique"
            )
        ]

    def _assert_editable(self) -> None:
        if self.policy.status in IMMUTABLE_ASSIGNMENT_POLICY_STATUSES:
            raise PublishedAssignmentPolicyImmutableError(
                "Evidence of a published assignment policy cannot be changed."
            )
        if self.pk:
            previous_policy_id = (
                type(self).objects.filter(pk=self.pk).values_list("policy_id", flat=True).first()
            )
            if previous_policy_id:
                previous_status = CurriculumAssignmentPolicy.objects.filter(
                    pk=previous_policy_id
                ).values_list("status", flat=True).first()
                if previous_status in IMMUTABLE_ASSIGNMENT_POLICY_STATUSES:
                    raise PublishedAssignmentPolicyImmutableError(
                        "Evidence cannot be moved away from a published assignment policy."
                    )

    def save(self, *args: object, **kwargs: object) -> None:
        self._assert_editable()
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        self._assert_editable()
        return super().delete(*args, **kwargs)


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
