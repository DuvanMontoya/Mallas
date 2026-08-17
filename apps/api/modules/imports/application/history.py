from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from domain.enums import (
    AttemptOrigin,
    AttemptStatus,
    CandidateStatus,
    ImportStatus,
    RecognitionType,
    ReconciliationDecision,
)
from domain.history import HistoryFormatError, ParseCandidate, ParseReport, parse_history_bytes
from modules.audit.application.services import run_degree_audit
from modules.curriculum.models import CourseVersion
from modules.identity.application.audit import record_audit_event
from modules.identity.application.authorization import (
    can_edit_student_history,
    can_view_enrollment,
)
from modules.imports.application.parser_isolation import parse_pdf_history_isolated
from modules.imports.application.retention import purge_applied_batch_payloads
from modules.imports.application.storage import (
    ArtifactValidationError,
    ValidatedArtifact,
    artifact_metadata,
    store_artifact,
    validate_artifact,
)
from modules.imports.models import (
    CandidateRecord,
    ImportBatch,
    ImportEvidence,
    RawArtifact,
    Reconciliation,
)
from modules.offerings.models import AcademicTerm
from modules.student_records.models import AcademicRecognition, CourseAttempt, ProgramEnrollment

_IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class HistoryImportError(RuntimeError):
    """Safe, explainable error raised by the history import workflow."""

    def __init__(self, message: str, *, code: str = "history_import_invalid") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ImportPreview:
    batch: ImportBatch
    created: bool
    candidate_count: int
    unresolved_count: int
    error_count: int


@dataclass(frozen=True, slots=True)
class ImportApplyResult:
    batch: ImportBatch
    created_attempts: int
    created_recognitions: int
    skipped_candidates: int
    audit_run_id: str | None
    idempotent: bool = False


def _json_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _history_fingerprint(candidates: list[CandidateRecord]) -> str:
    payload = [
        {
            "row": candidate.row_number,
            "fingerprint": candidate.candidate_fingerprint,
            "decision": candidate.reconciliation.decision,
        }
        for candidate in candidates
    ]
    return _json_hash(payload)


def _serialized_error(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _get_enrollment_for_edit(actor: Any, enrollment_id: UUID | str) -> ProgramEnrollment:
    try:
        enrollment = ProgramEnrollment.objects.select_related(
            "student", "student__institution"
        ).get(pk=enrollment_id)
    except ProgramEnrollment.DoesNotExist as exc:
        raise HistoryImportError("Enrollment was not found.", code="enrollment_not_found") from exc
    if not can_edit_student_history(actor, enrollment.student):
        raise HistoryImportError(
            "You cannot edit this student's history.", code="history_forbidden"
        )
    return enrollment


def get_import_batch_for_view(actor: Any, batch_id: UUID | str) -> ImportBatch:
    try:
        batch = ImportBatch.objects.select_related("student", "enrollment", "artifact").get(
            pk=batch_id
        )
    except ImportBatch.DoesNotExist as exc:
        raise HistoryImportError("Import batch was not found.", code="import_not_found") from exc
    if batch.enrollment_id and not can_view_enrollment(actor, batch.enrollment):
        raise HistoryImportError("You cannot view this import batch.", code="history_forbidden")
    if batch.enrollment_id is None and not (
        getattr(actor, "is_superuser", False) or batch.student.user_id == getattr(actor, "pk", None)
    ):
        raise HistoryImportError("You cannot view this import batch.", code="history_forbidden")
    return batch


def _find_term_and_course(
    enrollment: ProgramEnrollment, normalized: dict[str, Any]
) -> tuple[AcademicTerm | None, CourseVersion | None, list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    term_code = str(normalized.get("term_code", ""))
    term = AcademicTerm.objects.filter(
        institution_id=enrollment.student.institution_id, code=term_code
    ).first()
    if term is None:
        errors.append(
            _serialized_error("term_not_found", f"No term {term_code} belongs to the institution.")
        )
        return None, None, errors

    course_code = str(normalized.get("course_code", ""))
    from django.db.models import Q

    course_versions = list(
        CourseVersion.objects.filter(
            course__institution_id=enrollment.student.institution_id,
            course__code__iexact=course_code,
            valid_from__lte=term.starts_at.date(),
        )
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gt=term.starts_at.date()))
        .select_related("course")
        .order_by("-valid_from", "-created_at")
    )
    if not course_versions:
        if normalized.get("external_code"):
            return (
                term,
                None,
                [
                    _serialized_error(
                        "external_resolution_required",
                        "No internal course matched; select a target course for the external equivalence.",
                    )
                ],
            )
        errors.append(
            _serialized_error(
                "course_not_found", f"No course {course_code} belongs to the institution."
            )
        )
        return term, None, errors
    if len(course_versions) > 1:
        errors.append(
            _serialized_error(
                "course_version_ambiguous", "More than one temporal course version matched."
            )
        )
    return term, course_versions[0], errors


