from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from modules.imports.application.baseline import BaselineValidationError
from modules.imports.application.services import validate_curriculum_file


class Command(BaseCommand):
    help = "Validate a curriculum baseline without writing database state."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("path", nargs="?", default=None)
        parser.add_argument("--json", action="store_true", dest="as_json")

    def handle(self, *args: object, **options: object) -> str | None:
        del args
        path = options.get("path")
        try:
            document, report = validate_curriculum_file(
                path if isinstance(path, (str, Path)) else None
            )
        except (BaselineValidationError, ValueError) as exc:
            if isinstance(exc, BaselineValidationError):
                report = exc.report.as_dict()
                self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))
            raise CommandError(str(exc)) from exc
        if options.get("as_json"):
            self.stdout.write(
                json.dumps(
                    {"fingerprint": document.fingerprint, **report},
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Curriculum baseline is valid."))
            self.stdout.write(f"Schema: {document.schema_version}")
            self.stdout.write(f"Fingerprint: {document.fingerprint}")
            self.stdout.write(json.dumps(report["counts"], ensure_ascii=False, sort_keys=True))
        return None
