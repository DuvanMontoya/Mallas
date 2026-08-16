#!/usr/bin/env python3
"""Detect breaking changes between two OpenAPI 3 JSON contracts.

Additive paths, operations, response fields and optional request fields are
compatible. Removing an operation/schema, adding a required request field,
removing a required response field, or changing a type is breaking.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _operations(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    operations: dict[str, dict[str, Any]] = {}
    for path, item in document.get("paths", {}).items():
        for method, operation in item.items():
            if method.lower() in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "options",
                "head",
            }:
                operations[f"{method.upper()} {path}"] = operation
    return operations


def _schema(document: dict[str, Any], value: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    reference = value.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/components/schemas/"):
        name = reference.rsplit("/", 1)[-1]
        return document.get("components", {}).get("schemas", {}).get(name, {})
    return value


def _required_fields(schema: dict[str, Any]) -> set[str]:
    return {str(value) for value in schema.get("required", [])}


def _content_schema(
    document: dict[str, Any], content: dict[str, Any]
) -> dict[str, Any]:
    for media in (
        "application/json",
        "application/problem+json",
        "multipart/form-data",
    ):
        if media in content:
            return _schema(document, content[media].get("schema"))
    first = next(iter(content.values()), {})
    return _schema(document, first.get("schema")) if isinstance(first, dict) else {}


def _compare_schema(
    base_document: dict[str, Any],
    current_document: dict[str, Any],
    base_schema: dict[str, Any],
    current_schema: dict[str, Any],
    location: str,
    changes: list[str],
) -> None:
    base_schema = _schema(base_document, base_schema)
    current_schema = _schema(current_document, current_schema)
    if base_schema.get("type") != current_schema.get("type"):
        changes.append(f"{location}: schema type changed")
        return
    base_required = _required_fields(base_schema)
    current_required = _required_fields(current_schema)
    for field in sorted(base_required - current_required):
        changes.append(f"{location}: required response field removed: {field}")
    base_properties = base_schema.get("properties", {})
    current_properties = current_schema.get("properties", {})
    for field in sorted(base_required & set(base_properties) & set(current_properties)):
        if base_properties[field].get("type") != current_properties[field].get("type"):
            changes.append(f"{location}: required response field type changed: {field}")


def find_breaking_changes(
    base_document: dict[str, Any], current_document: dict[str, Any]
) -> list[str]:
    changes: list[str] = []
    base_operations = _operations(base_document)
    current_operations = _operations(current_document)
    for operation in sorted(set(base_operations) - set(current_operations)):
        changes.append(f"removed operation: {operation}")

    for operation in sorted(set(base_operations) & set(current_operations)):
        base_operation = base_operations[operation]
        current_operation = current_operations[operation]
        base_parameters = {
            (parameter.get("in"), parameter.get("name")): parameter
            for parameter in base_operation.get("parameters", [])
        }
        current_parameters = {
            (parameter.get("in"), parameter.get("name")): parameter
            for parameter in current_operation.get("parameters", [])
        }
        for key in sorted(set(base_parameters) - set(current_parameters)):
            if base_parameters[key].get("required"):
                changes.append(
                    f"{operation}: required parameter removed: {key[0]}:{key[1]}"
                )
        for key in sorted(set(current_parameters) - set(base_parameters)):
            if current_parameters[key].get("required"):
                changes.append(
                    f"{operation}: new required parameter: {key[0]}:{key[1]}"
                )
        base_body = base_operation.get("requestBody", {})
        current_body = current_operation.get("requestBody", {})
        base_body_schema = _content_schema(base_document, base_body.get("content", {}))
        current_body_schema = _content_schema(
            current_document, current_body.get("content", {})
        )
        base_body_required = _required_fields(base_body_schema)
        current_body_required = _required_fields(current_body_schema)
        for field in sorted(current_body_required - base_body_required):
            changes.append(f"{operation}: new required request field: {field}")
        for field in sorted(base_body_required & current_body_required):
            base_field = base_body_schema.get("properties", {}).get(field, {})
            current_field = current_body_schema.get("properties", {}).get(field, {})
            if base_field.get("type") != current_field.get("type"):
                changes.append(f"{operation}: request field type changed: {field}")

        base_responses = base_operation.get("responses", {})
        current_responses = current_operation.get("responses", {})
        for status in sorted(set(base_responses) - set(current_responses)):
            if str(status).startswith("2"):
                changes.append(f"{operation}: success response removed: {status}")
        for status in sorted(set(base_responses) & set(current_responses)):
            if str(status).startswith("2"):
                base_content = base_responses[status].get("content", {})
                current_content = current_responses[status].get("content", {})
                base_response_schema = _content_schema(base_document, base_content)
                current_response_schema = _content_schema(
                    current_document, current_content
                )
                _compare_schema(
                    base_document,
                    current_document,
                    base_response_schema,
                    current_response_schema,
                    f"{operation} {status}",
                    changes,
                )

    base_schemas = base_document.get("components", {}).get("schemas", {})
    current_schemas = current_document.get("components", {}).get("schemas", {})
    for schema in sorted(set(base_schemas) - set(current_schemas)):
        changes.append(f"removed schema: {schema}")
    return changes


def _read_revision(revision: str) -> dict[str, Any]:
    result = subprocess.run(
        ["git", "show", f"{revision}:artifacts/openapi.json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, help="Base OpenAPI JSON file")
    parser.add_argument(
        "--base-revision", help="Git revision containing artifacts/openapi.json"
    )
    parser.add_argument(
        "--current", type=Path, default=ROOT / "artifacts" / "openapi.json"
    )
    args = parser.parse_args()
    if bool(args.base) == bool(args.base_revision):
        parser.error("provide exactly one of --base or --base-revision")
    base = (
        _read_revision(args.base_revision)
        if args.base_revision
        else json.loads(args.base.read_text())
    )
    current = json.loads(args.current.read_text(encoding="utf-8"))
    changes = find_breaking_changes(base, current)
    if changes:
        print("Breaking OpenAPI changes detected:")
        print("\n".join(f"- {change}" for change in changes))
        return 1
    print("OpenAPI breaking-diff check passed: no incompatible changes detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
