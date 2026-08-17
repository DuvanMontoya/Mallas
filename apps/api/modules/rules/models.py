from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from domain.enums import EpistemicStatus, RequirementPurpose, enum_choices
from modules.common.models import UUIDTimestampedModel
from modules.curriculum.models import IMMUTABLE_REVISION_STATUSES, CurriculumRevision


class Requirement(UUIDTimestampedModel):
    revision = models.ForeignKey(
        "curriculum.CurriculumRevision",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="requirements",
    )
    owner_type = models.CharField(max_length=80)
    owner_id = models.UUIDField()
    code = models.CharField(max_length=120)
    purpose = models.CharField(max_length=40, choices=enum_choices(RequirementPurpose))
    ast = models.JSONField(default=dict)
    ast_schema_version = models.CharField(max_length=32, default="1.0.0")
    ast_hash = models.CharField(max_length=64, blank=True)
    epistemic_status = models.CharField(
        max_length=32,
        choices=enum_choices(EpistemicStatus),
        default=EpistemicStatus.UNKNOWN.value,
    )
    evidence = models.ManyToManyField(
        "governance.Evidence", blank=True, related_name="requirements"
    )
    explanation_key = models.CharField(max_length=240, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "owner_type", "owner_id", "code"],
                name="requirement_revision_owner_code_unique",
            )
        ]
        indexes = [
            models.Index(fields=["owner_type", "owner_id"], name="requirement_owner_idx"),
            models.Index(
                fields=["purpose", "epistemic_status"], name="requirement_purpose_status_idx"
            ),
            models.Index(fields=["ast_hash"], name="requirement_ast_hash_idx"),
        ]

    def clean(self) -> None:
        if not isinstance(self.ast, dict):
            raise ValidationError({"ast": "Requirement AST must be a JSON object."})

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        revision_ids = {self.revision_id}
        if self.pk:
            previous_revision_id = type(self).objects.filter(pk=self.pk).values_list(
                "revision_id", flat=True
            ).first()
            revision_ids.add(previous_revision_id)
        immutable_ids = {revision_id for revision_id in revision_ids if revision_id}
        statuses = set(
            CurriculumRevision.objects.filter(pk__in=immutable_ids).values_list("status", flat=True)
        )
        if statuses.intersection(IMMUTABLE_REVISION_STATUSES):
            raise ValidationError(
                "Requirements belonging to a published, superseded, or retired revision are immutable."
            )
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        if self.revision_id and CurriculumRevision.objects.filter(
            pk=self.revision_id, status__in=IMMUTABLE_REVISION_STATUSES
        ).exists():
            raise ValidationError(
                "Requirements belonging to a published, superseded, or retired revision are immutable."
            )
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.owner_type}:{self.code}"
