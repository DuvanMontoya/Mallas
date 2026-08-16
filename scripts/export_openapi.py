#!/usr/bin/env python3
"""Export the canonical Django Ninja schema for the generated client."""

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


TARGET = ROOT / "artifacts" / "openapi.json"
TARGET.parent.mkdir(parents=True, exist_ok=True)
TARGET.write_text(json.dumps(api.get_openapi_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {TARGET}")
