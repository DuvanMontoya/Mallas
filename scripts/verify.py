#!/usr/bin/env python3
"""Canonical verification orchestrator.

Works before source apps exist and expands automatically as the project is built.
Never delete checks merely because they fail.
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def run(label: str, cmd: list[str], cwd: Path | None = None, required: bool = True) -> bool:
    print(f"\n=== {label} ===")
    try:
        p = subprocess.run(cmd, cwd=cwd or ROOT, check=False)
    except FileNotFoundError:
        if required:
            print(f"ERROR: command not found: {cmd[0]}")
            return False
        print(f"SKIP: {cmd[0]} not installed yet")
        return True
    if p.returncode:
        print(f"FAIL [{p.returncode}]: {' '.join(cmd)}")
        return False
    return True

def main() -> int:
    ok = True
    ok &= run("curriculum invariants", [sys.executable, "scripts/validate_curriculum.py"])

    api = ROOT / "apps/api"
    web = ROOT / "apps/web"

    if (api / "pyproject.toml").exists():
        if shutil.which("uv"):
            ok &= run("backend tests", ["uv", "run", "pytest"], api)
            ok &= run("backend ruff", ["uv", "run", "ruff", "check", "."], api)
            ok &= run("backend format check", ["uv", "run", "ruff", "format", "--check", "."], api)
        else:
            print("ERROR: backend exists but uv is missing")
            ok = False

    if (web / "package.json").exists():
        if shutil.which("pnpm"):
            ok &= run("frontend lint", ["pnpm", "lint"], web)
            ok &= run("frontend typecheck", ["pnpm", "typecheck"], web)
            ok &= run("frontend unit tests", ["pnpm", "test", "--", "--run"], web)
        else:
            print("ERROR: frontend exists but pnpm is missing")
            ok = False

    print("\n=== RESULT ===")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
