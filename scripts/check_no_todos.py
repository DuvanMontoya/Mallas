#!/usr/bin/env python3
"""Guard for release-critical TODOs.

During development TODOs may exist, but a final production-readiness prompt should
run this and classify/resolve every hit.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
IGNORE = {".git", "node_modules", ".next", ".venv", "prompts"}
patterns = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
hits = []
for p in ROOT.rglob("*"):
    if not p.is_file() or any(part in IGNORE for part in p.parts):
        continue
    if p.suffix.lower() not in {".py",".ts",".tsx",".js",".jsx",".md",".json",".yaml",".yml"}:
        continue
    try:
        for i,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
            if patterns.search(line):
                hits.append((p.relative_to(ROOT),i,line.strip()))
    except UnicodeDecodeError:
        pass
for h in hits:
    print(f"{h[0]}:{h[1]}: {h[2]}")
print(f"hits={len(hits)}")
