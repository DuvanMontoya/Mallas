from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from domain.enums import NormRelationType, ProposalStatus, SourceStatus, enum_choices
from modules.common.models import UUIDTimestampedModel


class NormativeDocument(UUIDTimestampedModel):
    issuer = models.CharField(max_length=240)
    document_type = models.CharField(max_length=100)
    number = models.CharField(max_length=80)
    year = models.PositiveIntegerField()
    title = models.CharField(max_length=320)
    publication_date = models.DateField(null=True, blank=True)
    canonical_url = models.URLField(blank=True)
    status = models.CharField(
        max_length=24,
        choices=enum_choices(SourceStatus),
        default=SourceStatus.ACTIVE.value,
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-year", "document_type", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["issuer", "document_type", "number", "year"],
                name="normative_document_identity_unique",
            ),
            models.CheckConstraint(
                condition=Q(year__gte=1900), name="normative_document_year_valid"
            ),
        ]
        indexes = [
            models.Index(fields=["document_type", "year"], name="normative_type_year_idx"),
            models.Index(fields=["status", "publication_date"], name="normative_status_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.document_type} {self.number}/{self.year}"


class SourceSnapshot(UUIDTimestampedModel):
    document = models.ForeignKey(
        NormativeDocument, on_delete=models.PROTECT, related_name="snapshots"
    )
    captured_at = models.DateTimeField()
    sha256 = models.CharField(max_length=64)
    mime_type = models.CharField(max_length=120)
    storage_key = models.CharField(max_length=500)
    source_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-captured_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "sha256"], name="snapshot_document_hash_unique"
            ),
            models.CheckConstraint(
                condition=Q(sha256__regex=r"^[0-9a-fA-F]{64}$"), name="snapshot_sha256_hex"
            ),
        ]
        indexes = [
            models.Index(fields=["document", "-captured_at"], name="snapshot_document_time_idx"),
            models.Index(fields=["sha256"], name="snapshot_sha256_idx"),
        ]

    def clean(self) -> None:
        if len(self.sha256) != 64:
            raise ValidationError(
                {"sha256": "sha256 must contain exactly 64 hexadecimal characters."}
            )

    def __str__(self) -> str:
        return f"{self.document} — {self.sha256[:12]}"


class Evidence(UUIDTimestampedModel):
    snapshot = models.ForeignKey(SourceSnapshot, on_delete=models.PROTECT, related_name="evidence")
    page = models.PositiveIntegerField(null=True, blank=True)
    section = models.CharField(max_length=240, blank=True)
    line_locator = models.CharField(max_length=240, blank=True)
    excerpt_hash = models.CharField(max_length=128)
    excerpt = models.TextField(blank=True)
    annotation = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["snapshot", "page"], name="evidence_snapshot_page_idx"),
            models.Index(fields=["excerpt_hash"], name="evidence_excerpt_hash_idx"),
        ]

    def __str__(self) -> str:
        locator = (
            self.line_locator or self.section or (f"p. {self.page}" if self.page else "source")
        )
        return f"{self.snapshot} — {locator}"


class NormRelation(UUIDTimestampedModel):
    source_document = models.ForeignKey(
        NormativeDocument, on_delete=models.PROTECT, related_name="outgoing_relations"
    )
    target_document = models.ForeignKey(
        NormativeDocument, on_delete=models.PROTECT, related_name="incoming_relations"
    )
    relation = models.CharField(max_length=24, choices=enum_choices(NormRelationType))
    effective_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_document", "target_document", "relation"],
                name="norm_relation_identity_unique",
            ),
            models.CheckConstraint(
                condition=~Q(source_document=F("target_document")), name="norm_relation_not_self"
            ),
        ]
        indexes = [
            models.Index(fields=["source_document", "relation"], name="norm_relation_source_idx"),
            models.Index(fields=["target_document", "relation"], name="norm_relation_target_idx"),
        ]

    def clean(self) -> None:
        if self.source_document_id == self.target_document_id:
            raise ValidationError("A normative document cannot relate to itself.")

    def __str__(self) -> str:
        return f"{self.source_document} {self.relation} {self.target_document}"


class ChangeProposal(UUIDTimestampedModel):
    """Auditable semantic change proposal for a draft curriculum revision.

    A proposal is deliberately separate from publication. Importing a source can
    create a draft and proposal, but it cannot change a published revision or
    move a proposal through the editorial workflow by itself.
    """

    proposal_key = models.CharField(max_length=160, unique=True)
    title = models.CharField(max_length=320)
    status = models.CharField(
        max_length=24,
        choices=enum_choices(ProposalStatus),
        default=ProposalStatus.DRAFT.value,
    )
    base_revision = models.ForeignKey(
        "curriculum.CurriculumRevision",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="change_proposals_as_base",
    )
    candidate_revision = models.ForeignKey(
        "curriculum.CurriculumRevision",
        on_delete=models.PROTECT,
        related_name="change_proposals_as_candidate",
    )
    source_snapshot = models.ForeignKey(
        SourceSnapshot,
        on_delete=models.PROTECT,
        related_name="change_proposals",
    )
    content_fingerprint = models.CharField(max_length=64)
    semantic_diff = models.JSONField(default=dict)
    rationale = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "identity.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="curriculum_change_proposals",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["candidate_revision", "status"], name="proposal_candidate_status_idx"
            ),
            models.Index(fields=["content_fingerprint"], name="proposal_fingerprint_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["candidate_revision", "content_fingerprint"],
                name="proposal_candidate_fingerprint_unique",
            )
        ]

    def clean(self) -> None:
        if self.base_revision_id and self.base_revision_id == self.candidate_revision_id:
            raise ValidationError("A proposal cannot compare a revision with itself.")
        if self.base_revision_id and self.base_revision.plan_id != self.candidate_revision.plan_id:
            raise ValidationError("Proposal revisions must belong to the same curriculum plan.")

    def __str__(self) -> str:
        return self.title
