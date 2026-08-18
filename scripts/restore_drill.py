#!/usr/bin/env python3
"""Restore a PostgreSQL backup into an isolated temporary database.

The drill never targets the database named in ``DATABASE_URL``.  It creates a
generated database name, restores the custom-format dump, verifies migrations
and public tables, and drops the temporary database in a finally block.  A
Docker container can provide the PostgreSQL client with ``--container`` for a
developer machine that does not install ``pg_restore``/``psql`` locally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid4


class RestoreError(RuntimeError):
    """Raised for a safe, actionable restore failure."""


CRITICAL_TABLES = (
    "django_migrations",
    "curriculum_curriculumrevision",
    "curriculum_course",
    "curriculum_courseversion",
    "curriculum_requirementgroup",
    "curriculum_planmembership",
    "rules_requirement",
    "student_records_programenrollment",
    "audit_degreeauditrun",
    "governance_sourcesnapshot",
)


@dataclass(frozen=True, slots=True)
class DatabaseTarget:
    host: str
    port: int
    database: str
    user: str
    password: str
    sslmode: str


def _database_target(value: str) -> DatabaseTarget:
    parsed = urlparse(value)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RestoreError("DATABASE_URL must use the PostgreSQL scheme")
    if not parsed.hostname or not parsed.path.strip("/"):
        raise RestoreError("DATABASE_URL must include a host and database")
    database = unquote(parsed.path.strip("/"))
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,63}", database):
        raise RestoreError("database name contains unsupported characters")
    query = parse_qs(parsed.query)
    return DatabaseTarget(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=database,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        sslmode=query.get("sslmode", [""])[0],
    )


def _hash(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def _container_env_file(target: DatabaseTarget) -> Path:
    descriptor, raw_path = tempfile.mkstemp(prefix=".curriculum-pg-", suffix=".env")
    path = Path(raw_path)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            if target.password:
                stream.write(f"PGPASSWORD={target.password}\n")
            if target.sslmode:
                stream.write(f"PGSSLMODE={target.sslmode}\n")
        os.chmod(path, 0o600)
        return path
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _docker_prefix(
    target: DatabaseTarget,
    container: str,
    *,
    container_env_file: Path | None = None,
) -> list[str]:
    docker = shutil.which("docker")
    if docker is None:
        raise RestoreError("docker is required when --container is used")
    args = [docker, "exec", "-i"]
    if target.password and container_env_file is None:
        raise RestoreError("container credentials require a temporary env file")
    if container_env_file is not None:
        args.extend(["--env-file", str(container_env_file)])
    args.append(container)
    return args


def _client_command(
    target: DatabaseTarget,
    binary: str,
    database: str,
    *,
    container: str | None,
    container_env_file: Path | None = None,
    extra: list[str] | None = None,
) -> list[str]:
    command = (
        _docker_prefix(target, container, container_env_file=container_env_file)
        if container
        else [binary]
    )
    if container:
        command.append(binary)
    command.extend(
        [
            "--host",
            "127.0.0.1" if container else target.host,
            "--port",
            str(target.port),
            "--username",
            target.user,
            "--dbname",
            database,
        ]
    )
    if extra:
        command.extend(extra)
    return command


def _run(
    command: list[str],
    *,
    target: DatabaseTarget,
    container: bool = False,
    input_stream=None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if target.password and not container:
        environment["PGPASSWORD"] = target.password
    if target.sslmode:
        environment["PGSSLMODE"] = target.sslmode
    try:
        return subprocess.run(
            command,
            env=environment,
            stdin=input_stream,
            stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=input_stream is None,
            check=False,
            timeout=3600,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RestoreError(f"database client failed: {type(exc).__name__}") from exc


def _require_success(result: subprocess.CompletedProcess[str], operation: str) -> None:
    if result.returncode:
        detail = (result.stderr or "")[-500:].strip()
        raise RestoreError(f"{operation} failed ({result.returncode}): {detail}")


def _restore_extra_args(backup_path: Path, *, container: bool) -> list[str]:
    """Build pg_restore arguments; stdin is selected by omitting a filename."""

    arguments = ["--no-owner", "--no-acl", "--exit-on-error"]
    return arguments if container else [*arguments, str(backup_path)]


def _drop_drill_database(
    *,
    target: DatabaseTarget,
    drill_database: str,
    container: str | None,
    container_env_file: Path | None,
) -> None:
    """Drop the isolated database and fail the drill if cleanup is uncertain."""

    quoted_database = f'"{drill_database}"'
    drop = _client_command(
        target,
        "psql",
        "postgres",
        container=container,
        container_env_file=container_env_file,
        extra=["--command", f"DROP DATABASE IF EXISTS {quoted_database}"],
    )
    dropped = _run(drop, target=target, container=bool(container))
    if dropped.returncode:
        detail = (dropped.stderr or "")[-500:].strip()
        raise RestoreError(
            f"cleanup failed: could not drop temporary database {drill_database}: {detail}"
        )


def restore_drill(
    *,
    database_url: str,
    backup_path: Path,
    container: str | None = None,
    minimum_migrations: int = 1,
) -> dict[str, object]:
    target = _database_target(database_url)
    backup_path = backup_path.resolve()
    if not backup_path.is_file() or backup_path.stat().st_size == 0:
        raise RestoreError("backup file must exist and be non-empty")
    digest, size = _hash(backup_path)
    metadata_path = backup_path.with_suffix(backup_path.suffix + ".json")
    if not metadata_path.is_file():
        raise RestoreError("backup metadata manifest is required")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("sha256") != digest or metadata.get("size_bytes") != size:
        raise RestoreError("backup metadata hash/size does not match the dump")
    drill_database = f"restore_drill_{datetime.now(UTC):%Y%m%d%H%M%S}_{uuid4().hex[:8]}"
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", drill_database):
        raise RestoreError("generated drill database name is invalid")
    admin_database = "postgres"
    quoted_database = f'"{drill_database}"'
    created = False
    container_env_file = _container_env_file(target) if container else None
    try:
        create = _client_command(
            target,
            "psql",
            admin_database,
            container=container,
            container_env_file=container_env_file,
            extra=["--command", f"CREATE DATABASE {quoted_database}"],
        )
        _require_success(_run(create, target=target, container=bool(container)), "create drill database")
        created = True
        with backup_path.open("rb") as stream:
            restore = _client_command(
                target,
                "pg_restore",
                drill_database,
                container=container,
                container_env_file=container_env_file,
                extra=_restore_extra_args(backup_path, container=bool(container)),
            )
            _require_success(
                _run(
                    restore,
                    target=target,
                    container=bool(container),
                    input_stream=stream if container else None,
                ),
                "restore dump",
            )
        validate = _client_command(
            target,
            "psql",
            drill_database,
            container=container,
            container_env_file=container_env_file,
            extra=[
                "--no-psqlrc",
                "--tuples-only",
                "--no-align",
                "--command",
                "SELECT (SELECT COUNT(*) FROM django_migrations)::text || '|' || "
                "(SELECT COUNT(*) FROM pg_catalog.pg_tables WHERE schemaname='public')::text || '|' || "
                "(SELECT COUNT(*) FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename IN "
                "('django_migrations','curriculum_curriculumrevision','curriculum_course',"
                "'curriculum_courseversion','curriculum_requirementgroup','curriculum_planmembership',"
                "'rules_requirement','student_records_programenrollment','audit_degreeauditrun',"
                "'governance_sourcesnapshot'))::text",
            ],
        )
        validation = _run(validate, target=target, container=bool(container))
        _require_success(validation, "validate restored schema")
        values = (validation.stdout or "").strip().split("|")
        if len(values) != 3 or not all(value.isdigit() for value in values):
            raise RestoreError("restored schema validation returned an invalid result")
        migrations, tables, critical_tables = (int(value) for value in values)
        if migrations < minimum_migrations or tables == 0:
            raise RestoreError(
                f"restored schema is incomplete: migrations={migrations}, tables={tables}"
            )
        if critical_tables != len(CRITICAL_TABLES):
            raise RestoreError(
                "restored schema is not the curriculum product schema: "
                f"critical_tables={critical_tables}/{len(CRITICAL_TABLES)}"
            )
        return {
            "backup": str(backup_path),
            "backup_sha256": digest,
            "database": drill_database,
            "migrations": migrations,
            "tables": tables,
            "critical_tables": critical_tables,
            "status": "passed",
        }
    finally:
        try:
            if created:
                _drop_drill_database(
                    target=target,
                    drill_database=drill_database,
                    container=container,
                    container_env_file=container_env_file,
                )
        finally:
            if container_env_file is not None and container_env_file.exists():
                container_env_file.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    parser.add_argument("--container", help="Run PostgreSQL clients inside this Docker container")
    parser.add_argument("--minimum-migrations", type=int, default=1)
    args = parser.parse_args()
    if not args.database_url:
        print("FAIL restore drill: DATABASE_URL is required", file=sys.stderr)
        return 2
    try:
        result = restore_drill(
            database_url=args.database_url,
            backup_path=args.backup,
            container=args.container,
            minimum_migrations=args.minimum_migrations,
        )
    except (RestoreError, OSError, json.JSONDecodeError) as exc:
        print(f"FAIL restore drill: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
