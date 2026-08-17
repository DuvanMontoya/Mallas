from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"
_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_JWT = re.compile(r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
_LONG_NUMERIC = re.compile(r"\d{6,}")
_LONG_HEX = re.compile(r"^[0-9a-fA-F]{24,}$")
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|secret|token|authorization|cookie|session|csrf|api[_-]?key|"
    r"private[_-]?key|credential|file|content|body|raw|email|phone|ip|student|enrollment|"
    r"user[_-]?id|account[_-]?id|trace[_-]?state|saml|oauth)",
    re.IGNORECASE,
)


def _sanitize_text(value: str) -> str:
    value = _BEARER.sub(REDACTED, value)
    value = _JWT.sub(REDACTED, value)
    value = _EMAIL.sub(REDACTED, value)
    value = _UUID.sub("[ID]", value)
    value = _LONG_NUMERIC.sub("[ID]", value)
    if len(value) > 240:
        return f"{value[:237]}..."
    return value


def redact(value: Any, *, key: str | None = None, depth: int = 0) -> Any:
    """Return a bounded, JSON-safe representation with sensitive fields removed.

    Telemetry uses an allowlist at the call sites, but this defensive layer is
    still applied to every structured field so a future call site cannot leak a
    password, token, uploaded file, or academic payload accidentally.
    """

    if key and _SENSITIVE_KEY.search(key):
        return REDACTED
    if depth > 4:
        return "[TRUNCATED]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, Mapping):
        return {
            str(item_key): redact(item_value, key=str(item_key), depth=depth + 1)
            for item_key, item_value in list(value.items())[:32]
        }
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [redact(item, depth=depth + 1) for item in list(value)[:16]]
    return _sanitize_text(type(value).__name__)


def safe_route(path: str) -> str:
    """Normalize a request path without recording identifiers or query data."""

    raw_path = path.split("?", 1)[0]
    segments: list[str] = []
    for segment in raw_path.split("/"):
        if not segment:
            continue
        if (
            _UUID.fullmatch(segment)
            or _LONG_NUMERIC.fullmatch(segment)
            or _LONG_HEX.fullmatch(segment)
        ):
            segments.append(":id")
        elif _SAFE_SEGMENT.fullmatch(segment):
            segments.append(segment)
        else:
            segments.append(":segment")
    return "/" + "/".join(segments) if segments else "/"


def safe_exception_type(error: BaseException) -> str:
    """Expose only a stable exception class name, never its message or args."""

    return type(error).__name__[:120]
