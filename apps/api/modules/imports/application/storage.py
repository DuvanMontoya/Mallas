from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from django.conf import settings

MAX_ARTIFACT_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {"csv", "json", "pdf"}
_EXECUTABLE_SIGNATURES = (
    b"MZ",
    b"\x7fELF",
    b"PK\x03\x04",
    b"#!",
    b"\xca\xfe\xba\xbe",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xce",
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ArtifactValidationError(ValueError):
    """Raised before untrusted import bytes are persisted."""


@dataclass(frozen=True, slots=True)
class ValidatedArtifact:
    original_filename: str
    mime_type: str
    content_sha256: str
    size_bytes: int


def _safe_original_filename(filename: str) -> str:
    basename = Path(filename.replace("\\", "/")).name.strip()
    if not basename or basename in {".", ".."}:
        raise ArtifactValidationError("A non-empty filename is required")
    if len(basename) > 255:
        basename = basename[-255:]
    if any(ord(character) < 32 for character in basename):
        raise ArtifactValidationError("Filename contains control characters")
    return basename


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _mime_for_extension(extension: str) -> str:
    return {
        "csv": "text/csv",
        "json": "application/json",
        "pdf": "application/pdf",
    }.get(extension, "")


def validate_artifact(
    *, filename: str, content: bytes, declared_mime: str = ""
) -> ValidatedArtifact:
    safe_name = _safe_original_filename(filename)
    extension = _extension(safe_name)
    if extension not in ALLOWED_EXTENSIONS:
        raise ArtifactValidationError("Only .csv, .json and .pdf files are supported")
    size_bytes = len(content)
    if size_bytes == 0:
        raise ArtifactValidationError("The uploaded file must not be empty")
    if size_bytes > MAX_ARTIFACT_BYTES:
        raise ArtifactValidationError(f"The uploaded file cannot exceed {MAX_ARTIFACT_BYTES} bytes")
    if content.startswith(_EXECUTABLE_SIGNATURES):
        raise ArtifactValidationError("Executable or archive signatures are not accepted")
    if extension == "pdf" and not content.startswith(b"%PDF-"):
        raise ArtifactValidationError("The PDF signature does not match the filename")
    if extension != "pdf":
        if b"\x00" in content:
            raise ArtifactValidationError("Text imports cannot contain NUL bytes")
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ArtifactValidationError("CSV/JSON imports must be UTF-8") from exc
    expected_mime = _mime_for_extension(extension)
    if declared_mime and declared_mime not in {
        expected_mime,
        "application/octet-stream",
        "text/plain" if extension == "csv" else expected_mime,
    }:
        raise ArtifactValidationError("Declared MIME type does not match the file extension")
    return ValidatedArtifact(
        original_filename=safe_name,
        mime_type=expected_mime,
        content_sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=size_bytes,
    )


def private_storage_root() -> Path:
    configured = getattr(settings, "PRIVATE_IMPORT_STORAGE_ROOT", "")
    root = (
        Path(configured) if configured else Path(settings.PROJECT_ROOT) / "var" / "private-imports"
    )
    return root.resolve()


def _artifact_path(*, batch_id: UUID | str, content_sha256: str) -> Path:
    root = private_storage_root()
    if not _SHA256_PATTERN.fullmatch(content_sha256.lower()):
        raise ArtifactValidationError("Invalid artifact content hash")
    batch_text = str(batch_id)
    if not batch_text or any(separator in batch_text for separator in ("/", "\\")):
        raise ArtifactValidationError("Invalid artifact batch path")
    path = (root / "imports" / str(batch_id) / f"{content_sha256}.bin").resolve()
    if not path.is_relative_to(root):
        raise ArtifactValidationError("Invalid artifact storage path")
    return path


def store_artifact(*, batch_id: UUID | str, content_sha256: str, content: bytes) -> str:
    path = _artifact_path(batch_id=batch_id, content_sha256=content_sha256)
    root = private_storage_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        file_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        file_flags |= getattr(os, "O_BINARY", 0)
        descriptor = os.open(path, file_flags, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
    except FileExistsError:
        existing = path.read_bytes()
        if existing != content:
            raise ArtifactValidationError("Artifact storage collision detected") from None
    return str(path.relative_to(private_storage_root())).replace("\\", "/")


def read_artifact(storage_key: str) -> bytes:
    if not storage_key or "\x00" in storage_key:
        raise ArtifactValidationError("Invalid artifact storage path")
    root = private_storage_root()
    path = (root / storage_key).resolve()
    if not path.is_relative_to(root):
        raise ArtifactValidationError("Invalid artifact storage path")
    if path.is_symlink() or not path.is_file():
        raise ArtifactValidationError("Artifact storage path is not a regular file")
    return path.read_bytes()


def artifact_metadata(*, filename: str, mime_type: str, size_bytes: int) -> dict[str, Any]:
    return {
        "original_filename": filename,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "storage": "private-filesystem",
        "execution": "never-executed",
    }