def _existing_conflicts(
    enrollment: ProgramEnrollment,
    course_version: CourseVersion,
    term: AcademicTerm,
    normalized: dict[str, Any],
) -> list[dict[str, Any]]:
    requested_attempt = int(normalized.get("attempt_number", 1))
    conflicts: list[dict[str, Any]] = []
    for attempt in CourseAttempt.objects.filter(
        enrollment=enrollment, course_version=course_version
    ).order_by("attempt_number", "id"):
        if attempt.term_id != term.pk and attempt.attempt_number != requested_attempt:
            continue
        conflicts.append(
            {
                "attempt_id": str(attempt.pk),
                "attempt_number": attempt.attempt_number,
                "term_code": attempt.term.code,
                "status": attempt.status,
                "grade": str(attempt.grade) if attempt.grade is not None else None,
                "credits_earned": attempt.credits_earned,
                "kind": "same_attempt_number"
                if attempt.attempt_number == requested_attempt
                else "same_course_term",
            }
        )
    return conflicts


def _candidate_status(
    candidate: ParseCandidate,
    *,
    term: AcademicTerm | None,
    course_version: CourseVersion | None,
    resolution_errors: list[dict[str, str]],
    conflicts: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    details: list[dict[str, Any]] = [*candidate.errors, *resolution_errors]
    if candidate.errors:
        return CandidateStatus.ERROR.value, details
    if term is None:
        return CandidateStatus.ERROR.value, details
    blocking_errors = [
        error
        for error in resolution_errors
        if error.get("code") not in {"external_resolution_required", "course_version_ambiguous"}
    ]
    if blocking_errors:
        return CandidateStatus.ERROR.value, details
    if resolution_errors:
        return CandidateStatus.CONFLICT.value, details
    if course_version is None and not candidate.normalized_payload.get("external_code"):
        return CandidateStatus.ERROR.value, details
    if conflicts:
        details.extend(conflicts)
        return CandidateStatus.CONFLICT.value, details
    if course_version is None:
        return CandidateStatus.CONFLICT.value, details
    return CandidateStatus.VALID.value, details


def _persist_candidate(
    *,
    batch: ImportBatch,
    parsed: ParseCandidate,
    actor: Any,
) -> CandidateRecord:
    normalized = dict(parsed.normalized_payload)
    term, course_version, resolution_errors = _find_term_and_course(batch.enrollment, normalized)
    conflicts = (
        _existing_conflicts(batch.enrollment, course_version, term, normalized)
        if term is not None and course_version is not None
        else []
    )
    status, details = _candidate_status(
        parsed,
        term=term,
        course_version=course_version,
        resolution_errors=resolution_errors,
        conflicts=conflicts,
    )
    candidate = CandidateRecord.objects.create(
        batch=batch,
        row_number=parsed.row_number,
        source_locator=parsed.source_locator,
        candidate_fingerprint=parsed.fingerprint,
        raw_payload=parsed.raw_payload,
        normalized_payload=normalized,
        parse_errors=list(parsed.errors),
        warnings=list(parsed.warnings),
        confidence=parsed.confidence,
        requires_confirmation=parsed.requires_confirmation or bool(conflicts),
        status=status,
        suggested_course_version=course_version,
        suggested_term=term,
        conflict_details=details,
    )
    decision = ReconciliationDecision.PENDING.value
    selected_course = None
    metadata: dict[str, Any] = {}
    if status == CandidateStatus.VALID.value and not candidate.requires_confirmation:
        decision = ReconciliationDecision.ACCEPT.value
        selected_course = course_version
        candidate.status = CandidateStatus.RESOLVED.value
        candidate.save(update_fields=["status", "updated_at"])
        metadata = {"automatic": True, "actor_id": str(getattr(actor, "pk", ""))}
    Reconciliation.objects.create(
        candidate=candidate,
        decision=decision,
        selected_course_version=selected_course,
        decided_by=None if metadata.get("automatic") else actor,
        decided_at=None if metadata.get("automatic") else timezone.now(),
        metadata=metadata,
    )
    return candidate


def create_history_import(
    *,
    actor: Any,
    enrollment_id: UUID | str,
    filename: str,
    content: bytes,
    declared_mime: str = "",
    idempotency_key: str | None = None,
    request: Any | None = None,
) -> ImportPreview:
    enrollment = _get_enrollment_for_edit(actor, enrollment_id)
    if idempotency_key is not None and not _IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key):
        raise HistoryImportError(
            "Idempotency-Key must contain 1–128 safe ASCII characters.",
            code="idempotency_key_invalid",
        )
    try:
        validated = validate_artifact(
            filename=filename, content=content, declared_mime=declared_mime
        )
    except ArtifactValidationError as exc:
        raise HistoryImportError(str(exc), code="artifact_invalid") from exc
    try:
        report = (
            parse_pdf_history_isolated(content, source_name=validated.original_filename)
            if validated.mime_type == "application/pdf"
            else parse_history_bytes(
                content,
                source_name=validated.original_filename,
                mime_type=validated.mime_type,
            )
        )
    except (ValueError, HistoryFormatError) as exc:
        raise HistoryImportError(str(exc), code="history_format_invalid") from exc
    return _persist_history_import(
        actor=actor,
        enrollment=enrollment,
        content=content,
        validated=validated,
        report=report,
        idempotency_key=idempotency_key,
        request=request,
    )


