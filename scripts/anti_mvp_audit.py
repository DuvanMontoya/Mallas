#!/usr/bin/env python3
"""Static anti-MVP gate for production product code.

The gate is intentionally conservative about implementation shortcuts while
allowing the explicit no-op exception paths used by telemetry adapters. Test
fixtures and documentation are audited separately by their own checks.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_ROOTS = (
    ROOT / "apps/api/domain",
    ROOT / "apps/api/modules",
    ROOT / "apps/web/app",
    ROOT / "apps/web/components",
    ROOT / "apps/web/features",
    ROOT / "apps/web/lib",
    ROOT / "packages/api-client/src",
)
REQUIRED_CONTEXTS = {
    "identity": ROOT / "apps/api/modules/identity",
    "institutions": ROOT / "apps/api/modules/institutions",
    "curriculum": ROOT / "apps/api/modules/curriculum",
    "rules": ROOT / "apps/api/domain/rules",
    "audit": ROOT / "apps/api/modules/audit",
    "student_records": ROOT / "apps/api/modules/student_records",
    "offerings": ROOT / "apps/api/modules/offerings",
    "planning": ROOT / "apps/api/modules/planning",
    "optimization": ROOT / "apps/api/modules/optimization",
    "governance": ROOT / "apps/api/modules/governance",
    "imports": ROOT / "apps/api/modules/imports",
    "notifications": ROOT / "apps/api/modules/notifications",
    "analytics": ROOT / "apps/api/modules/analytics",
    "observability": ROOT / "apps/api/modules/observability",
}
TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".css",
    ".json",
    ".yaml",
    ".yml",
    ".sql",
    ".sh",
    ".ps1",
    ".html",
    ".xml",
    ".toml",
}
MARKERS = re.compile(r"\b(?:TODO|FIXME|HACK|XXX|NotImplementedError)\b")
COURSE_LITERAL = re.compile(r"(?:course\.code|course_code)\s*==\s*['\"][A-Za-z0-9_-]+['\"]")
MOCK_MARKER = re.compile(
    r"\b(?:vi\.mock|vi\.spyOn|jest\.mock|jest\.spyOn|unittest\.mock|mock\.patch|"
    r"MagicMock\(|Mock\()"
)
PASS_LINE = re.compile(r"^\s*pass\s*(?:#.*)?$")
ALLOWED_PASS = {
    Path("apps/api/modules/observability/tracing.py"),
    Path("apps/api/modules/observability/metrics.py"),
}


def iter_product_files() -> list[Path]:
    files: list[Path] = []
    for root in PRODUCT_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or (
                path.suffix.lower() not in TEXT_SUFFIXES and path.name != "Dockerfile"
            ):
                continue
            if any(part in {"node_modules", ".next", "__pycache__", "migrations"} for part in path.parts):
                continue
            if any(part in {"test", "tests", "__tests__"} for part in path.parts):
                continue
            files.append(path)
    return sorted(set(files))


def main() -> int:
    issues: list[str] = []
    missing = [name for name, path in REQUIRED_CONTEXTS.items() if not path.is_dir()]
    issues.extend(f"missing bounded context: {name}" for name in missing)

    files = iter_product_files()
    for path in files:
        relative = path.relative_to(ROOT)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            issues.append(f"non-UTF-8 product source: {relative}")
            continue
        content = "\n".join(lines)
        if MARKERS.search(content):
            issues.append(f"placeholder marker in product source: {relative}")
        if COURSE_LITERAL.search(content):
            issues.append(f"course-specific literal comparison in product source: {relative}")
        if MOCK_MARKER.search(content):
            issues.append(f"test mock marker in product source: {relative}")
        if relative not in ALLOWED_PASS:
            for line_number, line in enumerate(lines, 1):
                if PASS_LINE.fullmatch(line):
                    issues.append(f"bare pass in product source: {relative}:{line_number}")

    print(f"product_files_scanned={len(files)}")
    print(f"bounded_contexts={len(REQUIRED_CONTEXTS)}")
    if issues:
        for issue in issues:
            print(f"FAIL: {issue}")
        print(f"anti_mvp_issues={len(issues)}")
        return 1
    print("anti_mvp_issues=0")
    print("ANTI_MVP_STATIC_GATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
