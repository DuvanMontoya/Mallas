from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from django.test import Client, TestCase

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.check_openapi_breaking import find_breaking_changes  # noqa: E402


def _contract(*, required_request: bool = False) -> dict[str, Any]:
    request_schema: dict[str, Any] = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"] if required_request else [],
    }
    return {
        "paths": {
            "/items": {
                "post": {
                    "requestBody": {"content": {"application/json": {"schema": request_schema}}},
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"id": {"type": "string"}},
                                        "required": ["id"],
                                    }
                                }
                            }
                        }
                    },
                }
            }
        },
        "components": {"schemas": {"Item": {"type": "object"}}},
    }


class OpenApiDiffTests(TestCase):
    def test_additive_contract_change_is_compatible(self) -> None:
        base = _contract()
        current = _contract()
        current["paths"]["/items"]["post"]["responses"]["201"] = {"description": "Created"}
        self.assertEqual(find_breaking_changes(base, current), [])

    def test_detector_catches_removed_operation_and_required_request_field(self) -> None:
        base = _contract()
        current = _contract(required_request=True)
        del current["paths"]["/items"]
        changes = find_breaking_changes(base, current)
        self.assertTrue(any("removed operation" in change for change in changes))

        current = _contract(required_request=True)
        self.assertTrue(
            any(
                "new required request field" in change
                for change in find_breaking_changes(base, current)
            )
        )


class ApiProblemContractTests(TestCase):
    def test_unauthorized_errors_have_stable_problem_envelope_and_correlation(self) -> None:
        response = self.client.get(
            "/api/v1/auth/me",
            HTTP_X_REQUEST_ID="contract-test-1",
        )
        self.assertEqual(response.status_code, 401)
        payload = response.json()
        self.assertEqual(payload["code"], "AUTHENTICATION_REQUIRED")
        self.assertEqual(payload["status"], 401)
        self.assertEqual(payload["correlation_id"], "contract-test-1")
        self.assertEqual(response["X-Request-ID"], "contract-test-1")
        self.assertIn("type", payload)
        self.assertIn("fields", payload)

    def test_csrf_and_validation_errors_use_the_same_envelope(self) -> None:
        client = Client(enforce_csrf_checks=True)
        csrf_failed = client.post(
            "/api/v1/auth/login",
            {"email": "student@example.test"},
            content_type="application/json",
        )
        self.assertEqual(csrf_failed.status_code, 403)
        self.assertEqual(csrf_failed.json()["code"], "CSRF_FAILED")

        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        invalid = client.post(
            "/api/v1/auth/login",
            {"email": "student@example.test"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.json()["code"], "VALIDATION_ERROR")
        self.assertIn("fields", invalid.json())

    def test_openapi_declares_shared_problem_schema_on_operations(self) -> None:
        from config.api import api

        self.assertEqual(self.client.get("/api/v1/openapi.json").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/docs").status_code, 404)
        document = api.get_openapi_schema()
        self.assertIn("ProblemDetails", document["components"]["schemas"])
        for path, item in document["paths"].items():
            for method, operation in item.items():
                if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                    continue
                responses = {str(status): value for status, value in operation["responses"].items()}
                self.assertIn("400", responses, f"{method} {path}")
                error_schema = responses["400"]["content"]["application/json"]["schema"]
                self.assertEqual(error_schema["$ref"], "#/components/schemas/ProblemDetails")
