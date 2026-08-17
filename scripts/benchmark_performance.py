#!/usr/bin/env python3
"""Measure the critical domain/read paths without changing application state.

The benchmark intentionally reports p50/p95 and query counts instead of imposing
machine-specific latency thresholds.  The recorded environment and the query
plans are part of the P21 performance evidence; CI regression tests enforce
stable query budgets and semantic output separately.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import connection, transaction  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402

from domain.rules import AuditContext, RevisionFacts, evaluate_rule, parse_rule  # noqa: E402
from modules.audit.application.overview import build_academic_overview  # noqa: E402
from modules.audit.models import DegreeAuditRun  # noqa: E402
from modules.curriculum.application.graph import build_dependency_graph  # noqa: E402
from modules.curriculum.application.map import build_curriculum_map  # noqa: E402
from modules.curriculum.models import CurriculumRevision  # noqa: E402
from modules.offerings.models import AcademicTerm  # noqa: E402
from modules.student_records.models import ProgramEnrollment, StudentProfile  # noqa: E402

BASELINE = (
    ROOT
    / "data"
    / "curricula"
    / "unal"
    / "bogota"
    / "estadistica"
    / "2514"
    / "plan_2514_acuerdo_496_2023.json"
)


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((percentile / 100) * (len(ordered) - 1)))))
    return ordered[index]


def _payload_bytes(value: object) -> int:
    return len(json.dumps(value, default=str, separators=(",", ":")).encode("utf-8"))


def _measure_service(name: str, operation: Callable[[], object], iterations: int) -> None:
    operation()
    samples_ms: list[float] = []
    query_counts: list[int] = []
    sizes: list[int] = []
    for _ in range(iterations):
        with CaptureQueriesContext(connection) as queries:
            started = time.perf_counter()
            result = operation()
            elapsed = time.perf_counter() - started
        samples_ms.append(elapsed * 1000)
        query_counts.append(len(queries))
        sizes.append(_payload_bytes(result))
    print(
        "service="
        f"{name} iterations={iterations} p50_ms={_percentile(samples_ms, 50):.3f} "
        f"p95_ms={_percentile(samples_ms, 95):.3f} max_ms={max(samples_ms):.3f} "
        f"queries_min={min(query_counts)} queries_max={max(query_counts)} "
        f"payload_bytes={min(sizes)}..{max(sizes)}"
    )


def _benchmark_rules(iterations: int) -> None:
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    rules = [parse_rule(row["ast"]) for row in data["enrollment_requirements"]]
    context = AuditContext(
        revision=RevisionFacts(total_credits=141),
        earned_credits=113,
        passed_courses=frozenset(),
    )
    samples_us: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        for rule in rules:
            evaluate_rule(rule, context)
        samples_us.append((time.perf_counter() - started) / len(rules) * 1_000_000)
    print(
        f"rules iterations={iterations} evaluations_per_iteration={len(rules)} "
        f"p50_us={_percentile(samples_us, 50):.3f} "
        f"p95_us={_percentile(samples_us, 95):.3f} max_us={max(samples_us):.3f}"
    )


def _benchmark_ephemeral_overview(iterations: int) -> None:
    revision = (
        CurriculumRevision.objects.select_related("plan__program", "plan__program__faculty__campus")
        .filter(plan__code="2514")
        .order_by("-effective_from", "-created_at")
        .first()
    )
    if revision is None:
        print("service=academic_overview skipped=plan_2514_not_found")
        return
    term = (
        AcademicTerm.objects.filter(
            institution_id=revision.plan.program.faculty.campus.institution_id
        )
        .order_by("starts_at")
        .first()
    )
    if term is None:
        print("service=academic_overview skipped=term_not_found")
        return
    with transaction.atomic():
        user = get_user_model().objects.create_user(
            email=f"performance-{uuid4()}@example.test",
            password="benchmark-only",
        )
        student = StudentProfile.objects.create(
            user=user,
            institution_id=term.institution_id,
            student_number=f"PERF-{uuid4().hex[:12]}",
            display_name="Performance benchmark",
        )
        enrollment = ProgramEnrollment.objects.create(
            student=student,
            program=revision.plan.program,
            plan=revision.plan,
            revision_basis=revision,
            admission_term=term,
        )
        _measure_service(
            "academic_overview",
            lambda: build_academic_overview(user, enrollment_id=enrollment.pk),
            iterations,
        )
        transaction.set_rollback(True)


def _plan_nodes(plan: dict[str, Any]) -> list[str]:
    nodes = [
        ":".join(
            value
            for value in (
                str(plan.get("Node Type", "")),
                str(plan.get("Relation Name", "")),
                str(plan.get("Index Name", "")),
            )
            if value
        )
    ]
    for child in plan.get("Plans", []):
        if isinstance(child, dict):
            nodes.extend(_plan_nodes(child))
    return nodes


def _explain(label: str, queryset: Any) -> None:
    sql, params = queryset.query.sql_with_params()
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN (FORMAT JSON) " + sql, params)
        raw = cursor.fetchone()[0]
    plan = raw[0]["Plan"] if isinstance(raw, list) and raw else {}
    print(
        f"explain={label} startup_cost={plan.get('Startup Cost')} "
        f"total_cost={plan.get('Total Cost')} rows={plan.get('Plan Rows')} "
        f"nodes={' | '.join(_plan_nodes(plan))}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=15)
    parser.add_argument("--explain", action="store_true")
    args = parser.parse_args()
    if args.iterations < 3:
        parser.error("--iterations must be at least 3 for a useful p95")

    print(f"environment=python={sys.version.split()[0]} database={connection.vendor}")
    _benchmark_rules(args.iterations * 5)

    _measure_service("curriculum_map_public", lambda: build_curriculum_map(None), args.iterations)
    _measure_service(
        "dependency_graph_focus",
        lambda: build_dependency_graph(None, selected="2016360"),
        args.iterations,
    )
    _benchmark_ephemeral_overview(args.iterations)

    if args.explain:
        _explain(
            "revision_lookup",
            CurriculumRevision.objects.filter(plan__code="2514", status="PUBLISHED").order_by(
                "-effective_from", "-created_at", "-revision_code"
            )[:1],
        )
        enrollment = ProgramEnrollment.objects.order_by("created_at").first()
        if enrollment is not None:
            _explain(
                "latest_audit_run",
                DegreeAuditRun.objects.filter(enrollment_id=enrollment.pk)
                .select_related("result")
                .order_by("-generated_at", "-created_at")[:1],
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
