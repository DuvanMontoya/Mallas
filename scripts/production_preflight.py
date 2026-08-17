#!/usr/bin/env python3
"""Fail-closed preflight for the production Compose environment.

Compose cannot validate a variable's value with a regular expression. This
command does that validation before pull/migrate/up and never prints secret
values. The injected env file remains outside Git and is read only for the
duration of the check.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


IMMUTABLE_IMAGE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
REQUIRED = (
    "API_IMAGE",
    "WEB_IMAGE",
    "RUNTIME_DATABASE_URL",
    "MIGRATION_DATABASE_URL",
    "DJANGO_SECRET_KEY",
    "PRIVILEGED_MFA_REQUIRED",
)


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"invalid env line {line_number}")
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError(f"invalid env key at line {line_number}")
        values[key] = value.strip().strip("'\"")
    return values


def validate(values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED:
        if not values.get(key):
            errors.append(f"{key} is required")
    for key in ("API_IMAGE", "WEB_IMAGE"):
        value = values.get(key, "")
        if value and not IMMUTABLE_IMAGE.fullmatch(value):
            errors.append(f"{key} must be a registry reference ending in @sha256:<64 hex>")
    if values.get("DJANGO_SECRET_KEY", "").startswith("REPLACE_WITH") or len(
        values.get("DJANGO_SECRET_KEY", "")
    ) < 50:
        errors.append("DJANGO_SECRET_KEY must be a non-placeholder value of at least 50 characters")
    if values.get("PRIVILEGED_MFA_REQUIRED", "").lower() not in {"1", "true", "yes"}:
        errors.append("PRIVILEGED_MFA_REQUIRED must be true in production")
    if values.get("RUNTIME_DATABASE_URL") == values.get("MIGRATION_DATABASE_URL"):
        errors.append("RUNTIME_DATABASE_URL and MIGRATION_DATABASE_URL must use separate roles")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        values = _read_env_file(args.env_file)
    except (OSError, ValueError) as exc:
        print(f"FAIL production preflight: {exc}", file=sys.stderr)
        return 1
    values.update({key: value for key, value in os.environ.items() if key in REQUIRED})
    errors = validate(values)
    if errors:
        print("Production preflight failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Production preflight passed: immutable images, split database roles and privileged MFA gate verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
