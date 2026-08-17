from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from domain.enums import (
    EpistemicStatus,
    ExtractionCandidateStatus,
    NormRelationType,
    ProposalStatus,
    PublicationImpactStatus,
    ReviewDecision,
    SourceStatus,
    enum_choices,
)
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


class ExtractionCandidate(UUIDTimestampedModel):
    """One reviewable semantic statement extracted from an archived snapshot.

    Candidates are deliberately separate from requirements and revisions. A
    source importer may create a draft proposal and these candidates, but a
    candidate cannot silently become a VERIFIED rule or a published revision.
    """

    proposal = models.ForeignKey(
        ChangeProposal, on_delete=models.PROTECT, related_name="extraction_candidates"
    )
    source_snapshot = models.ForeignKey(
        SourceSnapshot, on_delete=models.PROTECT, related_name="extraction_candidates"
    )
    entity = models.CharField(max_length=80)
    entity_key = models.CharField(max_length=240)
    operation = models.CharField(max_length=16)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=enum_choices(ExtractionCandidateStatus),
        default=ExtractionCandidateStatus.PENDING.value,
    )
    epistemic_status = models.CharField(
        max_length=32,
        choices=enum_choices(EpistemicStatus),
        default=EpistemicStatus.INFERRED_PENDING_REVIEW.value,
    )
    evidence = models.ManyToManyField(Evidence, blank=True, related_name="extraction_candidates")
    reviewed_by = models.ForeignKey(
        "identity.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reviewed_extraction_candidates",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["entity", "entity_key", "operation"]
        constraints = [
            models.UniqueConstraint(
                fields=["proposal", "entity", "entity_key", "operation"],
                name="extraction_candidate_identity_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["proposal", "status"], name="candidate_proposal_status_idx"),
            models.Index(
                fields=["source_snapshot", "entity"], name="candidate_snapshot_entity_idx"
            ),
        ]

    def clean(self) -> None:
        if self.operation not in {"ADD", "REMOVE", "CHANGE"}:
            raise ValidationError({"operation": "Unsupported extraction operation."})
        if self.epistemic_status == EpistemicStatus.VERIFIED.value and not self.pk:
            raise ValidationError("A new extraction candidate cannot start as VERIFIED.")

    def __str__(self) -> str:
        return f"{self.entity}:{self.entity_key} ({self.operation})"


class Review(UUIDTimestampedModel):
    """Immutable decision record for a proposal review."""

    proposal = models.ForeignKey(ChangeProposal, on_delete=models.PROTECT, related_name="reviews")
    reviewer = models.ForeignKey(
        "identity.User", on_delete=models.PROTECT, related_name="curriculum_reviews"
    )
    decision = models.CharField(max_length=24, choices=enum_choices(ReviewDecision))
    comment = models.TextField(blank=True)
    proposal_version = models.CharField(max_length=80)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["proposal", "created_at"], name="review_proposal_time_idx"),
            models.Index(fields=["reviewer", "created_at"], name="review_reviewer_time_idx"),
        ]

    def save(self, *args: object, **kwargs: object) -> None:
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Review records are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("Review records cannot be deleted.")


class Publication(UUIDTimestampedModel):
    """Immutable publication receipt tied to one approved proposal/revision."""

    proposal = models.OneToOneField(
        ChangeProposal, on_delete=models.PROTECT, related_name="publication"
    )
    revision = models.OneToOneField(
        "curriculum.CurriculumRevision", on_delete=models.PROTECT, related_name="publication"
    )
    published_by = models.ForeignKey(
        "identity.User", on_delete=models.PROTECT, related_name="curriculum_publications"
    )
    published_at = models.DateTimeField()
    content_hash = models.CharField(max_length=128)
    source_set_hash = models.CharField(max_length=128)
    validation_report = models.JSONField(default=dict)
    semantic_diff = models.JSONField(default=dict)
    confirmation = models.TextField()

    class Meta:
        ordering = ["-published_at", "-id"]
        indexes = [
            models.Index(fields=["published_at"], name="publication_time_idx"),
            models.Index(
                fields=["published_by", "published_at"], name="publication_actor_time_idx"
            ),
        ]

    def save(self, *args: object, **kwargs: object) -> None:
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Publication records are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("Publication records cannot be deleted.")


