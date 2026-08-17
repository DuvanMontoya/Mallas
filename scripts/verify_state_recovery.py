#!/usr/bin/env python3
"""Verify that a new agent can recover project state without conversation memory."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def verify() -> dict[str, object]:
    errors: list[str] = []
    required = (
        "AGENTS.md",
        ".codex/STATUS.md",
        "docs/state/CURRENT_STATE.md",
        "docs/state/ROADMAP_STATUS.json",
        "docs/state/OPEN_DECISIONS.md",
        "docs/state/SESSION_LOG.md",
    )
    for relative in required:
        if not (ROOT / relative).is_file():
            errors.append(f"missing state file: {relative}")

    roadmap: dict[str, object] = {}
    roadmap_path = ROOT / "docs/state/ROADMAP_STATUS.json"
    if roadmap_path.is_file():
        try:
            parsed = json.loads(roadmap_path.read_text(encoding="utf-8"))
            if not isinstance(parsed, dict):
                errors.append("roadmap root must be an object")
            else:
                roadmap = parsed
                phases = parsed.get("phases")
                if not isinstance(phases, list) or not phases:
                    errors.append("roadmap must contain a non-empty phases list")
                else:
                    phase_ids: set[str] = set()
                    for phase in phases:
                        if not isinstance(phase, dict):
                            errors.append("roadmap contains a non-object phase")
                            continue
                        phase_id = str(phase.get("id", ""))
                        if not phase_id or phase_id in phase_ids:
                            errors.append(f"roadmap phase id is missing or duplicated: {phase_id}")
                        phase_ids.add(phase_id)
                        prompt = phase.get("prompt")
                        if isinstance(prompt, str) and not (ROOT / prompt).is_file():
                            errors.append(f"roadmap prompt is missing: {prompt}")
                        if phase.get("status") not in {"pending", "in_progress", "done", "blocked"}:
                            errors.append(f"roadmap phase has invalid status: {phase_id}")
                        if phase.get("status") == "done" and not phase.get("verification"):
                            errors.append(f"completed phase lacks verification: {phase_id}")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"roadmap cannot be read as JSON: {type(exc).__name__}")

    current_state = (ROOT / "docs/state/CURRENT_STATE.md").read_text(encoding="utf-8", errors="replace") if (ROOT / "docs/state/CURRENT_STATE.md").is_file() else ""
    if current_state and not (
        ("Problemas pendientes" in current_state or "No quedó terminado" in current_state)
        and "Siguiente" in current_state
        and "Comandos" in current_state
    ):
        errors.append("CURRENT_STATE must expose pending problems, next action and commands")
    status = (ROOT / ".codex/STATUS.md").read_text(encoding="utf-8", errors="replace") if (ROOT / ".codex/STATUS.md").is_file() else ""
    if status and "P24" not in status:
        errors.append(".codex/STATUS.md does not contain the current deployment milestone")

    phases = roadmap.get("phases", []) if isinstance(roadmap, dict) else []
    status_counts: dict[str, int] = {}
    if isinstance(phases, list):
        for phase in phases:
            if isinstance(phase, dict):
                state = str(phase.get("status", ""))
                status_counts[state] = status_counts.get(state, 0) + 1
    return {
        "schema_version": "1.0",
        "checked_at": datetime.now(UTC).isoformat(),
        "status": "ok" if not errors else "error",
        "errors": errors,
        "phase_counts": status_counts,
        "recovery_inputs": list(required),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
