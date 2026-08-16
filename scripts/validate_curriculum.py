#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data/curricula/unal/bogota/estadistica/2514/plan_2514_acuerdo_496_2023.json"

def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)

def walk_rule(rule):
    yield rule
    for child in rule.get("children", []):
        yield from walk_rule(child)

def main() -> None:
    data = json.loads(PLAN.read_text(encoding="utf-8"))
    components = {x["id"]: x for x in data["components"]}
    groups = {x["id"]: x for x in data["groups"]}
    courses = {x["code"]: x for x in data["courses"]}

    total = sum(x["required_credits"] for x in components.values())
    if total != data["identity"]["total_required_credits"]:
        fail(f"component total {total} != plan total")

    for component_id, component in components.items():
        group_total = sum(g["required_credits"] for g in groups.values() if g["component"] == component_id)
        if group_total != component["required_credits"]:
            fail(f"group total for {component_id}: {group_total} != {component['required_credits']}")

    for m in data["memberships"]:
        if m["course_code"] not in courses:
            fail(f"membership references missing course {m['course_code']}")
        if m["group"] not in groups:
            fail(f"membership references missing group {m['group']}")

    for r in data["enrollment_requirements"]:
        owner = r["owner_course_code"]
        if owner not in courses:
            fail(f"requirement owner missing {owner}")
        for node in walk_rule(r["ast"]):
            code = node.get("course_code")
            if code and code not in courses:
                fail(f"rule references missing course {code}")
            group = node.get("group")
            if group and group not in groups:
                fail(f"rule references missing group {group}")
            comp = node.get("component")
            if comp and comp not in components:
                fail(f"rule references missing component {comp}")

    # Plan-specific invariant: 80% of 141 -> first integer 113.
    plan_total = data["identity"]["total_required_credits"]
    first = next(c for c in range(plan_total + 1) if 5*c >= 4*plan_total)
    if first != 113:
        fail(f"80% threshold expected 113, got {first}")

    source = data["source_documents"][0]
    source_path = ROOT / source["local_path"]
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if digest != source["sha256"]:
        fail("source PDF SHA-256 mismatch")

    statuses = {a["status"] for a in data["known_ambiguities"]}
    if "UNKNOWN" not in statuses:
        fail("baseline must preserve known unknowns")

    print("OK: curriculum baseline invariants validated")
    print(f"courses={len(courses)} memberships={len(data['memberships'])} requirements={len(data['enrollment_requirements'])}")

if __name__ == "__main__":
    main()
