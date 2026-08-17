from __future__ import annotations

import csv
import json
import os
from argparse import ArgumentParser
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from domain.enums import EpistemicStatus
from modules.rules.models import Requirement

_QUEUE_STATUSES = (
    EpistemicStatus.INFERRED_PENDING_REVIEW.value,
    EpistemicStatus.UNKNOWN.value,
    EpistemicStatus.DISPUTED.value,
)


def _row(requirement: Requirement) -> dict[str, Any]:
    revision = requirement.revision
    evidence = list(requirement.evidence.all())
    evidence_rows = [
        {
            "id": str(item.pk),
            "snapshot_id": str(item.snapshot_id),
            "snapshot_sha256": item.snapshot.sha256,
            "locator": item.line_locator
            or item.section
            or (f"page:{item.page}" if item.page else "source"),
            "source_url": item.snapshot.source_url or item.snapshot.document.canonical_url or None,
        }
        for item in evidence
    ]
    return {
        "requirement_id": str(requirement.pk),
        "revision_id": str(requirement.revision_id) if requirement.revision_id else None,
        "revision_code": revision.revision_code if revision else None,
        "plan_code": revision.plan.code if revision else None,
        "owner_type": requirement.owner_type,
        "owner_id": str(requirement.owner_id),
        "code": requirement.code,
        "purpose": requirement.purpose,
        "epistemic_status": requirement.epistemic_status,
        "explanation_key": requirement.explanation_key,
        "evidence": evidence_rows,
        "evidence_count": len(evidence_rows),
        "review_action": "HUMAN_REVIEW_REQUIRED",
        "publish_blocker": requirement.epistemic_status != EpistemicStatus.VERIFIED.value,
    }


def build_queue() -> dict[str, Any]:
    requirements = (
        Requirement.objects.filter(epistemic_status__in=_QUEUE_STATUSES)
        .select_related("revision__plan")
        .prefetch_related("evidence__snapshot__document")
        .order_by("revision__plan__code", "code", "pk")
    )
    items = [_row(requirement) for requirement in requirements]
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "policy": "human_review_required_no_auto_publish",
        "items": items,
        "counts": {
            "total": len(items),
            "by_epistemic_status": dict(Counter(item["epistemic_status"] for item in items)),
            "with_evidence": sum(1 for item in items if item["evidence_count"]),
            "without_evidence": sum(1 for item in items if not item["evidence_count"]),
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.partial")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_csv(path: Path, items: list[dict[str, Any]]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.partial")
    fields = (
        "requirement_id",
        "revision_code",
        "plan_code",
        "owner_type",
        "owner_id",
        "code",
        "purpose",
        "epistemic_status",
        "evidence_count",
        "review_action",
        "publish_blocker",
    )
    try:
        with temporary.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for item in items:
                writer.writerow({field: item[field] for field in fields})
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


class Command(BaseCommand):
    help = "Export UNKNOWN, inferred-pending-review and disputed rules without publishing them."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--output", type=Path)
        parser.add_argument("--format", choices=("json", "csv"), default="json")

    def handle(self, *args: object, **options: object) -> str | None:
        del args
        output = options.get("output")
        if output is not None and not isinstance(output, Path):
            raise CommandError("--output must be a filesystem path")
        queue = build_queue()
        if output is not None:
            if options.get("format") == "csv":
                _write_csv(output, queue["items"])
            else:
                _write_json(output, queue)
        else:
            self.stdout.write(json.dumps(queue, ensure_ascii=False, sort_keys=True))
        return None
