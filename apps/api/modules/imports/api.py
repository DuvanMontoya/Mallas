from __future__ import annotations

from typing import Any, NoReturn
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from ninja import Header, Router, Schema
from ninja.security import django_auth

from modules.common.api import (
    raise_problem,
    require_if_match,
    validate_idempotency_key,
    with_problem_responses,
)
from modules.imports.application.history import (
    HistoryImportError,
    ImportPreview,
    confirm_history_import,
    create_history_import,
    get_import_batch_for_view,
    resolve_history_candidate,
)
from modules.imports.application.storage import MAX_ARTIFACT_BYTES
from modules.imports.models import CandidateRecord

router = Router(tags=["Student history imports"])


class CandidateView(Schema):
    id: UUID
    row_number: int
    source_locator: str
    status: str
    candidate_fingerprint: str
    raw_payload: dict[str, Any]
    normalized_payload: dict[str, Any]
    parse_errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    confidence: int
    requires_confirmation: bool
    conflict_details: list[dict[str, Any]]
    decision: str
    selected_course_version_id: UUID | None
    external_code: str
    note: str
    version: str


class ImportPreviewView(Schema):
    id: UUID
    enrollment_id: UUID | None
    status: str
    source_kind: str
    original_filename: str
    content_sha256: str
    content_fingerprint: str
    parser_version: str
    schema_version: str
    validation_errors: list[dict[str, Any]]
    metadata: dict[str, Any]
    created: bool
    candidate_count: int
    unresolved_count: int
    error_count: int
    candidates: list[CandidateView]
    version: str


class ResolvePayload(Schema):
    decision: str
    selected_course_version_id: UUID | None = None
    external_code: str = ""
    note: str = ""


class ApplyView(Schema):
    id: UUID
    status: str
    created_attempts: int
    created_recognitions: int
    skipped_candidates: int
    audit_run_id: UUID | None
    idempotent: bool


def _error(error: HistoryImportError) -> NoReturn:
    status = (
        403
        if error.code == "history_forbidden"
        else 404
        if error.code.endswith("_not_found")
        else 409
        if error.code
        in {
            "attempt_duplicate",
            "import_already_applied",
            "preview_unresolved",
            "preview_has_errors",
            "import_status_invalid",
            "conflict_note_required",
            "stale_resource",
            "idempotency_key_reused",
        }
        else 400
    )
    raise_problem(
        status=status,
        code=error.code.upper(),
        title="Request cannot be completed",
        detail=str(error),
    )


def _candidate_view(candidate: CandidateRecord) -> dict[str, Any]:
    reconciliation = candidate.reconciliation
    return {
        "id": candidate.pk,
        "row_number": candidate.row_number,
        "source_locator": candidate.source_locator,
        "status": candidate.status,
        "candidate_fingerprint": candidate.candidate_fingerprint,
        "raw_payload": candidate.raw_payload,
        "normalized_payload": candidate.normalized_payload,
        "parse_errors": candidate.parse_errors,
        "warnings": candidate.warnings,
        "confidence": candidate.confidence,
        "requires_confirmation": candidate.requires_confirmation,
        "conflict_details": candidate.conflict_details,
        "decision": reconciliation.decision,
        "selected_course_version_id": reconciliation.selected_course_version_id,
        "external_code": reconciliation.external_code,
        "note": reconciliation.note,
        "version": candidate.updated_at.isoformat(),
    }


def _preview_view(result: ImportPreview) -> dict[str, Any]:
    batch = result.batch
    candidates = list(
        batch.candidate_records.select_related("reconciliation").order_by("row_number", "id")
    )
    return {
        "id": batch.pk,
        "enrollment_id": batch.enrollment_id,
        "status": batch.status,
        "source_kind": batch.source_kind,
        "original_filename": batch.original_filename,
        "content_sha256": batch.content_sha256,
        "content_fingerprint": batch.content_fingerprint,
        "parser_version": batch.parser_version,
        "schema_version": batch.schema_version,
        "validation_errors": batch.validation_errors,
        "metadata": batch.metadata,
        "created": result.created,
        "candidate_count": result.candidate_count,
        "unresolved_count": result.unresolved_count,
        "error_count": result.error_count,
        "candidates": [_candidate_view(candidate) for candidate in candidates],
        "version": batch.updated_at.isoformat(),
    }