class PublicationEvent(UUIDTimestampedModel):
    """Immutable application event emitted after a revision is published."""

    event_key = models.CharField(max_length=180, unique=True)
    event_type = models.CharField(max_length=120, default="curriculum.revision.published")
    schema_version = models.CharField(max_length=24, default="1.0")
    publication = models.OneToOneField(
        Publication, on_delete=models.PROTECT, related_name="publication_event"
    )
    revision = models.ForeignKey(
        "curriculum.CurriculumRevision",
        on_delete=models.PROTECT,
        related_name="publication_events",
    )
    superseded_revision = models.ForeignKey(
        "curriculum.CurriculumRevision",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="superseded_publication_events",
    )
    created_by = models.ForeignKey(
        "identity.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="curriculum_publication_events",
    )
    changed_courses = models.JSONField(default=list, blank=True)
    changed_groups = models.JSONField(default=list, blank=True)
    changed_requirements = models.JSONField(default=list, blank=True)
    impact_summary = models.JSONField(default=dict, blank=True)
    recompute_plan = models.JSONField(default=dict, blank=True)
    notification_plan = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["revision", "created_at"], name="pub_event_revision_time_idx"),
            models.Index(
                fields=["superseded_revision", "created_at"],
                name="pub_event_superseded_time_idx",
            ),
        ]

    def clean(self) -> None:
        if (
            self.superseded_revision_id
            and self.revision_id
            and self.superseded_revision
            and self.revision.plan_id != self.superseded_revision.plan_id
        ):
            raise ValidationError("Published and superseded revisions must share a plan.")

    def save(self, *args: object, **kwargs: object) -> None:
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Publication events are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("Publication events cannot be deleted.")


class PublicationImpact(UUIDTimestampedModel):
    """Durable impact/recompute work item for one affected enrollment."""

    publication_event = models.ForeignKey(
        PublicationEvent, on_delete=models.PROTECT, related_name="enrollment_impacts"
    )
    enrollment = models.ForeignKey(
        "student_records.ProgramEnrollment",
        on_delete=models.PROTECT,
        related_name="curriculum_publication_impacts",
    )
    previous_revision = models.ForeignKey(
        "curriculum.CurriculumRevision",
        on_delete=models.PROTECT,
        related_name="publication_impacts_as_previous",
    )
    previous_audit_run = models.ForeignKey(
        "audit.DegreeAuditRun",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="publication_impacts",
    )
    previous_audit_result_hash = models.CharField(max_length=128, blank=True)
    changed_courses = models.JSONField(default=list, blank=True)
    changed_groups = models.JSONField(default=list, blank=True)
    changed_requirements = models.JSONField(default=list, blank=True)
    impact_status = models.CharField(
        max_length=32,
        choices=enum_choices(PublicationImpactStatus),
        default=PublicationImpactStatus.RECOMPUTE_QUEUED.value,
    )
    recompute_job_key = models.CharField(max_length=240, unique=True)
    recompute_requested_at = models.DateTimeField()
    recomputed_audit_run = models.ForeignKey(
        "audit.DegreeAuditRun",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="recomputed_publication_impacts",
    )
    requires_revision_decision = models.BooleanField(default=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["publication_event", "enrollment"],
                name="publication_event_enrollment_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["publication_event", "impact_status"], name="pub_impact_event_status_idx"
            ),
            models.Index(
                fields=["enrollment", "impact_status"], name="pub_impact_enroll_status_idx"
            ),
        ]

    def clean(self) -> None:
        if (
            self.enrollment_id
            and self.previous_revision_id
            and self.enrollment.revision_basis_id != self.previous_revision_id
        ):
            raise ValidationError("The previous revision must match the enrollment revision basis.")

    def __str__(self) -> str:
        return f"{self.publication_event_id} — {self.enrollment_id}"
