from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any, Protocol

from domain.enums import AttemptStatus

HISTORY_SCHEMA_VERSION = "student-history/1.0.0"
HISTORY_PARSER_VERSION = "student-history-parser/1.0.0"
MAX_RECORDS = 2_000
MAX_EXCERPT_LENGTH = 1_000
_COURSE_CODE_PATTERN = re.compile(r"^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9._-]{1,39}$", re.IGNORECASE)
_TERM_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._/-]{1,39}$", re.IGNORECASE)


class HistoryFormatError(ValueError):
    """Raised when an import does not conform to the owned history format."""


@dataclass(frozen=True, slots=True)
class ParseCandidate:
    row_number: int
    source_locator: str
    raw_payload: dict[str, Any]
    normalized_payload: dict[str, Any]
    errors: tuple[dict[str, str], ...]
    warnings: tuple[dict[str, str], ...]
    confidence: int
    requires_confirmation: bool
    fingerprint: str


@dataclass(frozen=True, slots=True)
class ParseReport:
    schema_version: str
    parser_version: str
    source_kind: str
    candidates: tuple[ParseCandidate, ...]
    errors: tuple[dict[str, str], ...]
    metadata: dict[str, Any]

    @property
    def valid_candidates(self) -> tuple[ParseCandidate, ...]:
        return tuple(candidate for candidate in self.candidates if not candidate.errors)


class CandidateParser(Protocol):
    parser_version: str

    def parse(self, content: bytes, *, source_name: str) -> ParseReport: ...


def _fingerprint(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def _decimal_text(value: Any) -> str:
    raw = _text(value).replace(",", ".")
    if not raw:
        return ""
    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("grade must be a decimal number") from exc
    if not parsed.is_finite() or parsed < 0 or parsed > 5:
        raise ValueError("grade must be between 0 and 5")
    return format(parsed.quantize(Decimal("0.01")), "f")


def _integer(value: Any, *, field: str, minimum: int = 0, maximum: int = 255) -> int | None:
    raw = _text(value)
    if not raw:
        return None
    try:
        parsed = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer") from exc
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return parsed


def _normalize_row(
    raw_payload: Mapping[str, Any],
    *,
    row_number: int,
    source_locator: str,
    requires_confirmation: bool,
    confidence: int,
    source_metadata: Mapping[str, Any] | None = None,
) -> ParseCandidate:
    raw = {str(key): value for key, value in raw_payload.items()}
    normalized: dict[str, Any] = {}
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    course_code = _text(raw.get("course_code") or raw.get("code"))
    if not course_code:
        errors.append({"code": "course_code_required", "message": "course_code is required"})
    elif not _COURSE_CODE_PATTERN.fullmatch(course_code):
        errors.append({"code": "course_code_invalid", "message": "course_code has invalid format"})
    else:
        normalized["course_code"] = course_code.upper()

    term_code = _text(raw.get("term_code") or raw.get("term"))
    if not term_code:
        errors.append({"code": "term_code_required", "message": "term_code is required"})
    elif not _TERM_CODE_PATTERN.fullmatch(term_code):
        errors.append({"code": "term_code_invalid", "message": "term_code has invalid format"})
    else:
        normalized["term_code"] = term_code

    status = _text(raw.get("status")).upper()
    valid_statuses = {member.value for member in AttemptStatus}
    if not status:
        errors.append({"code": "status_required", "message": "status is required"})
    elif status not in valid_statuses:
        errors.append({"code": "status_invalid", "message": f"unsupported status: {status}"})
    else:
        normalized["status"] = status

    try:
        grade = _decimal_text(raw.get("grade"))
    except ValueError as exc:
        errors.append({"code": "grade_invalid", "message": str(exc)})
    else:
        if grade:
            normalized["grade"] = grade

    try:
        credits_value = (
            raw.get("credits_earned")
            if raw.get("credits_earned") not in (None, "")
            else raw.get("credits")
        )
        credits = _integer(credits_value, field="credits_earned")
    except ValueError as exc:
        errors.append({"code": "credits_invalid", "message": str(exc)})
    else:
        if credits is not None:
            normalized["credits_earned"] = credits

    try:
        attempt_number = _integer(
            (
                raw.get("attempt_number")
                if raw.get("attempt_number") not in (None, "")
                else raw.get("attempt")
            ),
            field="attempt_number",
            minimum=1,
            maximum=99,
        )
    except ValueError as exc:
        errors.append({"code": "attempt_number_invalid", "message": str(exc)})
        attempt_number = None
    normalized["attempt_number"] = attempt_number or 1

    course_name = _text(raw.get("course_name") or raw.get("name"))
    external_code = _text(raw.get("external_code") or raw.get("equivalence_code"))
    if course_name:
        normalized["course_name"] = course_name[:240]
    if external_code:
        normalized["external_code"] = external_code[:120]
    normalized["source_locator"] = source_locator
    if source_metadata:
        normalized["source_metadata"] = dict(source_metadata)

    if (
        normalized.get("status") in {AttemptStatus.PASSED.value, AttemptStatus.VALIDATED.value}
        and "grade" not in normalized
    ):
        warnings.append(
            {"code": "grade_missing", "message": "approved status has no grade; confirm explicitly"}
        )
    if normalized.get("status") in {
        AttemptStatus.FAILED.value,
        AttemptStatus.CANCELLED.value,
        AttemptStatus.WITHDRAWN.value,
        AttemptStatus.ANNULLED.value,
    } and normalized.get("credits_earned", 0) not in {0, None}:
        errors.append(
            {
                "code": "credits_inconsistent",
                "message": "non-approved status cannot carry earned credits",
            }
        )

    return ParseCandidate(
        row_number=row_number,
        source_locator=source_locator,
        raw_payload=raw,
        normalized_payload=normalized,
        errors=tuple(errors),
        warnings=tuple(warnings),
        confidence=max(0, min(100, confidence)),
        requires_confirmation=requires_confirmation,
        fingerprint=_fingerprint(
            {
                key: value
                for key, value in normalized.items()
                if key not in {"source_locator", "source_metadata"}
            }
        ),
    )


def _duplicate_warnings(candidates: Sequence[ParseCandidate]) -> tuple[ParseCandidate, ...]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.fingerprint] = counts.get(candidate.fingerprint, 0) + 1
    updated: list[ParseCandidate] = []
    for candidate in candidates:
        if counts[candidate.fingerprint] < 2:
            updated.append(candidate)
            continue
        warnings = candidate.warnings + (
            {
                "code": "duplicate_in_file",
                "message": "same normalized record appears more than once",
            },
        )
        updated.append(
            ParseCandidate(
                row_number=candidate.row_number,
                source_locator=candidate.source_locator,
                raw_payload=candidate.raw_payload,
                normalized_payload=candidate.normalized_payload,
                errors=candidate.errors,
                warnings=warnings,
                confidence=candidate.confidence,
                requires_confirmation=candidate.requires_confirmation,
                fingerprint=candidate.fingerprint,
            )
        )
    return tuple(updated)


