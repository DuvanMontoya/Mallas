from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from domain.enums import (
    CandidateStatus,
    ImportArtifactStatus,
    ImportStatus,
    ReconciliationDecision,
    enum_choices,
)
from modules.common.models import UUIDTimestampedModel


def history_raw_payload_expiry() -> datetime:
    return timezone.now() + timedelta(days=settings.HISTORY_RAW_PAYLOAD_RETENTION_DAYS)


class ImportBatch(UUIDTimestampedModel):
    student = models.ForeignKey(
        "student_records.StudentProfile",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="import_batches",
    )
    enrollment = models.ForeignKey(
        "student_records.ProgramEnrollment",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="import_batches",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="created_import_batches",
    )
    source_kind = models.CharField(max_length=80)
    original_filename = models.CharField(max_length=255, blank=True)
    content_sha256 = models.CharField(max_length=64, blank=True)
    idempotency_key = models.CharField(max_length=128, blank=True)
    storage_key = models.CharField(max_length=500, blank=True)
    parser_version = models.CharField(max_length=80, blank=True)
    status = models.CharField(
        max_length=20,
        choices=enum_choices(ImportStatus),
        default=ImportStatus.RECEIVED.value,
    )
    validation_errors = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    schema_version = models.CharField(max_length=32, blank=True)
    content_fingerprint = models.CharField(max_length=64, blank=True)
    source_snapshot = models.ForeignKey(
        "governance.SourceSnapshot",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="import_batches",
    )
    curriculum_revision = models.ForeignKey(
        "curriculum.CurriculumRevision",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="import_batches",
    )
    report_markdown = models.TextField(blank=True)
    semantic_diff = models.JSONField(default=dict, blank=True)
    history_fingerprint = models.CharField(max_length=64, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="confirmed_import_batches",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "content_sha256"],
                condition=models.Q(enrollment__isnull=False) & ~models.Q(content_sha256=""),
                name="import_enrollment_hash_unique",
            ),
            models.UniqueConstraint(
                fields=["enrollment", "idempotency_key"],
                condition=models.Q(enrollment__isnull=False) & ~models.Q(idempotency_key=""),
                name="import_enrollment_idempotency_unique",
            ),
            models.UniqueConstraint(
                fields=["source_kind", "content_fingerprint", "parser_version"],
                condition=models.Q(source_kind="CURRICULUM_BASELINE", content_fingerprint__gt=""),
                name="curriculum_import_fingerprint_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "status"], name="import_student_status_idx"),
            models.Index(fields=["enrollment", "status"], name="import_enroll_status_idx"),
            models.Index(fields=["content_sha256"], name="import_content_hash_idx"),
            models.Index(
                fields=["enrollment", "idempotency_key"], name="import_enrollment_key_idx"
            ),
            models.Index(fields=["created_by", "created_at"], name="import_creator_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.source_kind} — {self.created_at:%Y-%m-%d %H:%M}"


class RawArtifact(UUIDTimestampedModel):
    """Private, validated source bytes retained for import provenance."""

    batch = models.OneToOneField(ImportBatch, on_delete=models.PROTECT, related_name="artifact")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="uploaded_import_artifacts",
    )
    original_filename = models.CharField(max_length=255)
    content_sha256 = models.CharField(max_length=64)
    size_bytes = models.PositiveBigIntegerField()
    mime_type = models.CharField(max_length=120)
    storage_key = models.CharField(max_length=500, blank=True)
    content_expires_at = models.DateTimeField(default=history_raw_payload_expiry)
    content_purged_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=enum_choices(ImportArtifactStatus),
        default=ImportArtifactStatus.STORED.value,
    )
    validation_errors = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(size_bytes__gt=0), name="artifact_size_positive"
            ),
        ]
        indexes = [
            models.Index(fields=["content_sha256"], name="artifact_content_hash_idx"),
            models.Index(fields=["status", "created_at"], name="artifact_status_time_idx"),
            models.Index(
                fields=["content_purged_at", "content_expires_at"],
                name="artifact_retention_idx",
            ),
        ]

    def clean(self) -> None:
        if len(self.content_sha256) != 64:
            raise ValidationError({"content_sha256": "content_sha256 must be 64 hex characters."})
        if self.size_bytes <= 0:
            raise ValidationError({"size_bytes": "An artifact must not be empty."})

    def __str__(self) -> str:
        return f"{self.original_filename} — {self.content_sha256[:12]}"


