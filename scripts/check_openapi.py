#!/usr/bin/env python3
"""Fail when the checked-in OpenAPI artifact differs from the backend contract."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from config.api import api


artifact = ROOT / "artifacts" / "openapi.json"
if not artifact.exists():
    raise SystemExit(f"OpenAPI artifact missing: {artifact}")
expected = api.get_openapi_schema()
actual = json.loads(artifact.read_text(encoding="utf-8"))
# JSON serialization normalizes integer response-code keys to strings.
expected_json = json.loads(json.dumps(expected, ensure_ascii=False))
if actual != expected_json:
    raise SystemExit("OpenAPI artifact is stale; run scripts/export_openapi.py and regenerate the client.")
print("OK: OpenAPI artifact matches the backend contract")