def _report(
    *,
    source_kind: str,
    candidates: Sequence[ParseCandidate],
    errors: Sequence[dict[str, str]] = (),
    metadata: Mapping[str, Any] | None = None,
) -> ParseReport:
    return ParseReport(
        schema_version=HISTORY_SCHEMA_VERSION,
        parser_version=HISTORY_PARSER_VERSION,
        source_kind=source_kind,
        candidates=_duplicate_warnings(candidates),
        errors=tuple(errors),
        metadata=dict(metadata or {}),
    )


def parse_json_history(content: bytes) -> ParseReport:
    try:
        document = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoryFormatError("JSON must be valid UTF-8 JSON") from exc
    if not isinstance(document, Mapping):
        raise HistoryFormatError("JSON root must be an object")
    if document.get("schema_version") != HISTORY_SCHEMA_VERSION:
        raise HistoryFormatError(f"schema_version must be {HISTORY_SCHEMA_VERSION}")
    records = document.get("records")
    if not isinstance(records, list):
        raise HistoryFormatError("records must be an array")
    if len(records) > MAX_RECORDS:
        raise HistoryFormatError(f"records cannot exceed {MAX_RECORDS}")
    candidates: list[ParseCandidate] = []
    errors: list[dict[str, str]] = []
    for index, value in enumerate(records, start=1):
        if not isinstance(value, Mapping):
            errors.append(
                {"code": "row_not_object", "message": f"records[{index - 1}] must be an object"}
            )
            continue
        source_locator = _text(value.get("source_locator")) or f"row:{index + 1}"
        candidates.append(
            _normalize_row(
                value,
                row_number=index,
                source_locator=source_locator,
                requires_confirmation=False,
                confidence=100,
            )
        )
    if not candidates:
        errors.append({"code": "no_records", "message": "records must contain at least one row"})
    return _report(
        source_kind="JSON_HISTORY",
        candidates=candidates,
        errors=errors,
        metadata={"records_declared": len(records)},
    )


