#!/usr/bin/env python3
"""Check that documentation works from a clean repository checkout.

The check is intentionally filesystem-only: it does not import the application
or depend on a developer's virtualenv. It catches relative links to files that
would be absent after cloning, machine-specific absolute paths, and missing
operator-facing entry points.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
_MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
_ABSOLUTE_WINDOWS = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z]:[\\/](?![\\/])|\\\\[A-Za-z0-9_.-]+[\\/]"
)


def _markdown_files() -> list[Path]:
    files: list[Path] = []
    for directory in (ROOT / "docs", ROOT / "infra", ROOT / ".codex"):
        if directory.is_dir():
            files.extend(path for path in directory.rglob("*.md") if path.is_file())
    return files


def _resolve_link(source: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().split()[0].strip("<>")
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or target.startswith("#"):
        return None
    path_text = unquote(parsed.path)
    if not path_text or path_text.startswith("/"):
        return None
    return (source.parent / path_text).resolve()


def verify() -> list[str]:
    errors: list[str] = []
    required = (
        "AGENTS.md",
        "docs/00_PRODUCT_SCOPE.md",
        "docs/19_TEST_STRATEGY.md",
        "docs/41_ACCEPTANCE_GATES_MATRIX.md",
        "docs/ops/DEPLOYMENT_RUNBOOK.md",
        "docs/ops/BACKUP_RESTORE_RUNBOOK.md",
        "docs/ops/ROLLBACK_RUNBOOK.md",
        "infra/docker-compose.yml",
        "infra/docker-compose.production.yml",
    )
    errors.extend(
        f"missing required checkout file: {relative}"
        for relative in required
        if not (ROOT / relative).is_file()
    )

    for source in _markdown_files():
        relative = source.relative_to(ROOT).as_posix()
        text = source.read_text(encoding="utf-8")
        if _ABSOLUTE_WINDOWS.search(text):
            errors.append(f"{relative} contains a machine-specific absolute Windows path")
        for raw_target in _MARKDOWN_LINK.findall(text):
            resolved = _resolve_link(source, raw_target)
            if resolved is None:
                continue
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(f"{relative} links outside the repository: {raw_target}")
                continue
            if not resolved.exists():
                errors.append(
                    f"{relative} links to a missing checkout file: "
                    f"{resolved.relative_to(ROOT).as_posix()}"
                )
    return errors


def main() -> int:
    errors = verify()
    if errors:
        print("Documentation clone-clean verification failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Documentation clone-clean verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
