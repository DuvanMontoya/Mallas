from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.imports.application.retention import purge_expired_candidate_payloads


class Command(BaseCommand):
    help = "Purge minimized history candidate rows after the configured retention window."

    def handle(self, *args: object, **options: object) -> None:
        del args, options
        purged = purge_expired_candidate_payloads()
        self.stdout.write(self.style.SUCCESS(f"Purged {purged} expired candidate payload(s)."))
