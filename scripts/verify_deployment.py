#!/usr/bin/env python3
"""Verify production deployment assets without requiring Docker or credentials."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_DIGEST = re.compile(r"@sha256:[0-9a-f]{64}")


def _require(path: Path, *snippets: str) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"missing {path.relative_to(ROOT).as_posix()}"]
    text = path.read_text(encoding="utf-8")
    for snippet in snippets:
        if snippet not in text:
            errors.append(f"{path.relative_to(ROOT).as_posix()} missing {snippet!r}")
    return errors


def verify() -> list[str]:
    errors: list[str] = []
    for relative, user in (
        ("infra/docker/api.Dockerfile", "USER app"),
        ("infra/docker/web.Dockerfile", "USER nextjs"),
    ):
        path = ROOT / relative
        errors.extend(_require(path, user, "HEALTHCHECK", "COPY --from="))
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if len(_DIGEST.findall(text)) < 1:
                errors.append(f"{relative} must pin at least one base image digest")
            for forbidden in ("DJANGO_SECRET_KEY=", "POSTGRES_PASSWORD=", "PGPASSWORD="):
                if forbidden in text:
                    errors.append(f"{relative} contains a baked secret assignment {forbidden}")

    compose = ROOT / "infra/docker-compose.production.yml"
    errors.extend(
        _require(
            compose,
            "migrate:",
            "reverse-proxy:",
            "read_only: true",
            "no-new-privileges:true",
            "private_imports:",
            "API_IMAGE must be an immutable registry reference",
            "WEB_IMAGE must be an immutable registry reference",
            "MIGRATION_DATABASE_URL",
            "RUNTIME_DATABASE_URL",
        )
    )
    if compose.is_file():
        text = compose.read_text(encoding="utf-8")
        if "build:" in text:
            errors.append("production Compose must consume promoted images, not build on the server")
        constant_images = [
            line
            for line in text.splitlines()
            if line.strip().startswith("image:") and "${" not in line
        ]
        if not constant_images or any("@sha256:" not in line for line in constant_images):
            errors.append("all constant production image references must use digests")

    dev_compose = ROOT / "infra/docker-compose.yml"
    errors.extend(
        _require(
            dev_compose,
            "services:",
            "postgres:",
            "postgres:18.0-alpine@sha256:",
            "curriculum_local_only",
        )
    )

    env_example = ROOT / "infra/production.env.example"
    errors.extend(_require(env_example, "API_IMAGE=", "WEB_IMAGE=", "REPLACE_WITH"))
    for relative, snippets in {
        "infra/docker/Caddyfile": ("reverse_proxy web:3000", "Strict-Transport-Security"),
        "scripts/backup_postgres.py": ("format=custom", "sha256"),
        "scripts/restore_drill.py": ("restore_drill_", "DROP DATABASE"),
        "scripts/production_preflight.py": ("@sha256:", "RUNTIME_DATABASE_URL", "PRIVILEGED_MFA_REQUIRED"),
        "infra/postgres/provision-least-privilege.sql": ("identity_auditevent", "REVOKE UPDATE, DELETE"),
        "docs/ops/DEPLOYMENT_RUNBOOK.md": ("servidor", "smoke.py"),
        "docs/ops/BACKUP_RESTORE_RUNBOOK.md": ("restore_drill.py", "RPO/RTO"),
        "docs/ops/ROLLBACK_RUNBOOK.md": ("digest", "smoke"),
        "docs/ops/OBJECT_STORAGE_STRATEGY.md": ("bucket", "cifrado"),
        ".github/workflows/production-gates.yml": ("restore-drill:", "Docker Scout"),
        ".github/workflows/dependency-check.yml": ("pip-audit", "pnpm audit", "--frozen-lockfile"),
        ".github/workflows/source-freshness.yml": ("source_freshness.py", "fail-on-stale"),
        ".github/workflows/periodic-audits.yml": ("playwright", "scan_secrets.py"),
        "docs/research/source_watch.json": ("observe_only_no_auto_publish", "allowed_hosts"),
        "docs/research/SOURCE_WATCH_DESIGN.md": ("no auto-publish", "source_freshness.py"),
        "docs/ops/SOURCE_FRESHNESS_RUNBOOK.md": ("HUMAN_REVIEW_REQUIRED", "publish"),
        "docs/ops/DATABASE_MAINTENANCE_RUNBOOK.md": ("VACUUM (ANALYZE)", "migrate --check"),
        "docs/ops/RELEASE_CADENCE.md": ("restore-drill", "no auto-publish"),
        "docs/ops/STATE_MAINTENANCE.md": ("verify_state_recovery.py", "ROADMAP_STATUS.json"),
        "scripts/source_freshness.py": ("observe_only_no_auto_publish", "fail-on-stale"),
        "scripts/update_technology_baseline.py": ("official release-note", "--check"),
        "scripts/verify_state_recovery.py": ("CURRENT_STATE.md", "ROADMAP_STATUS.json"),
        "apps/api/modules/governance/management/commands/unknown_rule_queue.py": (
            "HUMAN_REVIEW_REQUIRED",
            "publish_blocker",
        ),
        "apps/api/modules/common/management/commands/db_maintenance.py": ("VACUUM (ANALYZE)", "migrations"),
        "renovate.json": ("dependencyDashboard", '"automerge": false'),
    }.items():
        errors.extend(_require(ROOT / relative, *snippets))
    return errors


def main() -> int:
    errors = verify()
    if errors:
        print("Deployment asset verification failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Deployment asset verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
