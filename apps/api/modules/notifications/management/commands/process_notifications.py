from __future__ import annotations

from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from modules.notifications.application.services import dispatch_pending_notifications


class Command(BaseCommand):
    help = "Materialize committed notification outbox rows and deliver configured channels."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        limit = int(options["limit"])
        if limit < 1 or limit > 500:
            raise CommandError("--limit must be between 1 and 500.")
        result = dispatch_pending_notifications(limit=limit)
        self.stdout.write(self.style.SUCCESS(str(result)))
