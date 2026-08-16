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
            ok &= run(
                "OpenAPI freshness",
                ["uv", "run", "--frozen", "python", "..\\..\\scripts\\check_openapi.py"],
                api,
            )
            ok &= run(
                "OpenAPI breaking-diff self-check",
                [
                    sys.executable,
                    "scripts/check_openapi_breaking.py",
                    "--base",
                    "artifacts/openapi.json",
                    "--current",
                    "artifacts/openapi.json",
                ],
            )
            ok &= run("backend Django checks", ["uv", "run", "--frozen", "python", "manage.py", "check"], api)
            ok &= run(
                "backend migration graph",
                [
                    "uv",
                    "run",
                    "--frozen",
                    "python",
                    "manage.py",
                    "makemigrations",
                    "--check",
                    "--dry-run",
                ],
                api,
            )
            ok &= run(
                "backend migration state",
                ["uv", "run", "--frozen", "python", "manage.py", "migrate", "--check"],
                api,
            )
            ok &= run("backend tests", ["uv", "run", "--frozen", "pytest"], api)
            ok &= run("backend ruff", ["uv", "run", "--frozen", "ruff", "check", "."], api)
            ok &= run("backend format check", ["uv", "run", "--frozen", "ruff", "format", "--check", "."], api)
            ok &= run("backend typecheck", ["uv", "run", "--frozen", "mypy", "config", "modules", "tests"], api)
        else:
            print("ERROR: backend exists but uv is missing")
            ok = False

    if (web / "package.json").exists():
        pnpm = shutil.which("pnpm") or shutil.which("pnpm.cmd")
        if pnpm:
            ok &= run(
                "generated API client freshness",
                [pnpm, "--dir", "packages/api-client", "verify"],
            )
            ok &= run("frontend lint", [pnpm, "lint"], web)
            ok &= run("frontend typecheck", [pnpm, "typecheck"], web)
            ok &= run("frontend unit tests", [pnpm, "test", "--", "--run"], web)
        else:
            print("ERROR: frontend exists but pnpm is missing")
            ok = False

    print("\n=== RESULT ===")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
