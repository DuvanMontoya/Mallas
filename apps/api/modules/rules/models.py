from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from domain.enums import EpistemicStatus, RequirementPurpose, enum_choices
from modules.common.models import UUIDTimestampedModel


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

    def __str__(self) -> str:
        return f"{self.owner_type}:{self.code}"
