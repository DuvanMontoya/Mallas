from __future__ import annotations

import json
import logging
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

from .redaction import redact
from .tracing import current_trace_ids

_correlation_id: ContextVar[str | None] = ContextVar("observability_correlation_id", default=None)


def set_correlation_id(value: str) -> Token[str | None]:
    return _correlation_id.set(value)


def reset_correlation_id(token: Token[str | None]) -> None:
    _correlation_id.reset(token)


def current_correlation_id() -> str | None:
    return _correlation_id.get()


class JsonFormatter(logging.Formatter):
    """Emit bounded JSON records with trace context and no exception payloads."""

    def format(self, record: logging.LogRecord) -> str:
        trace_id, span_id = current_trace_ids()
        structured = getattr(record, "structured", {})
        if not isinstance(structured, dict):
            structured = {"value": structured}
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }
        correlation_id = getattr(record, "correlation_id", None) or current_correlation_id()
        if correlation_id:
            # The ID was validated by ensure_correlation_id before it reached
            # this formatter; preserving it is what makes log correlation work.
            payload["correlation_id"] = str(correlation_id)[:80]
        if trace_id:
            payload["trace_id"] = trace_id
        if span_id:
            payload["span_id"] = span_id
        payload.update(redact(structured))
        # Never call formatException here: Django and database exception
        # messages can contain query values or academic identifiers.
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def record_log(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    correlation_id: str | None = None,
    **fields: Any,
) -> None:
    """Record an allowlisted event through the defensive JSON formatter."""

    logger.log(
        level,
        event,
        extra={
            "structured": {"event": event, **fields},
            "correlation_id": correlation_id or current_correlation_id(),
        },
    )
