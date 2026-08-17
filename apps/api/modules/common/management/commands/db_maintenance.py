from __future__ import annotations

import json
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


def _pending_migrations() -> list[str]:
    executor = MigrationExecutor(connection)
    return [
        f"{migration.app_label}.{migration.name}"
        for migration, _ in executor.migration_plan(executor.loader.graph.leaf_nodes())
    ]


def _analyze() -> str:
    if connection.vendor == "postgresql":
        previous = connection.get_autocommit()
        if not previous:
            connection.set_autocommit(True)
        try:
            with connection.cursor() as cursor:
                cursor.execute("VACUUM (ANALYZE)")
        finally:
            if not previous:
                connection.set_autocommit(False)
        return "VACUUM (ANALYZE)"
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE")
    return "ANALYZE"


class Command(BaseCommand):
    help = "Check migration state and optionally run bounded database statistics maintenance."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--check-only", action="store_true", help="only check for pending migrations"
        )
        parser.add_argument("--analyze", action="store_true", help="refresh planner statistics")
        parser.add_argument("--json", action="store_true", dest="as_json")

    def handle(self, *args: object, **options: object) -> str | None:
        del args
        pending = _pending_migrations()
        action: str | None = None
        if options.get("analyze"):
            action = _analyze()
        result: dict[str, Any] = {
            "database_vendor": connection.vendor,
            "pending_migrations": pending,
            "pending_count": len(pending),
            "maintenance_action": action,
            "status": "ok" if not pending else "pending_migrations",
        }
        if options.get("as_json"):
            self.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))
        else:
            self.stdout.write(f"Database vendor: {connection.vendor}")
            self.stdout.write(f"Pending migrations: {len(pending)}")
            if action:
                self.stdout.write(f"Maintenance action: {action}")
        if pending and options.get("check_only"):
            raise CommandError("database has unapplied migrations")
        return None
