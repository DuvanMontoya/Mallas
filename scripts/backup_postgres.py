#!/usr/bin/env python3
"""Create an auditable PostgreSQL custom-format backup without logging secrets.

The normal production invocation uses the host's ``pg_dump`` client.  Local
Docker installations may pass ``--container`` to run the client inside the
PostgreSQL container.  The output and metadata are written atomically with
0600 permissions; encryption and off-site retention belong to the configured
object-storage/secret-management boundary described in the runbook.
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

import psycopg


class BackupError(RuntimeError):
    """Raised for a safe, actionable backup failure."""


BUSINESS_TABLES = (
    "curriculum_curriculumrevision",
    "curriculum_course",
    "curriculum_courseversion",
    "curriculum_planmembership",
    "rules_requirement",
    "student_records_programenrollment",
    "identity_auditevent",
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
        raise BackupError("DATABASE_URL must use the PostgreSQL scheme")
    if not parsed.hostname or not parsed.path.strip("/"):
        raise BackupError("DATABASE_URL must include a host and database")
    database = unquote(parsed.path.strip("/"))
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,63}", database):
        raise BackupError("database name contains unsupported characters")
    query = parse_qs(parsed.query)
    sslmode = query.get("sslmode", [""])[0]
    return DatabaseTarget(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=database,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        sslmode=sslmode,
    )


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


def _command(
    target: DatabaseTarget,
    *,
    binary: str,
    container: str | None,
    container_env_file: Path | None = None,
    snapshot_id: str | None = None,
) -> list[str]:
    args = [binary]
    if container:
        args = [shutil.which("docker") or "docker", "exec", "-i"]
        if target.password and container_env_file is None:
            raise BackupError("container credentials require a temporary env file")
        if container_env_file is not None:
            args.extend(["--env-file", str(container_env_file)])
        args.append(container)
        args.append(binary)
    args.extend(
        [
            "--format=custom",
            "--no-owner",
            "--no-acl",
            "--host",
            "127.0.0.1" if container else target.host,
            "--port",
            str(target.port),
            "--username",
            target.user,
            "--dbname",
            target.database,
        ]
    )
    if snapshot_id:
        args.extend(["--snapshot", snapshot_id])
    return args


def _business_row_counts(
    connection: psycopg.Connection[object],
) -> dict[str, int]:
    statements = " UNION ALL ".join(
        f"SELECT '{table}', COUNT(*)::bigint FROM {table}" for table in BUSINESS_TABLES
    )
    try:
        rows = connection.execute(statements).fetchall()
    except psycopg.Error as exc:
        raise BackupError(
            f"business row-count query failed: {type(exc).__name__}"
        ) from exc
    counts = {str(table): int(count) for table, count in rows}
    if set(counts) != set(BUSINESS_TABLES):
        raise BackupError("business row-count query returned an incomplete result")
    return counts


def _metadata_path(backup_path: Path) -> Path:
    return backup_path.with_suffix(backup_path.suffix + ".json")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.partial")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def create_backup(
    *,
    database_url: str,
    output_dir: Path,
    label: str,
    container: str | None = None,
    timeout_seconds: int = 3600,
) -> tuple[Path, Path]:
    target = _database_target(database_url)
    if container and shutil.which("docker") is None:
        raise BackupError("docker is required when --container is used")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", label):
        raise BackupError("label contains unsupported characters")
    output_dir = output_dir.resolve()
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output_dir, 0o700)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = output_dir / f"{label}-{stamp}.dump"
    metadata_path = _metadata_path(backup_path)
    if backup_path.exists() or metadata_path.exists():
        raise BackupError(f"refusing to overwrite existing backup {backup_path.name}")
    partial = output_dir / f".{backup_path.name}.{os.getpid()}.partial"
    environment = os.environ.copy()
    if target.password and not container:
        environment["PGPASSWORD"] = target.password
    if target.sslmode:
        environment["PGSSLMODE"] = target.sslmode
    container_env_file = _container_env_file(target) if container else None
    business_row_counts: dict[str, int]
    try:
        try:
            with psycopg.connect(database_url) as snapshot_connection:
                snapshot_connection.execute(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                )
                snapshot_row = snapshot_connection.execute(
                    "SELECT pg_export_snapshot()"
                ).fetchone()
                if snapshot_row is None:
                    raise BackupError("PostgreSQL did not export a backup snapshot")
                command = _command(
                    target,
                    binary="pg_dump",
                    container=container,
                    container_env_file=container_env_file,
                    snapshot_id=str(snapshot_row[0]),
                )
                with partial.open("wb") as stream:
                    completed = subprocess.run(
                        command,
                        env=environment,
                        stdout=stream,
                        stderr=subprocess.PIPE,
                        check=False,
                        timeout=timeout_seconds,
                    )
                if completed.returncode:
                    detail = completed.stderr.decode("utf-8", errors="replace")[
                        -500:
                    ].strip()
                    raise BackupError(
                        f"pg_dump failed ({completed.returncode}): {detail}"
                    )
                business_row_counts = _business_row_counts(snapshot_connection)
                snapshot_connection.rollback()
            if partial.stat().st_size == 0:
                raise BackupError("pg_dump produced an empty backup")
            os.chmod(partial, 0o600)
            os.replace(partial, backup_path)
        except (OSError, subprocess.TimeoutExpired, psycopg.Error) as exc:
            raise BackupError(f"backup command failed: {type(exc).__name__}") from exc
    finally:
        if partial.exists():
            partial.unlink()
        if container_env_file is not None and container_env_file.exists():
            container_env_file.unlink()

    version = "unknown"
    try:
        version_result = subprocess.run(
            ["pg_dump", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        version = version_result.stdout.strip() or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        if container:
            version = "container-client"
    metadata = {
        "backup_format": "postgres-custom",
        "created_at": datetime.now(UTC).isoformat(),
        "database": target.database,
        "filename": backup_path.name,
        "host": target.host,
        "port": target.port,
        "pg_dump_version": version,
        "sha256": _sha256(backup_path),
        "size_bytes": backup_path.stat().st_size,
        "business_row_counts": business_row_counts,
    }
    _write_json(metadata_path, metadata)
    return backup_path, metadata_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    parser.add_argument("--output-dir", type=Path, default=Path("var/backups"))
    parser.add_argument("--label", default="curriculum")
    parser.add_argument("--container", help="Run pg_dump inside this Docker container")
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    args = parser.parse_args()
    if not args.database_url:
        print("FAIL backup: DATABASE_URL is required", file=sys.stderr)
        return 2
    try:
        backup, metadata = create_backup(
            database_url=args.database_url,
            output_dir=args.output_dir,
            label=args.label,
            container=args.container,
            timeout_seconds=args.timeout_seconds,
        )
    except BackupError as exc:
        print(f"FAIL backup: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps({"backup": str(backup), "metadata": str(metadata)}, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
