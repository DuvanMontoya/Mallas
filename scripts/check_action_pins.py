#!/usr/bin/env python3
"""Require immutable commit pins for every third-party GitHub Action."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def check() -> list[str]:
    errors: list[str] = []
    if not WORKFLOW_ROOT.is_dir():
        return ["missing .github/workflows"]
    for path in sorted(WORKFLOW_ROOT.glob("*.y*ml")):
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            match = USES_RE.match(line)
            if not match:
                continue
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            if "@" not in reference:
                errors.append(f"{path.relative_to(ROOT)}:{line_number}: missing action ref")
                continue
            action, commit = reference.rsplit("@", 1)
            if not action or not COMMIT_RE.fullmatch(commit):
                errors.append(
                    f"{path.relative_to(ROOT)}:{line_number}: {reference!r} is not a 40-character commit pin"
                )
    return errors


def main() -> int:
    errors = check()
    if errors:
        print("GitHub Action pinning failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("GitHub Action pinning passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
