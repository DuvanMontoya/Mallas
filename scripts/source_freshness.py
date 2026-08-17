#!/usr/bin/env python3
"""Observe official normative sources without publishing curriculum changes.

The source list is committed and allowlisted. The job records reachability,
HTTP metadata and a bounded content hash in a JSON report. It never writes a
SourceSnapshot, changes a curriculum revision, or marks a rule VERIFIED.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import socket
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class SourceWatchError(RuntimeError):
    """Raised when a configured source violates the safe watch contract."""


@dataclass(frozen=True, slots=True)
class WatchedSource:
    key: str
    url: str
    allowed_hosts: tuple[str, ...]
    max_age_days: int


def _public_addresses(hostname: str, port: int) -> tuple[str, ...]:
    try:
        records = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise SourceWatchError(f"DNS resolution failed for {hostname}") from exc
    addresses = tuple(sorted({record[4][0] for record in records}))
    if not addresses:
        raise SourceWatchError(f"DNS returned no addresses for {hostname}")
    for value in addresses:
        address = ipaddress.ip_address(value)
        if not address.is_global:
            raise SourceWatchError(f"source resolved to non-public address for {hostname}")
    return addresses


def _validate_url(url: str, allowed_hosts: tuple[str, ...]) -> tuple[str, int, str]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise SourceWatchError("source URL must be HTTPS without credentials")
    if parsed.port not in (None, 443):
        raise SourceWatchError("source URL must use the default HTTPS port")
    try:
        hostname = (parsed.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as exc:
        raise SourceWatchError("source hostname is not valid IDNA") from exc
    normalized_allowlist = {item.encode("idna").decode("ascii").lower().rstrip(".") for item in allowed_hosts}
    if not hostname or hostname not in normalized_allowlist:
        raise SourceWatchError(f"source host is not allowlisted: {hostname or '<empty>'}")
    _public_addresses(hostname, parsed.port or 443)
    return hostname, parsed.port or 443, parsed.path or "/"


class _ValidatedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allowed_hosts: tuple[str, ...]) -> None:
        super().__init__()
        self.allowed_hosts = allowed_hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        _validate_url(newurl, self.allowed_hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _parse_last_modified(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _load_sources(path: Path) -> list[WatchedSource]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("policy") != "observe_only_no_auto_publish":
        raise SourceWatchError("source watch policy must be observe_only_no_auto_publish")
    result: list[WatchedSource] = []
    for raw in payload.get("sources", []):
        if not isinstance(raw, dict):
            raise SourceWatchError("each source entry must be an object")
        key = str(raw.get("key", ""))
        url = str(raw.get("url", ""))
        hosts = tuple(str(item) for item in raw.get("allowed_hosts", []))
        max_age_days = int(raw.get("max_age_days", 0))
        if not key or not hosts or not 1 <= max_age_days <= 3650:
            raise SourceWatchError(f"invalid source watch entry: {key or '<empty>'}")
        _validate_url(url, hosts)
        result.append(WatchedSource(key, url, hosts, max_age_days))
    if not result:
        raise SourceWatchError("source watch configuration contains no sources")
    return result


def _check_source(source: WatchedSource, *, timeout: float, max_bytes: int) -> dict[str, object]:
    checked_at = datetime.now(UTC)
    try:
        _validate_url(source.url, source.allowed_hosts)
        request = Request(
            source.url,
            headers={
                "Accept": "text/html,application/pdf,application/json;q=0.8,*/*;q=0.1",
                "User-Agent": "curriculum-navigator-source-watch/1.0",
            },
        )
        opener = build_opener(_ValidatedRedirectHandler(source.allowed_hosts))
        with opener.open(request, timeout=timeout) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                raise SourceWatchError("source response exceeds the configured byte limit")
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise SourceWatchError("source response exceeds the configured byte limit")
            last_modified = _parse_last_modified(response.headers.get("Last-Modified"))
            age_days = (
                max(0.0, (checked_at - last_modified).total_seconds() / 86400)
                if last_modified
                else None
            )
            if age_days is None:
                state = "UNKNOWN"
                basis = "no_freshness_validator"
            else:
                state = "STALE" if age_days > source.max_age_days else "FRESH"
                basis = "last_modified"
            return {
                "key": source.key,
                "url": source.url,
                "checked_at": checked_at.isoformat(),
                "http_status": int(response.status),
                "content_type": response.headers.get("Content-Type", "").split(";", 1)[0],
                "last_modified": last_modified.isoformat() if last_modified else None,
                "age_days": age_days,
                "max_age_days": source.max_age_days,
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
                "state": state,
                "basis": basis,
            }
    except (HTTPError, URLError, OSError, ValueError, SourceWatchError) as exc:
        return {
            "key": source.key,
            "url": source.url,
            "checked_at": checked_at.isoformat(),
            "state": "ERROR",
            "reason": type(exc).__name__,
            "detail": str(exc)[:240],
        }


def build_report(
    config_path: Path,
    *,
    offline: bool = False,
    timeout: float = 10.0,
    max_bytes: int = 5 * 1024 * 1024,
) -> dict[str, object]:
    sources = _load_sources(config_path)
    checks: list[dict[str, object]] = []
    if offline:
        checked_at = datetime.now(UTC).isoformat()
        checks = [
            {
                "key": source.key,
                "url": source.url,
                "checked_at": checked_at,
                "state": "UNKNOWN",
                "reason": "offline_mode",
            }
            for source in sources
        ]
    else:
        checks = [_check_source(source, timeout=timeout, max_bytes=max_bytes) for source in sources]
    return {
        "schema_version": "1.0",
        "policy": "observe_only_no_auto_publish",
        "generated_at": datetime.now(UTC).isoformat(),
        "config": str(config_path.as_posix()),
        "checks": checks,
        "summary": {
            state: sum(1 for check in checks if check.get("state") == state)
            for state in ("FRESH", "STALE", "UNKNOWN", "ERROR")
        },
    }


def _write_report(path: Path, report: dict[str, object]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.partial")
    try:
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("docs/research/source_watch.json"))
    parser.add_argument("--output", type=Path, default=Path("var/reports/source-freshness.json"))
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--max-bytes", type=int, default=5 * 1024 * 1024)
    parser.add_argument("--fail-on-stale", action="store_true")
    parser.add_argument("--fail-on-unknown", action="store_true")
    args = parser.parse_args()
    try:
        report = build_report(
            args.config,
            offline=args.offline,
            timeout=args.timeout,
            max_bytes=args.max_bytes,
        )
        _write_report(args.output, report)
    except (OSError, ValueError, SourceWatchError) as exc:
        print(f"FAIL source freshness: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], sort_keys=True))
    summary = report["summary"]
    if args.fail_on_stale and summary["STALE"]:
        return 1
    if args.fail_on_unknown and (summary["UNKNOWN"] or summary["ERROR"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