@router.post("/imports", auth=django_auth, response=with_problem_responses(ImportPreviewView))
def upload_history_import(
    request: HttpRequest,
    idempotency_key: str | None = Header(  # type: ignore[type-arg]
        None,
        alias="Idempotency-Key",
        description="Stable key for retrying the same upload without creating another batch.",
    ),
) -> dict[str, Any]:
    idempotency_key = validate_idempotency_key(idempotency_key)
    upload = request.FILES.get("file")
    enrollment_value = request.POST.get("enrollment_id", "")
    if upload is None or not enrollment_value:
        raise_problem(
            status=400,
            code="MULTIPART_FIELDS_REQUIRED",
            title="Missing upload fields",
            detail="multipart fields file and enrollment_id are required.",
        )
    try:
        enrollment_id = UUID(enrollment_value)
    except ValueError:
        raise_problem(
            status=400,
            code="ENROLLMENT_ID_INVALID",
            title="Invalid enrollment id",
            detail="enrollment_id must be a UUID.",
        )
    if upload.size is not None and upload.size > MAX_ARTIFACT_BYTES:
        raise_problem(
            status=400,
            code="ARTIFACT_TOO_LARGE",
            title="Uploaded file is too large",
            detail=f"The uploaded file cannot exceed {MAX_ARTIFACT_BYTES} bytes.",
        )
    content = upload.read(MAX_ARTIFACT_BYTES + 1)
    try:
        result = create_history_import(
            actor=request.auth,
            enrollment_id=enrollment_id,
            filename=upload.name,
            content=content,
            declared_mime=upload.content_type or "",
            idempotency_key=idempotency_key,
            request=request,
        )
    except HistoryImportError as error:
        _error(error)
    return _preview_view(result)


@router.get(
    "/imports/{batch_id}", auth=django_auth, response=with_problem_responses(ImportPreviewView)
)
def history_import_preview(request: HttpRequest, batch_id: UUID) -> dict[str, Any]:
    try:
        batch = get_import_batch_for_view(request.auth, batch_id)
    except HistoryImportError as error:
        _error(error)
    result = ImportPreview(
        batch=batch,
        created=False,
        candidate_count=batch.candidate_records.count(),
        unresolved_count=batch.candidate_records.filter(reconciliation__decision="PENDING").count(),
        error_count=batch.candidate_records.filter(status="ERROR").count(),
    )
    return _preview_view(result)


@router.post(
    "/imports/{batch_id}/candidates/{candidate_id}/resolve",
    auth=django_auth,
    response=with_problem_responses(CandidateView),
)
def resolve_candidate(
    request: HttpRequest,
    response: HttpResponse,
    batch_id: UUID,
    candidate_id: UUID,
    payload: ResolvePayload,
    if_match: str | None = Header(  # type: ignore[type-arg]
        None,
        alias="If-Match",
        description="The candidate version returned by the preview.",
    ),
) -> dict[str, Any]:
    try:
        candidate = resolve_history_candidate(
            actor=request.auth,
            batch_id=batch_id,
            candidate_id=candidate_id,
            decision=payload.decision,
            selected_course_version_id=payload.selected_course_version_id,
            external_code=payload.external_code,
            note=payload.note,
            expected_version=require_if_match(if_match),
            request=request,
        )
    except HistoryImportError as error:
        _error(error)
    view = _candidate_view(candidate)
    response["ETag"] = f'"{view["version"]}"'
    return view


@router.post(
    "/imports/{batch_id}/confirm", auth=django_auth, response=with_problem_responses(ApplyView)
)
def confirm_import(request: HttpRequest, batch_id: UUID) -> dict[str, Any]:
    try:
        result = confirm_history_import(actor=request.auth, batch_id=batch_id, request=request)
    except HistoryImportError as error:
        _error(error)
    return {
        "id": result.batch.pk,
        "status": result.batch.status,
        "created_attempts": result.created_attempts,
        "created_recognitions": result.created_recognitions,
        "skipped_candidates": result.skipped_candidates,
        "audit_run_id": result.audit_run_id,
        "idempotent": result.idempotent,
    }
