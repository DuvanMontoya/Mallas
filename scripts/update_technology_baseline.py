#!/usr/bin/env python3
"""Extract pinned tool/dependency versions for a reviewed tech-baseline update.

This command is deliberately offline. Resolving a new version still requires
the official release-note and compatibility review described in
``docs/32_TECH_UPDATE_POLICY.md``; the command makes the repository pins
visible and detects drift before a release.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.11+ is required by the project
    tomllib = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]


def _package_versions() -> dict[str, str]:
    if tomllib is None:
        raise RuntimeError("Python 3.11+ with tomllib is required")
    payload = tomllib.loads((ROOT / "apps/api/pyproject.toml").read_text(encoding="utf-8"))
    versions: dict[str, str] = {}
    for dependency in [*payload["project"]["dependencies"], *payload["dependency-groups"]["dev"]]:
        name, separator, version = str(dependency).partition("==")
        if separator:
            versions[name.split("[", 1)[0].lower()] = version
    return versions


def collect() -> dict[str, object]:
    if tomllib is None:
        raise RuntimeError("Python 3.11+ with tomllib is required")
    pyproject = tomllib.loads((ROOT / "apps/api/pyproject.toml").read_text(encoding="utf-8"))
    root_package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    web_package = json.loads((ROOT / "apps/web/package.json").read_text(encoding="utf-8"))
    versions = _package_versions()
    python_requires = str(pyproject["project"]["requires-python"])
    return {
        "python": python_requires.removeprefix(">=").split(",", 1)[0],
        "python_requires": python_requires,
        "node": (ROOT / ".nvmrc").read_text(encoding="utf-8").strip(),
        "pnpm": str(root_package.get("packageManager", "")).removeprefix("pnpm@"),
        "django": versions.get("django", ""),
        "django_ninja": versions.get("django-ninja", ""),
        "pydantic": versions.get("pydantic", ""),
        "psycopg": versions.get("psycopg[binary]", versions.get("psycopg", "")),
        "hypothesis": versions.get("hypothesis", ""),
        "ortools": versions.get("ortools", ""),
        "ruff": versions.get("ruff", ""),
        "mypy": versions.get("mypy", ""),
        "next": str(web_package["dependencies"]["next"]),
        "react": str(web_package["dependencies"]["react"]),
        "react_dom": str(web_package["dependencies"]["react-dom"]),
        "typescript": str(web_package["devDependencies"]["typescript"]),
        "lockfiles": ["apps/api/uv.lock", "pnpm-lock.yaml"],
    }


def _render(payload: dict[str, object]) -> str:
    lines = [
        "# Resolved technology baseline (generated)",
        "",
        "> Generated from repository manifests. Review official release notes, advisories and compatibility before applying an upgrade.",
        "",
        "| Component | Resolved pin | Source |",
        "| --- | --- | --- |",
    ]
    source = {
        "python": "apps/api/pyproject.toml",
        "node": ".nvmrc",
        "pnpm": "package.json",
        "django": "apps/api/pyproject.toml + uv.lock",
        "django_ninja": "apps/api/pyproject.toml + uv.lock",
        "pydantic": "apps/api/pyproject.toml + uv.lock",
        "psycopg": "apps/api/pyproject.toml + uv.lock",
        "hypothesis": "apps/api/pyproject.toml + uv.lock",
        "ortools": "apps/api/pyproject.toml + uv.lock",
        "ruff": "apps/api/pyproject.toml + uv.lock",
        "mypy": "apps/api/pyproject.toml + uv.lock",
        "next": "apps/web/package.json + pnpm-lock.yaml",
        "react": "apps/web/package.json + pnpm-lock.yaml",
        "react_dom": "apps/web/package.json + pnpm-lock.yaml",
        "typescript": "apps/web/package.json + pnpm-lock.yaml",
    }
    for key, value in payload.items():
        if key in source:
            lines.append(f"| `{key}` | `{value}` | `{source[key]}` |")
    lines.extend(
        [
            "",
            "Lockfiles required: " + ", ".join(f"`{item}`" for item in payload["lockfiles"]),
            "",
        ]
    )
    return "\n".join(lines)


def _check_baseline(payload: dict[str, object]) -> list[str]:
    baseline_path = ROOT / "docs/research/TECHNOLOGY_BASELINE.md"
    text = baseline_path.read_text(encoding="utf-8")
    checks = {
        "Django": payload["django"],
        "Django Ninja": payload["django_ninja"],
        "Next.js": payload["next"],
        "React": payload["react"],
        "pypdf": "6.16.1",
        "pnpm": payload["pnpm"],
        "Node.js": payload["node"],
    }
    errors = [
        f"technology baseline does not mention current {name} pin {value}"
        for name, value in checks.items()
        if str(value) not in text
    ]
    if re.search(r"(^|[^A-Za-z])latest([^A-Za-z]|$)", text, flags=re.IGNORECASE):
        # The policy phrase is allowed; a dependency manifest must still be exact.
        for manifest in (ROOT / "package.json", ROOT / "apps/web/package.json"):
            if '"latest"' in manifest.read_text(encoding="utf-8"):
                errors.append(f"mutable latest dependency found in {manifest.relative_to(ROOT)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check the reviewed baseline contains current pins")
    parser.add_argument("--output", type=Path, help="write a generated Markdown snapshot")
    args = parser.parse_args()
    try:
        payload = collect()
        if args.check:
            errors = _check_baseline(payload)
            if errors:
                print("Technology baseline check failed:\n- " + "\n- ".join(errors), file=sys.stderr)
                return 1
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(_render(payload), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    except (OSError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL technology baseline: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
