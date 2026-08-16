#!/usr/bin/env python3
"""Small reproducible benchmark for the pure rule evaluator."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from domain.rules import AuditContext, RevisionFacts, evaluate_rule, parse_rule  # noqa: E402

BASELINE = ROOT / "data" / "curricula" / "unal" / "bogota" / "estadistica" / "2514" / "plan_2514_acuerdo_496_2023.json"


def main() -> None:
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    rules = [parse_rule(row["ast"]) for row in data["enrollment_requirements"]]
    context = AuditContext(
        revision=RevisionFacts(total_credits=141),
        earned_credits=113,
        passed_courses=frozenset(),
    )
    iterations = 100
    start = time.perf_counter()
    for _ in range(iterations):
        for rule in rules:
            evaluate_rule(rule, context)
    elapsed = time.perf_counter() - start
    evaluations = iterations * len(rules)
    print(f"evaluations={evaluations} elapsed_seconds={elapsed:.6f} per_evaluation_us={elapsed / evaluations * 1_000_000:.2f}")


if __name__ == "__main__":
    main()
