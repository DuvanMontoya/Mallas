from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from modules.imports.application.baseline import BaselineValidationError
from modules.imports.application.services import diff_curriculum_files


class Command(BaseCommand):
    help = "Show a deterministic semantic diff between two curriculum baselines."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("candidate", nargs="?", default=None)
        parser.add_argument("--base", dest="base_path", default=None)

    def handle(self, *args: object, **options: object) -> str | None:
        del args
        candidate = options.get("candidate")
        base = options.get("base_path")
        try:
            diff = diff_curriculum_files(
                candidate if isinstance(candidate, (str, Path)) else None,
                base if isinstance(base, (str, Path)) else None,
            )
        except (BaselineValidationError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(diff, ensure_ascii=False, indent=2, sort_keys=True))
        return None
