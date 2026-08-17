from __future__ import annotations

import logging
import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from modules.common.api import ensure_correlation_id

from .logging import record_log, reset_correlation_id, set_correlation_id
from .metrics import record_request
from .redaction import safe_exception_type, safe_route
from .tracing import mark_span_failure, mark_span_success, request_span

logger = logging.getLogger(__name__)


class ObservabilityMiddleware:
    """Attach safe request telemetry without changing domain behavior."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = ensure_correlation_id(request)
        context_token = set_correlation_id(correlation_id)
        started = time.perf_counter()
        route = safe_route(request.path)
        response: HttpResponse | None = None
        status_code = 500
        span_context = None
        request_error: BaseException | None = None
        try:
            with request_span(
                method=request.method,
                path=request.path,
                correlation_id=correlation_id,
                headers=request.headers,
            ) as span:
                span_context = span.get_span_context()
                try:
                    response = self.get_response(request)
                    status_code = response.status_code
                    mark_span_success(span, status_code=status_code)
                except Exception as error:
                    request_error = error
                    mark_span_failure(span, error)
                    record_log(
                        logger,
                        "http.request.failed",
                        level=logging.ERROR,
                        correlation_id=correlation_id,
                        method=request.method,
                        route=route,
                        status_code=500,
                        error_type=safe_exception_type(error),
                    )
                    raise
            return response
        finally:
            duration_seconds = time.perf_counter() - started
            record_request(
                method=request.method,
                route=route,
                status_code=status_code,
                duration_seconds=duration_seconds,
            )
            if response is not None:
                response["X-Request-ID"] = correlation_id
                private_prefixes = (
                    "/api/v1/auth/",
                    "/api/v1/history/",
                    "/api/v1/imports/",
                    "/api/v1/scenarios",
                    "/api/v1/audit",
                    "/api/v1/analytics/student",
                    "/api/v1/notifications",
                    "/api/v1/academic-overview",
                    "/api/v1/curriculum-map",
                    "/api/v1/dependency-graph",
                    "/api/v1/offerings",
                    "/api/v1/optimization-runs",
                )
                if request.path.startswith("/api/v1/health/"):
                    response["Cache-Control"] = "no-store"
                elif request.path.startswith(private_prefixes):
                    response["Cache-Control"] = "private, no-store"
                    response["Pragma"] = "no-cache"
                if span_context is not None and span_context.is_valid:
                    response["X-Trace-ID"] = f"{span_context.trace_id:032x}"
                record_log(
                    logger,
                    "http.request.completed",
                    correlation_id=correlation_id,
                    method=request.method,
                    route=route,
                    status_code=status_code,
                    duration_ms=round(duration_seconds * 1000, 3),
                    outcome="error" if request_error is not None or status_code >= 500 else "ok",
                )
            reset_correlation_id(context_token)
