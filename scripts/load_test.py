#!/usr/bin/env python3
"""Run a bounded HTTP load probe and report measured latency percentiles.

This is deliberately a small standard-library probe for local/staging use. It
does not create accounts, mutate academic data, or treat a local latency as a
universal SLO. Every request is read-only and the endpoint list is explicit.
"""

from __future__ import annotations

import argparse
import statistics
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class Result:
    endpoint: str
    status: int
    elapsed_ms: float
    error: str | None = None


def _base_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password:
        raise ValueError("base URL must be an HTTP(S) URL without credentials")
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def _request(base: str, endpoint: str, timeout: float) -> Result:
    path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    url = f"{base}{path}"
    started = time.perf_counter()
    request = Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            response.read(64 * 1024)
            status = response.status
            error = None
    except HTTPError as exc:
        status = exc.code
        error = f"http_{exc.code}"
    except (TimeoutError, URLError, OSError) as exc:
        status = 0
        error = type(exc).__name__
    return Result(endpoint, status, (time.perf_counter() - started) * 1000, error)


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((percentile / 100) * (len(ordered) - 1)))))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument(
        "--endpoint",
        action="append",
        dest="endpoints",
        default=["/api/v1/health/live", "/api/v1/curriculum-map"],
        help="Read-only endpoint path; repeat to add endpoints.",
    )
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1 or args.timeout <= 0:
        parser.error("requests, concurrency and timeout must be positive")
    try:
        base = _base_url(args.base_url)
    except ValueError as error:
        parser.error(str(error))

    endpoints = list(dict.fromkeys(args.endpoints))
    work = [endpoints[index % len(endpoints)] for index in range(args.requests)]
    results: list[Result] = []
    with ThreadPoolExecutor(max_workers=args.concurrency, thread_name_prefix="load-probe") as pool:
        futures = [pool.submit(_request, base, endpoint, args.timeout) for endpoint in work]
        for future in as_completed(futures):
            results.append(future.result())

    failed = 0
    for endpoint in endpoints:
        endpoint_results = [result for result in results if result.endpoint == endpoint]
        latencies = [result.elapsed_ms for result in endpoint_results]
        failures = [result for result in endpoint_results if not 200 <= result.status < 400]
        failed += len(failures)
        if not latencies:
            print(f"FAIL endpoint={endpoint} samples=0")
            failed += 1
            continue
        statuses: dict[int, int] = defaultdict(int)
        for result in endpoint_results:
            statuses[result.status] += 1
        print(
            f"endpoint={endpoint} samples={len(latencies)} "
            f"p50_ms={_percentile(latencies, 50):.3f} "
            f"p95_ms={_percentile(latencies, 95):.3f} "
            f"max_ms={max(latencies):.3f} statuses={dict(sorted(statuses.items()))}"
        )
        for result in failures[:3]:
            print(f"failure endpoint={endpoint} status={result.status} error={result.error}")

    print(
        f"summary requests={len(results)} concurrency={args.concurrency} "
        f"mean_ms={statistics.fmean(result.elapsed_ms for result in results):.3f} "
        f"failures={failed}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
