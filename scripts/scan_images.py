#!/usr/bin/env python3
"""Fail when Docker Scout reports vulnerabilities at or above a threshold."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", help="local image references")
    parser.add_argument("--severity", default="critical", help="critical,high or a comma list")
    args = parser.parse_args()
    docker = shutil.which("docker")
    if docker is None:
        print("FAIL image scan: docker is not installed", file=sys.stderr)
        return 2
    failed = False
    for image in args.images:
        command = [
            docker,
            "scout",
            "cves",
            "--exit-code",
            "--only-severity",
            args.severity,
            f"local://{image}",
        ]
        print(f"=== image scan {image} ({args.severity}) ===")
        result = subprocess.run(command, check=False)
        failed |= result.returncode != 0
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
