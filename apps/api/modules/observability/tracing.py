from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from django.conf import settings
from opentelemetry import context, propagate, trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Span, SpanKind, Status, StatusCode, get_current_span

from .redaction import safe_exception_type, safe_route

_TRACER_NAME = "curriculum-navigator.api"
_configured = False
_provider: TracerProvider | None = None
_capture_exporter: InMemorySpanExporter | None = None


def _enabled(value: object) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


def configure_tracing() -> TracerProvider:
    """Configure one process-wide SDK provider and return it.

    Export is opt-in through OTEL_EXPORTER_OTLP_* environment variables.  The
    application therefore remains useful in local development without making
    outbound telemetry requests, while production can point it at a collector.
    """

    global _capture_exporter, _configured, _provider
    if _configured and _provider is not None:
        return _provider

    resource = Resource.create(
        {
            "service.name": os.environ.get(
                "OTEL_SERVICE_NAME",
                getattr(settings, "OTEL_SERVICE_NAME", "curriculum-navigator-api"),
            ),
            "service.version": getattr(settings, "APP_VERSION", "unknown"),
            "deployment.environment": "development"
            if getattr(settings, "DEBUG", False)
            else "production",
        }
    )
    provider = TracerProvider(resource=resource)

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(
                        endpoint=endpoint,
                        timeout=float(os.environ.get("OTEL_EXPORTER_OTLP_TIMEOUT", "5")),
                    )
                )
            )
        except ImportError, ValueError:
            # Telemetry configuration must not prevent the API from starting.
            # The health endpoint still reports application health; deployment
            # diagnostics should inspect collector/exporter configuration.
            pass

    if _enabled(
        os.environ.get("OTEL_TRACE_CAPTURE", getattr(settings, "OTEL_TRACE_CAPTURE", False))
    ):
        _capture_exporter = InMemorySpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(_capture_exporter))

    try:
        trace.set_tracer_provider(provider)
    except Exception:
        # A host embedding Django may have configured a provider before Django
        # loaded.  Reusing the existing provider is safer than failing startup.
        existing = trace.get_tracer_provider()
        if isinstance(existing, TracerProvider):
            provider = existing
    _provider = provider
    _configured = True
    return provider


def tracer() -> trace.Tracer:
    configure_tracing()
    return trace.get_tracer(_TRACER_NAME)


def current_trace_ids() -> tuple[str | None, str | None]:
    span = get_current_span()
    span_context = span.get_span_context()
    if not span_context.is_valid:
        return None, None
    return f"{span_context.trace_id:032x}", f"{span_context.span_id:016x}"


def captured_spans() -> tuple[Any, ...]:
    """Return captured spans for diagnostics/tests without exposing payloads."""

    if _capture_exporter is None:
        return ()
    return tuple(_capture_exporter.get_finished_spans())


@contextmanager
def request_span(
    *,
    method: str,
    path: str,
    correlation_id: str,
    headers: Mapping[str, str],
) -> Iterator[Span]:
    carrier = {key.lower(): value for key, value in headers.items() if key.lower() == "traceparent"}
    parent_context = propagate.extract(carrier) if carrier else context.get_current()
    route = safe_route(path)
    with tracer().start_as_current_span(
        f"{method.upper()} {route}",
        context=parent_context,
        kind=SpanKind.SERVER,
        attributes={
            "http.request.method": method.upper(),
            "http.route": route,
            "curriculum.correlation_id": correlation_id,
        },
    ) as span:
        yield span


@contextmanager
def operation_span(name: str) -> Iterator[Span]:
    with tracer().start_as_current_span(
        f"curriculum.{safe_route(name).removeprefix('/')}",
        kind=SpanKind.INTERNAL,
        attributes={"curriculum.operation": safe_route(name)},
    ) as span:
        yield span


def mark_span_success(span: Span, *, status_code: int) -> None:
    span.set_attribute("http.response.status_code", status_code)
    if status_code >= 500:
        span.set_status(Status(StatusCode.ERROR))
    else:
        span.set_status(Status(StatusCode.OK))


def mark_span_failure(span: Span, error: BaseException) -> None:
    # Avoid Span.record_exception: it serializes the exception message, which
    # could contain identifiers or database details from an unexpected error.
    span.set_attribute("error.type", safe_exception_type(error))
    span.set_status(Status(StatusCode.ERROR))
