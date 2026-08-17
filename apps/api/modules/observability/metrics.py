from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from django.conf import settings
from opentelemetry import metrics as otel_metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource

from .redaction import safe_route
from .tracing import mark_span_failure, mark_span_success, operation_span

P = ParamSpec("P")
R = TypeVar("R")

_BUCKETS = (0.005, 0.025, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_lock = threading.RLock()
_counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = defaultdict(int)


@dataclass
class _Histogram:
    count: int = 0
    total: float = 0.0
    buckets: dict[float, int] = field(default_factory=lambda: {bucket: 0 for bucket in _BUCKETS})


_histograms: dict[tuple[str, tuple[tuple[str, str], ...]], _Histogram] = {}
_otel_configured = False
_otel_instruments: dict[str, Any] = {}


def _enabled(value: object) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


def _labels(values: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
    # Every label is bounded and comes from a controlled vocabulary at the
    # call site.  This is a second line of defence against cardinality abuse.
    return tuple(sorted((str(key), str(value)[:80]) for key, value in values.items()))


def configure_otel_metrics() -> None:
    global _otel_configured
    if _otel_configured:
        return
    readers: list[Any] = []
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT") or os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

            readers.append(
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(
                        endpoint=endpoint,
                        timeout=float(os.environ.get("OTEL_EXPORTER_OTLP_TIMEOUT", "5")),
                    ),
                    export_interval_millis=int(
                        os.environ.get("OTEL_METRIC_EXPORT_INTERVAL_MS", "60000")
                    ),
                )
            )
        except ImportError, ValueError:
            pass

    provider = MeterProvider(
        resource=Resource.create(
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
        ),
        metric_readers=readers,
    )
    with suppress(Exception):
        otel_metrics.set_meter_provider(provider)
    meter = otel_metrics.get_meter("curriculum-navigator.api")
    _otel_instruments.update(
        {
            "http_requests": meter.create_counter(
                "curriculum.http.requests", unit="{request}", description="Completed HTTP requests"
            ),
            "http_duration": meter.create_histogram(
                "curriculum.http.duration", unit="s", description="HTTP request duration"
            ),
            "db_checks": meter.create_counter(
                "curriculum.db.health_checks", unit="{check}", description="Database health checks"
            ),
            "jobs": meter.create_counter(
                "curriculum.jobs", unit="{job}", description="Background job outcomes"
            ),
            "job_duration": meter.create_histogram(
                "curriculum.job.duration", unit="s", description="Background job duration"
            ),
            "domain_operations": meter.create_counter(
                "curriculum.domain.operations",
                unit="{operation}",
                description="Domain operation outcomes",
            ),
            "domain_duration": meter.create_histogram(
                "curriculum.domain.duration", unit="s", description="Domain operation duration"
            ),
        }
    )
    _otel_configured = True


def _otel_add(name: str, value: int | float, labels: dict[str, str]) -> None:
    configure_otel_metrics()
    instrument = _otel_instruments.get(name)
    if instrument is not None:
        instrument.add(value, attributes=labels)


def _otel_record(name: str, value: float, labels: dict[str, str]) -> None:
    configure_otel_metrics()
    instrument = _otel_instruments.get(name)
    if instrument is not None:
        instrument.record(value, attributes=labels)


def _counter(name: str, labels: Mapping[str, object], *, increment: int = 1) -> None:
    normalized = _labels(labels)
    with _lock:
        _counters[(name, normalized)] += increment
    _otel_add(name, increment, dict(normalized))


def _histogram(name: str, value: float, labels: Mapping[str, object]) -> None:
    normalized = _labels(labels)
    bounded = max(0.0, min(float(value), 3600.0))
    with _lock:
        histogram = _histograms.setdefault((name, normalized), _Histogram())
        histogram.count += 1
        histogram.total += bounded
        for bucket in _BUCKETS:
            if bounded <= bucket:
                histogram.buckets[bucket] += 1
    _otel_record(name, bounded, dict(normalized))


def record_request(*, method: str, route: str, status_code: int, duration_seconds: float) -> None:
    status_class = f"{max(100, min(status_code, 599)) // 100}xx"
    labels = {
        "method": method.upper()[:12],
        "route": safe_route(route),
        "status_class": status_class,
    }
    _counter("http_requests", labels)
    _histogram("http_duration", duration_seconds, labels)


def record_db_check(outcome: str) -> None:
    _counter("db_checks", {"outcome": outcome if outcome in {"ok", "error"} else "unknown"})


def record_job(*, kind: str, status: str, duration_seconds: float) -> None:
    labels = {"kind": kind[:64], "status": status[:32]}
    _counter("jobs", labels)
    _histogram("job_duration", duration_seconds, labels)


def record_domain_operation(*, kind: str, status: str, duration_seconds: float) -> None:
    labels = {"kind": kind[:64], "status": status[:32]}
    _counter("domain_operations", labels)
    _histogram("domain_duration", duration_seconds, labels)


def record_event(*, name: str, outcome: str = "counted") -> None:
    _counter("domain_operations", {"kind": name[:64], "status": outcome[:32]})


def _observe[**P, R](
    fn: Callable[P, R],
    *,
    kind: str,
    job: bool,
) -> Callable[P, R]:
    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        started = time.perf_counter()
        status = "ok"
        try:
            with operation_span(kind) as span:
                try:
                    result = fn(*args, **kwargs)
                except Exception as error:
                    status = "error"
                    mark_span_failure(span, error)
                    raise
                mark_span_success(span, status_code=200)
                return result
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.perf_counter() - started
            if job:
                record_job(kind=kind, status=status, duration_seconds=duration)
            else:
                record_domain_operation(kind=kind, status=status, duration_seconds=duration)

    return wrapper


def measure_domain_timing(kind: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    return lambda fn: _observe(fn, kind=kind, job=False)


def measure_job_timing(kind: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    return lambda fn: _observe(fn, kind=kind, job=True)


def _label_text(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    escaped = [
        f'{key}="{value.replace(chr(92), chr(92) + chr(92)).replace(chr(34), chr(92) + chr(34))}"'
        for key, value in labels
    ]
    return "{" + ",".join(escaped) + "}"


def render_prometheus() -> str:
    """Render bounded process metrics for a collector sidecar/scraper."""

    lines: list[str] = []
    with _lock:
        counter_items = sorted(_counters.items())
        histogram_items = sorted(_histograms.items())
    seen_types: set[str] = set()
    for (name, labels), value in counter_items:
        metric_name = {
            "http_requests": "curriculum_http_requests_total",
            "db_checks": "curriculum_db_health_checks_total",
            "jobs": "curriculum_jobs_total",
            "domain_operations": "curriculum_domain_operations_total",
        }[name]
        if metric_name not in seen_types:
            lines.append(f"# TYPE {metric_name} counter")
            seen_types.add(metric_name)
        lines.append(f"{metric_name}{_label_text(labels)} {value}")
    for (name, labels), histogram in histogram_items:
        metric_name = {
            "http_duration": "curriculum_http_duration_seconds",
            "job_duration": "curriculum_job_duration_seconds",
            "domain_duration": "curriculum_domain_duration_seconds",
        }[name]
        if metric_name not in seen_types:
            lines.append(f"# TYPE {metric_name} histogram")
            seen_types.add(metric_name)
        for bucket in _BUCKETS:
            bucket_labels = dict(labels)
            bucket_labels["le"] = str(bucket)
            lines.append(
                f"{metric_name}_bucket{_label_text(_labels(bucket_labels))} {histogram.buckets[bucket]}"
            )
        bucket_labels = dict(labels)
        bucket_labels["le"] = "+Inf"
        lines.append(f"{metric_name}_bucket{_label_text(_labels(bucket_labels))} {histogram.count}")
        lines.append(f"{metric_name}_sum{_label_text(labels)} {histogram.total:.6f}")
        lines.append(f"{metric_name}_count{_label_text(labels)} {histogram.count}")
    return "\n".join(lines) + ("\n" if lines else "")


def snapshot_metrics() -> dict[str, float]:
    """Return aggregate, label-free metrics suitable for a health response."""

    aggregate: dict[str, float] = defaultdict(float)
    with _lock:
        for (name, _labels_value), value in _counters.items():
            aggregate[name] += float(value)
        for (name, _labels_value), histogram in _histograms.items():
            aggregate[f"{name}.count"] += float(histogram.count)
            aggregate[f"{name}.sum_seconds"] += histogram.total
    return dict(sorted(aggregate.items()))


def metrics_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": getattr(settings, "OTEL_SERVICE_NAME", "curriculum-navigator-api"),
        "generated_at": datetime.now(UTC),
        "metrics": snapshot_metrics(),
    }
