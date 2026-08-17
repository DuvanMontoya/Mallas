from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from modules.institutions.models import Campus, Institution
from modules.offerings.application.importer import (
    OFFICIAL_SIA_COURSE_SEARCH_URL,
    SourceDescriptor,
    StaticJsonOfferingAdapter,
    import_offering_payload,
)


class Command(BaseCommand):
    help = "Import an explicitly archived, normalized offerings JSON payload."

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument("json_path", type=Path)
        parser.add_argument("--institution-slug", required=True)
        parser.add_argument("--campus-code")
        parser.add_argument("--source-key", required=True)
        parser.add_argument("--source-name", required=True)
        parser.add_argument("--source-url", default=OFFICIAL_SIA_COURSE_SEARCH_URL)
        parser.add_argument("--captured-at")

    def handle(self, *args, **options) -> None:  # type: ignore[no-untyped-def]
        path: Path = options["json_path"]
        try:
            institution = Institution.objects.get(slug=options["institution_slug"])
        except Institution.DoesNotExist as exc:
            raise CommandError("Institution not found.") from exc
        campus = None
        if options.get("campus_code"):
            campus = Campus.objects.filter(
                institution=institution, code=options["campus_code"]
            ).first()
            if campus is None:
                raise CommandError("Campus not found for institution.")
        descriptor = SourceDescriptor(
            key=options["source_key"],
            name=options["source_name"],
            url=options["source_url"],
        )
        adapter = StaticJsonOfferingAdapter.from_file(path, descriptor=descriptor)
        captured_at = None
        if options.get("captured_at"):
            try:
                captured_at = datetime.fromisoformat(options["captured_at"].replace("Z", "+00:00"))
            except ValueError as exc:
                raise CommandError("--captured-at must be ISO-8601.") from exc
            if captured_at.tzinfo is None:
                captured_at = captured_at.replace(tzinfo=UTC)
        payload = adapter.fetch(str(adapter.payload.get("term", {}).get("code", "")))
        try:
            result = import_offering_payload(
                payload,
                institution=institution,
                campus=campus,
                descriptor=descriptor,
                captured_at=captured_at,
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result.__dict__, default=str, ensure_ascii=False, indent=2))