def parse_csv_history(content: bytes) -> ParseReport:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HistoryFormatError("CSV must be UTF-8") from exc
    if "\x00" in text:
        raise HistoryFormatError("CSV contains a NUL byte")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    headers = {str(header or "").strip() for header in reader.fieldnames or []}
    required = {"course_code", "term_code", "status"}
    missing = sorted(required - headers)
    if missing:
        raise HistoryFormatError(f"CSV is missing required columns: {', '.join(missing)}")
    candidates: list[ParseCandidate] = []
    for index, value in enumerate(reader, start=2):
        source_locator = _text(value.get("source_locator")) or f"row:{index}"
        candidates.append(
            _normalize_row(
                value,
                row_number=index - 1,
                source_locator=source_locator,
                requires_confirmation=False,
                confidence=100,
            )
        )
        if len(candidates) > MAX_RECORDS:
            raise HistoryFormatError(f"records cannot exceed {MAX_RECORDS}")
    errors: list[dict[str, str]] = []
    if not candidates:
        errors.append({"code": "no_records", "message": "CSV must contain at least one data row"})
    return _report(
        source_kind="CSV_HISTORY",
        candidates=candidates,
        errors=errors,
        metadata={"headers": sorted(headers), "records_declared": len(candidates)},
    )


def _pdf_row(line: str) -> list[str] | None:
    parts = [part.strip() for part in re.split(r"\s{2,}|\t|\|", line.strip())]
    if len(parts) < 3:
        return None
    if not _COURSE_CODE_PATTERN.fullmatch(parts[0]):
        return None
    if not _TERM_CODE_PATTERN.fullmatch(parts[1]):
        return None
    return parts


class PdfHistoryCandidateParser:
    """Conservative text-table parser; every candidate remains review-required."""

    parser_version = f"{HISTORY_PARSER_VERSION}+pypdf-6.10.0"

    def parse(self, content: bytes, *, source_name: str) -> ParseReport:
        del source_name
        if not content.startswith(b"%PDF-"):
            raise HistoryFormatError("PDF signature is missing")
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content), strict=False)
        except Exception as exc:
            raise HistoryFormatError("PDF could not be parsed safely") from exc
        if len(reader.pages) > 200:
            raise HistoryFormatError("PDF cannot contain more than 200 pages")
        candidates: list[ParseCandidate] = []
        errors: list[dict[str, str]] = []
        for page_index, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text(extraction_mode="layout") or ""
            except Exception as exc:
                errors.append(
                    {
                        "code": "pdf_page_extract_failed",
                        "message": f"page {page_index} could not be extracted: {type(exc).__name__}",
                    }
                )
                continue
            for line_index, line in enumerate(text.splitlines(), start=1):
                parts = _pdf_row(line)
                if parts is None:
                    continue
                payload: dict[str, Any] = {
                    "course_code": parts[0],
                    "term_code": parts[1],
                    "status": parts[2],
                    "grade": parts[3] if len(parts) > 3 else "",
                    "credits_earned": parts[4] if len(parts) > 4 else "",
                    "source_locator": f"page:{page_index}:line:{line_index}",
                }
                candidates.append(
                    _normalize_row(
                        payload,
                        row_number=len(candidates) + 1,
                        source_locator=payload["source_locator"],
                        requires_confirmation=True,
                        confidence=60,
                        source_metadata={
                            "page": page_index,
                            "line": line_index,
                            "text_excerpt": line[:MAX_EXCERPT_LENGTH],
                            "extraction": "pypdf-text-only",
                        },
                    )
                )
                if len(candidates) >= MAX_RECORDS:
                    errors.append(
                        {
                            "code": "record_limit_reached",
                            "message": f"PDF candidate limit {MAX_RECORDS} reached",
                        }
                    )
                    return _report(
                        source_kind="PDF_HISTORY",
                        candidates=candidates,
                        errors=errors,
                        metadata={"pages": len(reader.pages), "text_extraction": "pypdf"},
                    )
        if not candidates:
            errors.append(
                {
                    "code": "pdf_no_candidate_rows",
                    "message": "No conservative course rows were extracted; manual correction is required",
                }
            )
        return _report(
            source_kind="PDF_HISTORY",
            candidates=candidates,
            errors=errors,
            metadata={"pages": len(reader.pages), "text_extraction": "pypdf"},
        )


def parse_history_bytes(content: bytes, *, source_name: str, mime_type: str = "") -> ParseReport:
    suffix = source_name.lower().rsplit(".", 1)[-1] if "." in source_name else ""
    if suffix == "json" or mime_type == "application/json":
        return parse_json_history(content)
    if suffix == "csv" or mime_type in {"text/csv", "application/csv"}:
        return parse_csv_history(content)
    if suffix == "pdf" or mime_type == "application/pdf":
        return PdfHistoryCandidateParser().parse(content, source_name=source_name)
    raise HistoryFormatError("Only CSV, JSON and PDF history files are supported")