@transaction.atomic  # type: ignore[untyped-decorator]
def _persist_history_import(
    *,
    actor: Any,
    enrollment: ProgramEnrollment,
    content: bytes,
    validated: ValidatedArtifact,
    report: ParseReport,
    idempotency_key: str | None,
    request: Any | None,
) -> ImportPreview:
    # Serialize preview creation for one enrollment so the hash/key uniqueness
    # contract remains deterministic under concurrent uploads.
    ProgramEnrollment.objects.select_for_update().get(pk=enrollment.pk)
    existing_by_key = (
        ImportBatch.objects.filter(enrollment=enrollment, idempotency_key=idempotency_key).first()
        if idempotency_key
        else None
    )
    if existing_by_key is not None and existing_by_key.content_sha256 != validated.content_sha256:
        raise HistoryImportError(
            "This Idempotency-Key was already used for different content.",
            code="idempotency_key_reused",
        )
    existing = (
        existing_by_key
        or ImportBatch.objects.filter(
            enrollment=enrollment,
            content_sha256=validated.content_sha256,
        ).first()
    )
    if existing is not None:
        return ImportPreview(
            batch=existing,
            created=False,
            candidate_count=existing.candidate_records.count(),
            unresolved_count=existing.candidate_records.filter(
                reconciliation__decision=ReconciliationDecision.PENDING.value
            ).count(),
            error_count=existing.candidate_records.filter(
                status=CandidateStatus.ERROR.value
            ).count(),
        )
    batch = ImportBatch.objects.create(
        student=enrollment.student,
        enrollment=enrollment,
        created_by=actor,
        source_kind=report.source_kind,
        original_filename=validated.original_filename,
        content_sha256=validated.content_sha256,
        idempotency_key=idempotency_key or "",
        parser_version=report.parser_version,
        status=ImportStatus.PREVIEW.value,
        validation_errors=list(report.errors),
        metadata={
            **report.metadata,
            "source_kind": report.source_kind,
            "parser_version": report.parser_version,
            "format": "student-history/1.0.0",
        },
        schema_version=report.schema_version,
        content_fingerprint=_json_hash(
            {
                "schema_version": report.schema_version,
                "parser_version": report.parser_version,
                "candidates": [candidate.fingerprint for candidate in report.candidates],
            }
        ),
    )
    try:
        storage_key = store_artifact(
            batch_id=batch.pk,
            content_sha256=validated.content_sha256,
            content=content,
        )
        RawArtifact.objects.create(
            batch=batch,
            uploaded_by=actor,
            original_filename=validated.original_filename,
            content_sha256=validated.content_sha256,
            size_bytes=validated.size_bytes,
            mime_type=validated.mime_type,
            storage_key=storage_key,
            metadata=artifact_metadata(
                filename=validated.original_filename,
                mime_type=validated.mime_type,
                size_bytes=validated.size_bytes,
            ),
        )
        batch.storage_key = storage_key
        batch.save(update_fields=["storage_key", "updated_at"])
    except (OSError, ArtifactValidationError) as exc:
        raise HistoryImportError(
            "The private artifact could not be stored.", code="artifact_storage_error"
        ) from exc

    candidates = [
        _persist_candidate(batch=batch, parsed=parsed, actor=actor) for parsed in report.candidates
    ]
    batch.history_fingerprint = _history_fingerprint(candidates)
    batch.save(update_fields=["history_fingerprint", "updated_at"])
    record_audit_event(
        request,
        action="HISTORY_IMPORT_PREVIEW_CREATED",
        actor=actor,
        object_type="ImportBatch",
        object_id=batch.pk,
        institution_id=enrollment.student.institution_id,
        metadata={
            "candidate_count": len(candidates),
            "error_count": sum(
                1 for candidate in candidates if candidate.status == CandidateStatus.ERROR.value
            ),
            "source_kind": report.source_kind,
        },
    )
    return ImportPreview(
        batch=batch,
        created=True,
        candidate_count=len(candidates),
        unresolved_count=sum(
            1
            for candidate in candidates
            if candidate.reconciliation.decision == ReconciliationDecision.PENDING.value
        ),
        error_count=sum(
            1 for candidate in candidates if candidate.status == CandidateStatus.ERROR.value
        ),
    )


