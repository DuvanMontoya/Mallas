from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.http import HttpRequest

from modules.identity.models import AuditEvent

_SENSITIVE_KEY_PARTS = ("password", "token", "secret", "authorization", "cookie", "email")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


def digest_identifier(value: str) -> str:
    """Return a keyed digest suitable for correlation without storing PII."""

    normalized = value.strip().lower().encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), normalized, hashlib.sha256).hexdigest()


def _is_sensitive_key(key: str) -> bool:
    return any(part in key.lower() for part in _SENSITIVE_KEY_PARTS)


def _safe_value(value: Any, *, key: str = "", depth: int = 0) -> Any:
    if _is_sensitive_key(key):
        return "[REDACTED]"
    if depth > 4:
        return "[REDACTED_NESTED]"
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {
            str(child_key): _safe_value(child_value, key=str(child_key), depth=depth + 1)
            for child_key, child_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_safe_value(item, depth=depth + 1) for item in value]
    return str(value)


def _safe_metadata(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    return {str(key): _safe_value(raw, key=str(key)) for key, raw in value.items()}


def request_ip_hash(request: HttpRequest) -> str:
    address = request.META.get("REMOTE_ADDR", "")
    if getattr(settings, "TRUST_PROXY_HEADERS", False):
        forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
        address = forwarded or address
    return digest_identifier(address) if address else ""


def record_audit_event(
    request: HttpRequest | None,
    *,
    action: str,
    actor: Any | None = None,
    object_type: str = "",
    object_id: Any | None = None,
    institution_id: Any | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AuditEvent:
    request_user = getattr(request, "user", None) if request is not None else None
    resolved_actor = (
        actor
        if actor is not None
        else (request_user if getattr(request_user, "is_authenticated", False) else None)
    )
    request_id = getattr(request, "correlation_id", "") if request is not None else ""
    if not isinstance(request_id, str) or not _REQUEST_ID_PATTERN.fullmatch(request_id):
        request_id = ""
    return AuditEvent.objects.create(
        actor=resolved_actor,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id is not None else "",
        institution_id=institution_id,
        request_id=request_id[:80],
        ip_hash=request_ip_hash(request) if request is not None else "",
        metadata=_safe_metadata(metadata),
    )
