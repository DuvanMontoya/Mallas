#!/usr/bin/env python3
"""Guard for release-critical TODOs.

During development TODOs may exist, but a final production-readiness prompt should
run this and classify/resolve every hit.
"""

import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
IGNORE_DIRS = {
    ".git",
    ".next",
    ".venv",
    ".pnpm-store",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".hypothesis",
    ".uv-cache",
    ".uv-python",
    "node_modules",
    "__pycache__",
    "prompts",
}
TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".sql",
    ".sh",
    ".ps1",
    ".html",
    ".xml",
    ".toml",
    ".ini",
}
SPECIAL_FILENAMES = {"Dockerfile", "Containerfile"}
PRODUCT_ROOTS = tuple(
    ROOT / relative
    for relative in (
        "apps/api",
        "apps/web",
        "packages/api-client/src",
    )
)
PRODUCT_EXCLUDED_PARTS = {"test", "tests", "__tests__", "migrations"}
patterns = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
hits: list[tuple[Path, int, str]] = []
errors: list[tuple[Path, str]] = []
files_scanned = 0

for directory, subdirectories, filenames in os.walk(ROOT, topdown=True):
    subdirectories[:] = [
        name
        for name in subdirectories
        if name not in IGNORE_DIRS
        and not name.startswith(".pnpm")
        and not name.startswith(".node_modules")
    ]
    for filename in filenames:
        p = Path(directory) / filename
        if p.suffix.lower() not in TEXT_SUFFIXES and p.name not in SPECIAL_FILENAMES and not p.name.startswith(".env"):
            continue
        files_scanned += 1
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if patterns.search(line):
                    hits.append((p.relative_to(ROOT), i, line.strip()))
        except (OSError, UnicodeDecodeError) as exc:
            errors.append((p.relative_to(ROOT), str(exc)))

if errors:
    for path, error in errors:
        print(f"ERROR: {path}: {error}")
    print(f"files_scanned={files_scanned}")
    print(f"read_errors={len(errors)}")
    raise SystemExit(1)

def is_product_file(relative: Path) -> bool:
    if any(part in PRODUCT_EXCLUDED_PARTS for part in relative.parts):
        return False
    return any(
        relative == product_root.relative_to(ROOT)
        or product_root.relative_to(ROOT) in relative.parents
        for product_root in PRODUCT_ROOTS
        if product_root.is_dir()
    )


functional_hits = [hit for hit in hits if is_product_file(hit[0])]
nonfunctional_hits = [hit for hit in hits if not is_product_file(hit[0])]
for h in nonfunctional_hits:
    print(f"NONFUNCTIONAL: {h[0]}:{h[1]}: {h[2]}")
for h in functional_hits:
    print(f"FUNCTIONAL: {h[0]}:{h[1]}: {h[2]}")
print(f"files_scanned={files_scanned}")
print(f"nonfunctional_hits={len(nonfunctional_hits)}")
print(f"functional_hits={len(functional_hits)}")
if functional_hits:
    raise SystemExit(1)
print("TODO_RELEASE_GATE=PASS")