@transaction.atomic  # type: ignore[untyped-decorator]
def resolve_history_candidate(
    *,
    actor: Any,
    batch_id: UUID | str,
    candidate_id: UUID | str,
    decision: str,
    selected_course_version_id: UUID | str | None = None,
    external_code: str = "",
    note: str = "",
    expected_version: str | None = None,
    request: Any | None = None,
) -> CandidateRecord:
    batch = _get_editable_batch(actor, batch_id)
    # Reconciliation and confirmation always acquire the batch lock first,
    # then candidate locks. This prevents a stale resolver from writing after
    # the batch has been applied by a concurrent confirmation.
    batch = ImportBatch.objects.select_for_update().get(pk=batch.pk)
    if batch.status == ImportStatus.APPLIED.value:
        raise HistoryImportError(
            "Applied imports cannot be changed.", code="import_already_applied"
        )
    try:
        locked = CandidateRecord.objects.select_for_update().get(pk=candidate_id, batch=batch)
        candidate = CandidateRecord.objects.select_related(
            "batch__enrollment__student", "reconciliation", "suggested_course_version"
        ).get(pk=locked.pk)
    except CandidateRecord.DoesNotExist as exc:
        raise HistoryImportError("Candidate was not found.", code="candidate_not_found") from exc
    if (
        expected_version is not None
        and expected_version.strip('"') != candidate.updated_at.isoformat()
    ):
        raise HistoryImportError(
            "The candidate changed since it was read; reload the preview before resolving.",
            code="stale_resource",
        )
    if candidate.parse_errors or candidate.status == CandidateStatus.ERROR.value:
        raise HistoryImportError(
            "Invalid candidates must be corrected by uploading valid data.",
            code="candidate_invalid",
        )
    if decision not in {
        member.value
        for member in ReconciliationDecision
        if member != ReconciliationDecision.PENDING
    }:
        raise HistoryImportError("Unsupported reconciliation decision.", code="decision_invalid")
    if (
        candidate.status == CandidateStatus.CONFLICT.value
        and decision == ReconciliationDecision.ACCEPT.value
        and not note.strip()
    ):
        raise HistoryImportError(
            "An explicit note is required to accept a conflict.", code="conflict_note_required"
        )
    selected_course = None
    if selected_course_version_id is not None:
        selected_course = (
            CourseVersion.objects.filter(
                pk=selected_course_version_id,
                course__institution_id=batch.student.institution_id,
            )
            .select_related("course")
            .first()
        )
        if selected_course is None:
            raise HistoryImportError(
                "Selected course is not in the student's institution.", code="course_forbidden"
            )
    if decision == ReconciliationDecision.ACCEPT.value and selected_course is None:
        selected_course = candidate.suggested_course_version
        if selected_course is None:
            raise HistoryImportError(
                "Accept requires an internal course mapping.", code="course_mapping_required"
            )
    if decision == ReconciliationDecision.EXTERNAL.value and (
        not external_code.strip() or selected_course is None
    ):
        raise HistoryImportError(
            "External decisions require an external code and target course.",
            code="external_mapping_required",
        )
    reconciliation = candidate.reconciliation
    reconciliation.decision = decision
    reconciliation.selected_course_version = selected_course
    reconciliation.external_code = external_code.strip()[:120]
    reconciliation.note = note.strip()[:2_000]
    reconciliation.decided_by = actor
    reconciliation.decided_at = timezone.now()
    reconciliation.metadata = {"manual": True}
    reconciliation.full_clean()
    reconciliation.save()
    candidate.status = (
        CandidateStatus.SKIPPED.value
        if decision == ReconciliationDecision.SKIP.value
        else CandidateStatus.RESOLVED.value
    )
    candidate.save(update_fields=["status", "updated_at"])
    # A reconciliation decision changes the reviewed batch snapshot.
    batch.save(update_fields=["updated_at"])
    record_audit_event(
        request,
        action="HISTORY_IMPORT_CANDIDATE_RESOLVED",
        actor=actor,
        object_type="CandidateRecord",
        object_id=candidate.pk,
        institution_id=batch.student.institution_id,
        metadata={"decision": decision, "batch_id": str(batch.pk)},
    )
    return candidate