class CandidateRecord(UUIDTimestampedModel):
    """A parser output that is not authoritative until reconciled and confirmed."""

    batch = models.ForeignKey(
        ImportBatch, on_delete=models.PROTECT, related_name="candidate_records"
    )
    row_number = models.PositiveIntegerField()
    source_locator = models.CharField(max_length=240)
    candidate_fingerprint = models.CharField(max_length=64)
    raw_payload = models.JSONField(default=dict)
    raw_payload_expires_at = models.DateTimeField(default=history_raw_payload_expiry)
    raw_payload_purged_at = models.DateTimeField(null=True, blank=True)
    normalized_payload = models.JSONField(default=dict)
    parse_errors = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    confidence = models.PositiveSmallIntegerField(default=0)
    requires_confirmation = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=enum_choices(CandidateStatus),
        default=CandidateStatus.PENDING.value,
    )
    suggested_course_version = models.ForeignKey(
        "curriculum.CourseVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="suggested_import_candidates",
    )
    suggested_term = models.ForeignKey(
        "offerings.AcademicTerm",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="suggested_import_candidates",
    )
    conflict_details = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "row_number"], name="candidate_batch_row_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(confidence__lte=100), name="candidate_confidence_valid"
            ),
        ]
        indexes = [
            models.Index(fields=["batch", "status"], name="candidate_batch_status_idx"),
            models.Index(fields=["batch", "candidate_fingerprint"], name="candidate_batch_fp_idx"),
            models.Index(
                fields=["raw_payload_purged_at", "raw_payload_expires_at"],
                name="candidate_raw_retention_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.batch_id} — row {self.row_number}"


class Reconciliation(UUIDTimestampedModel):
    """Explicit human/system decision for one candidate record."""

    candidate = models.OneToOneField(
        CandidateRecord, on_delete=models.PROTECT, related_name="reconciliation"
    )
    decision = models.CharField(
        max_length=20,
        choices=enum_choices(ReconciliationDecision),
        default=ReconciliationDecision.PENDING.value,
    )
    selected_course_version = models.ForeignKey(
        "curriculum.CourseVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="selected_import_reconciliations",
    )
    external_code = models.CharField(max_length=120, blank=True)
    note = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="import_reconciliations",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["decision", "decided_at"], name="recon_decision_time_idx"),
        ]

    def clean(self) -> None:
        if self.decision == ReconciliationDecision.EXTERNAL.value and not self.external_code:
            raise ValidationError({"external_code": "External decisions require external_code."})
        if (
            self.decision == ReconciliationDecision.ACCEPT.value
            and not self.selected_course_version_id
        ):
            raise ValidationError({"selected_course_version": "Accept decisions require a course."})

    def __str__(self) -> str:
        return f"{self.candidate_id} — {self.decision}"


class ImportEvidence(UUIDTimestampedModel):
    """Lineage from a confirmed attempt back to its private source artifact."""

    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT, related_name="evidence")
    artifact = models.ForeignKey(RawArtifact, on_delete=models.PROTECT, related_name="evidence")
    candidate = models.ForeignKey(
        CandidateRecord, on_delete=models.PROTECT, related_name="evidence"
    )
    course_attempt = models.ForeignKey(
        "student_records.CourseAttempt",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="import_evidence",
    )
    source_locator = models.CharField(max_length=240)
    excerpt = models.TextField(blank=True)
    excerpt_hash = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "source_locator"],
                name="import_evidence_candidate_locator_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["course_attempt"], name="import_evidence_attempt_idx"),
            models.Index(fields=["artifact", "source_locator"], name="import_evidence_source_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.batch_id} — {self.source_locator}"
