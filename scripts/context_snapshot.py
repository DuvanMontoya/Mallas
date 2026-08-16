#!/usr/bin/env python3
"""Print a compact recovery packet for a new agent session."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "docs/state/CURRENT_STATE.md",
    "docs/state/OPEN_DECISIONS.md",
    "docs/state/RISKS.md",
]

def git(*args):
    p = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    return p.stdout.strip()

print("# CONTEXT SNAPSHOT")
print("\n## Git")
print(git("status", "--short"))
print("\nRecent commits:")
print(git("log", "--oneline", "-15"))
for rel in FILES:
    p = ROOT / rel
    print(f"\n## {rel}")
    print(p.read_text(encoding="utf-8") if p.exists() else "(missing)")