def _get_editable_batch(actor: Any, batch_id: UUID | str) -> ImportBatch:
    try:
        batch = ImportBatch.objects.select_related("student", "enrollment").get(pk=batch_id)
    except ImportBatch.DoesNotExist as exc:
        raise HistoryImportError("Import batch was not found.", code="import_not_found") from exc
    if batch.enrollment_id is None or not can_edit_student_history(actor, batch.student):
        raise HistoryImportError("You cannot edit this import batch.", code="history_forbidden")
    return batch


def _grade(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        grade = Decimal(str(value))
    except InvalidOperation as exc:
        raise HistoryImportError("Grade is not a decimal number.", code="grade_invalid") from exc
    if not grade.is_finite() or grade < 0 or grade > 5:
        raise HistoryImportError("Grade must be between 0 and 5.", code="grade_invalid")
    return grade


def _credits(normalized: dict[str, Any], *, status: str, course_version: CourseVersion) -> int:
    raw = normalized.get("credits_earned")
    if raw not in (None, ""):
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise HistoryImportError(
                "credits_earned must be an integer.", code="credits_invalid"
            ) from exc
        if value < 0:
            raise HistoryImportError("credits_earned cannot be negative.", code="credits_invalid")
        return value
    if status in {
        AttemptStatus.PASSED.value,
        AttemptStatus.VALIDATED.value,
        AttemptStatus.HOMOLOGATED.value,
        AttemptStatus.TRANSFERRED.value,
    }:
        return course_version.credits or 0
    return 0


def _next_attempt_number(
    enrollment: ProgramEnrollment, course_version: CourseVersion, requested: int
) -> int:
    used = set(
        CourseAttempt.objects.filter(
            enrollment=enrollment, course_version=course_version
        ).values_list("attempt_number", flat=True)
    )
    if requested not in used:
        return requested
    return max(used, default=requested) + 1


def _evidence_excerpt(candidate: CandidateRecord) -> tuple[str, str, dict[str, Any]]:
    metadata = candidate.normalized_payload.get("source_metadata", {})
    excerpt = ""
    if isinstance(metadata, dict):
        excerpt = str(metadata.get("text_excerpt", ""))
    if not excerpt:
        excerpt = json.dumps(candidate.raw_payload, ensure_ascii=False, sort_keys=True)
    excerpt = excerpt[:2_000]
    return (
        excerpt,
        hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
        {
            "confidence": candidate.confidence,
            "requires_confirmation": candidate.requires_confirmation,
            "warnings": candidate.warnings,
        },
    )


@transaction.atomic  # type: ignore[untyped-decorator]
def confirm_history_import(
    *,
    actor: Any,
    batch_id: UUID | str,
    expected_version: str | None = None,
    request: Any | None = None,
) -> ImportApplyResult:
    batch = _get_editable_batch(actor, batch_id)
    # Lock only the batch row. PostgreSQL cannot apply FOR UPDATE to nullable
    # sides introduced by select_related joins (student/enrollment are legacy-
    # nullable on ImportBatch), while the base-row lock is sufficient to make
    # confirmation and idempotent replay serialize.
    batch = ImportBatch.objects.select_for_update().get(pk=batch.pk)
    if batch.status == ImportStatus.APPLIED.value:
        # Confirmation is an idempotent command. A client that lost the first
        # response must be able to replay the same request even though applying
        # the batch advanced updated_at. No mutation is performed in this path.
        latest = batch.enrollment.audit_runs.order_by("-generated_at").first()
        return ImportApplyResult(
            batch=batch,
            created_attempts=0,
            created_recognitions=0,
            skipped_candidates=0,
            audit_run_id=str(latest.pk) if latest else None,
            idempotent=True,
        )
    if expected_version is not None and expected_version.strip('"') != batch.updated_at.isoformat():
        raise HistoryImportError(
            "The import changed since it was reviewed; reload the preview before confirming.",
            code="stale_resource",
        )
    if batch.status != ImportStatus.PREVIEW.value:
        raise HistoryImportError(
            "Only a preview batch can be confirmed.", code="import_status_invalid"
        )
    # Lock candidate base rows in a stable order before reading their nullable
    # related mappings. This serializes confirmation with reconciliation
    # without applying FOR UPDATE to nullable joins.
    list(
        CandidateRecord.objects.select_for_update()
        .filter(batch=batch)
        .order_by("row_number", "id")
        .values_list("id", flat=True)
    )
    candidates = list(
        batch.candidate_records.select_related(
            "reconciliation",
            "suggested_term",
            "suggested_course_version",
            "suggested_course_version__course",
        ).order_by("row_number", "id")
    )
    if batch.validation_errors or any(
        candidate.status == CandidateStatus.ERROR.value for candidate in candidates
    ):
        raise HistoryImportError(
            "The preview contains row errors that must be corrected before confirmation.",
            code="preview_has_errors",
        )
    pending = [
        candidate.row_number
        for candidate in candidates
        if candidate.reconciliation.decision == ReconciliationDecision.PENDING.value
    ]
    if pending:
        raise HistoryImportError(
            f"Candidates still require a reconciliation decision: rows {pending}.",
            code="preview_unresolved",
        )
    artifact = batch.artifact
    created_attempts = 0
    created_recognitions = 0
    skipped_candidates = 0
    for candidate in candidates:
        reconciliation = candidate.reconciliation
        if reconciliation.decision == ReconciliationDecision.SKIP.value:
            skipped_candidates += 1
            continue
        term = candidate.suggested_term
        if term is None:
            raise HistoryImportError(
                f"Row {candidate.row_number} has no resolved academic term.",
                code="term_mapping_required",
            )
        course_version = reconciliation.selected_course_version
        if course_version is None:
            raise HistoryImportError(
                f"Row {candidate.row_number} has no resolved course.",
                code="course_mapping_required",
            )
        normalized = candidate.normalized_payload
        if reconciliation.decision == ReconciliationDecision.EXTERNAL.value:
            credits = _credits(
                normalized, status=AttemptStatus.TRANSFERRED.value, course_version=course_version
            )
            recognition = AcademicRecognition.objects.create(
                enrollment=batch.enrollment,
                target_course_version=course_version,
                recognition_type=RecognitionType.TRANSFER.value,
                credits_applied=credits,
                resolution_reference=reconciliation.external_code,
                notes=reconciliation.note or f"Imported from {batch.original_filename}.",
            )
            created_recognitions += 1
            excerpt, excerpt_hash, evidence_metadata = _evidence_excerpt(candidate)
            ImportEvidence.objects.create(
                batch=batch,
                artifact=artifact,
                candidate=candidate,
                source_locator=candidate.source_locator,
                excerpt=excerpt,
                excerpt_hash=excerpt_hash,
                metadata={**evidence_metadata, "recognition_id": str(recognition.pk)},
            )
            continue
        status = str(normalized.get("status", ""))
        requested_attempt = int(normalized.get("attempt_number", 1))
        attempt_number = _next_attempt_number(batch.enrollment, course_version, requested_attempt)
        attempt = CourseAttempt(
            enrollment=batch.enrollment,
            course_version=course_version,
            term=term,
            attempt_number=attempt_number,
            status=status,
            grade=_grade(normalized.get("grade")),
            credits_earned=_credits(normalized, status=status, course_version=course_version),
            origin=AttemptOrigin.IMPORT.value,
            import_batch=batch,
            entered_by=actor,
            notes=(
                reconciliation.note
                or f"Imported from {batch.original_filename}; source {candidate.source_locator}."
            ),
        )
        attempt.full_clean()
        attempt.save()
        created_attempts += 1
        excerpt, excerpt_hash, evidence_metadata = _evidence_excerpt(candidate)
        ImportEvidence.objects.create(
            batch=batch,
            artifact=artifact,
            candidate=candidate,
            course_attempt=attempt,
            source_locator=candidate.source_locator,
            excerpt=excerpt,
            excerpt_hash=excerpt_hash,
            metadata=evidence_metadata,
        )

    audit_result, audit_run, _ = run_degree_audit(batch.enrollment_id)
    batch.status = ImportStatus.APPLIED.value
    batch.confirmed_by = actor
    batch.confirmed_at = timezone.now()
    batch.applied_at = batch.confirmed_at
    batch.history_fingerprint = _history_fingerprint(candidates)
    batch.save(
        update_fields=[
            "status",
            "confirmed_by",
            "confirmed_at",
            "applied_at",
            "history_fingerprint",
            "updated_at",
        ]
    )
    purge_applied_batch_payloads(batch_id=batch.pk, as_of=batch.applied_at)
    record_audit_event(
        request,
        action="HISTORY_IMPORT_APPLIED",
        actor=actor,
        object_type="ImportBatch",
        object_id=batch.pk,
        institution_id=batch.student.institution_id,
        metadata={
            "created_attempts": created_attempts,
            "created_recognitions": created_recognitions,
            "skipped_candidates": skipped_candidates,
            "audit_run_id": str(audit_run.pk),
            "audit_result_hash": audit_result.result_hash,
        },
    )
    return ImportApplyResult(
        batch=batch,
        created_attempts=created_attempts,
        created_recognitions=created_recognitions,
        skipped_candidates=skipped_candidates,
        audit_run_id=str(audit_run.pk),
    )
