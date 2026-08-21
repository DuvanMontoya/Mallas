#!/usr/bin/env python3
"""Run public, non-authenticated synthetic checks without logging response data."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


def _base_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password:
        raise ValueError("base URL must be an HTTP(S) URL without credentials")
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def _fetch(url: str) -> tuple[int, bytes | None, str | None]:
    request = Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=5) as response:
            # Keep a hard ceiling even though health responses are deliberately
            # small, so a compromised endpoint cannot exhaust the smoke runner.
            return response.status, response.read(4 * 1024 * 1024), None
    except HTTPError as error:
        return error.code, None, f"http_{error.code}"
    except (TimeoutError, URLError, OSError) as error:
        return 0, None, type(error).__name__


def _check_json(url: str, predicate: Callable[[dict[str, object]], bool]) -> tuple[bool, str]:
    status, body, error = _fetch(url)
    if error or status != 200 or body is None:
        return False, error or f"status_{status}"
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, "invalid_json"
    if not isinstance(payload, dict) or not predicate(payload):
        return False, "unexpected_payload"
    return True, "ok"


def _check_web(url: str) -> tuple[bool, str]:
    status, _body, error = _fetch(url)
    if error or not 200 <= status < 400:
        return False, error or f"status_{status}"
    return True, "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="API base URL, for example http://localhost:8000")
    parser.add_argument("--web-url", help="Optional web URL, for example http://localhost:3000")
    args = parser.parse_args()
    try:
        base = _base_url(args.base_url)
        web = _base_url(args.web_url) if args.web_url else None
    except ValueError as error:
        print(f"FAIL configuration: {error}")
        return 2

    checks = [
        (
            "live",
            _check_json(
                f"{base}/api/v1/health/live",
                lambda payload: payload.get("status") == "ok",
            ),
        ),
        (
            "ready",
            _check_json(
                f"{base}/api/v1/health/ready",
                lambda payload: payload.get("status") == "ready" and payload.get("database") == "ok",
            ),
        ),
    ]
    if web:
        checks.append(("web", _check_web(web)))

    failed = False
    for name, (passed, reason) in checks:
        print(f"{'PASS' if passed else 'FAIL'} {name}: {reason}")
        failed |= not passed
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
