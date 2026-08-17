"""High-confidence secret scan for the repository and CI.

This is intentionally conservative: it reports credential material that must
never be committed and ignores documented test/development placeholders. It
does not claim to replace a managed secret scanner in the hosting platform.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

_TEXT_SUFFIXES = {
    ".cfg",
    ".conf",
    ".css",
    ".env",
    ".example",
    ".ini",
    ".json",
    ".js",
    ".md",
    ".py",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yml",
    ".yaml",
}
_IGNORED_PARTS = {
    ".git",
    ".codex",
    ".cache",
    ".next",
    ".venv",
    "node_modules",
    ".pnpm",
    ".pnpm-store",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    (
        "credential-assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|secret[_-]?key)"
            r"\s*[:=]\s*[\"'](?P<value>[^\"']{16,})[\"']"
        ),
    ),
    (
        "database-credential-url",
        re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|redis)://[^\s:@]+:[^\s@]+@"),
    ),
)
_PLACEHOLDER_MARKERS = (
    "example",
    "changeme",
    "change-me",
    "dummy",
    "fake",
    "insecure-development",
    "local_only",
    "local-only",
    "curriculum_local_only",
    "curriculum_ci_only",
    "migrator_password",
    "not-a-secret",
    "placeholder",
    "safe-password",
    ".test",
    "runtime_password",
)


def _is_ignored(path: Path, root: Path) -> bool:
    return bool(_IGNORED_PARTS.intersection(path.relative_to(root).parts))


def _is_placeholder(value: str, path: Path) -> bool:
    lowered = value.lower()
    path_parts = {part.lower() for part in path.parts}
    return (
        any(marker in lowered for marker in _PLACEHOLDER_MARKERS)
        or path.name.lower().endswith((".example", ".example.local"))
        or bool(path_parts.intersection({"test", "tests", "fixtures"}))
        or lowered.startswith((":", "$"))
    )


def _files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, directories, filenames in os.walk(root):
        directories[:] = [directory for directory in directories if directory not in _IGNORED_PARTS]
        current_path = Path(current)
        for filename in filenames:
            path = current_path / filename
            if path.suffix.lower() not in _TEXT_SUFFIXES or _is_ignored(path, root):
                continue
            try:
                if path.stat().st_size <= 2 * 1024 * 1024:
                    files.append(path)
            except OSError:
                continue
    return sorted(files)


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for path in _files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(root).as_posix()
        for line_number, line in enumerate(text.splitlines(), start=1):
            for name, pattern in _PATTERNS:
                match = pattern.search(line)
                if match is None:
                    continue
                value = match.groupdict().get("value", match.group(0))
                if _is_placeholder(value, path):
                    continue
                findings.append(f"{relative}:{line_number}:{name}")
    return sorted(set(findings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    findings = scan(args.root.resolve())
    if findings:
        print("Potential committed secrets detected:")
        print("\n".join(findings))
        return 1
    print("Secret scan passed: no high-confidence committed secrets detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
