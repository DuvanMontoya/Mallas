from __future__ import annotations

import json
from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class DatabaseMaintenanceCommandTests(TestCase):
    def test_check_only_reports_clean_migration_state(self) -> None:
        output = StringIO()
        call_command("db_maintenance", "--check-only", "--json", stdout=output)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["pending_count"], 0)
        self.assertEqual(payload["status"], "ok")

    def test_analyze_is_explicit_and_does_not_require_postgres(self) -> None:
        output = StringIO()
        call_command("db_maintenance", "--analyze", "--json", stdout=output)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["maintenance_action"], "ANALYZE")
