from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts import backup_postgres, production_preflight, restore_drill  # noqa: E402


class OperationalSecurityTests(SimpleTestCase):
    def test_database_password_never_enters_container_command_argv(self) -> None:
        target = backup_postgres._database_target(
            "postgresql://backup:super-secret@db.example.test:5432/curriculum?sslmode=require"
        )
        command = backup_postgres._command(
            target,
            binary="pg_dump",
            container="postgres",
            container_env_file=Path("C:/tmp/curriculum-pg.env"),
        )
        self.assertNotIn(target.password, command)
        self.assertIn("--env-file", command)

        restore_target = restore_drill._database_target(
            "postgresql://backup:super-secret@db.example.test:5432/curriculum?sslmode=require"
        )
        with patch("scripts.restore_drill.shutil.which", return_value="docker"):
            restore_command = restore_drill._client_command(
                restore_target,
                "psql",
                "postgres",
                container="postgres",
                container_env_file=Path("C:/tmp/curriculum-pg.env"),
            )
        self.assertNotIn(restore_target.password, restore_command)
        self.assertIn("--env-file", restore_command)

    def test_restore_drill_reports_cleanup_failure(self) -> None:
        target = restore_drill._database_target(
            "postgresql://backup:secret@db.example.test:5432/curriculum"
        )
        failed = subprocess.CompletedProcess(["psql"], 1, "", "drop failed")
        with (
            patch("scripts.restore_drill._client_command", return_value=["psql"]),
            patch("scripts.restore_drill._run", return_value=failed),
            self.assertRaisesRegex(restore_drill.RestoreError, "cleanup failed"),
        ):
            restore_drill._drop_drill_database(
                target=target,
                drill_database="restore_drill_test",
                container=None,
                container_env_file=None,
            )

    def test_production_preflight_requires_split_roles_mfa_and_immutable_images(self) -> None:
        valid = {
            "API_IMAGE": "registry.example/api:2026.08.17@sha256:" + "a" * 64,
            "WEB_IMAGE": "registry.example/web:2026.08.17@sha256:" + "b" * 64,
            "RUNTIME_DATABASE_URL": "postgresql://runtime:one@db/curriculum",
            "MIGRATION_DATABASE_URL": "postgresql://migrator:two@db/curriculum",
            "DJANGO_SECRET_KEY": "k" * 64,
            "PRIVILEGED_MFA_REQUIRED": "true",
        }
        self.assertEqual(production_preflight.validate(valid), [])

        invalid = {
            **valid,
            "API_IMAGE": "registry.example/api:latest",
            "PRIVILEGED_MFA_REQUIRED": "false",
        }
        invalid["MIGRATION_DATABASE_URL"] = invalid["RUNTIME_DATABASE_URL"]
        errors = production_preflight.validate(invalid)
        self.assertTrue(any("API_IMAGE" in error for error in errors))
        self.assertTrue(any("MFA" in error for error in errors))
        self.assertTrue(any("separate roles" in error for error in errors))

    def test_workflow_action_pins_are_immutable(self) -> None:
        from scripts.check_action_pins import check

        self.assertEqual(check(), [])
