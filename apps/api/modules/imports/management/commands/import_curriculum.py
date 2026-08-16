from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from modules.imports.application.services import (
    CurriculumImportError,
    import_curriculum_baseline,
)


class Command(BaseCommand):
    help = "Import a curriculum baseline as an auditable DRAFT revision."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("path", nargs="?", default=None)
        parser.add_argument("--report", dest="report_path", default=None)
        parser.add_argument("--json", action="store_true", dest="as_json")

    def handle(self, *args: object, **options: object) -> str | None:
        del args
        path = options.get("path")
        report_path = options.get("report_path")
        as_json = bool(options.get("as_json"))
        try:
            result = import_curriculum_baseline(
                path if isinstance(path, (str, Path)) else None,
                report_path=report_path if isinstance(report_path, (str, Path)) else None,
            )
        except (CurriculumImportError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        payload = {
            "batch_id": result.batch_id,
            "revision_id": result.revision_id,
            "proposal_id": result.proposal_id,
            "fingerprint": result.fingerprint,
            "source_sha256": result.source_sha256,
            "report_path": result.report_path,
            "counts": result.counts,
            "validation": result.validation,
        }
        if as_json:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            self.stdout.write(self.style.SUCCESS("Curriculum baseline imported as DRAFT."))
            self.stdout.write(f"Revision: {result.revision_id}")
            self.stdout.write(f"Proposal: {result.proposal_id}")
            self.stdout.write(f"Fingerprint: {result.fingerprint}")
            self.stdout.write(f"Report: {result.report_path}")
            self.stdout.write(json.dumps(result.counts, ensure_ascii=False, sort_keys=True))
        return None
