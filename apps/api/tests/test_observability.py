from __future__ import annotations

import json
import logging
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings

from modules.observability.logging import JsonFormatter
from modules.observability.metrics import record_request, render_prometheus
from modules.observability.redaction import redact, safe_route


class ObservabilityTests(TestCase):
    def test_request_correlation_and_trace_headers_are_returned(self) -> None:
        response = self.client.get(
            "/api/v1/health/live",
            HTTP_X_REQUEST_ID="request-2514",
            HTTP_TRACEPARENT=("00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Request-ID"], "request-2514")
        self.assertRegex(response["X-Trace-ID"], r"^[0-9a-f]{32}$")
        self.assertEqual(response.json()["status"], "ok")

    def test_invalid_correlation_id_is_replaced(self) -> None:
        response = self.client.get("/api/v1/health/live", HTTP_X_REQUEST_ID="id with spaces")

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response["X-Request-ID"], "id with spaces")
        self.assertRegex(response["X-Request-ID"], r"^[0-9a-f-]{36}$")

    def test_private_api_responses_are_never_cached(self) -> None:
        response = self.client.get("/api/v1/auth/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["Pragma"], "no-cache")

    def test_formatter_redacts_sensitive_values_and_exception_details(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="request from student@example.edu bearer abc.def.ghi",
            args=(),
            exc_info=None,
        )
        record.structured = {
            "password": "secret-value",
            "safe_status": "ok",
            "student_number": "12345678",
        }

        payload = json.loads(formatter.format(record))

        self.assertNotIn("student@example.edu", json.dumps(payload))
        self.assertNotIn("secret-value", json.dumps(payload))
        self.assertEqual(payload["safe_status"], "ok")
        self.assertEqual(payload["student_number"], "[REDACTED]")

    def test_route_and_metrics_do_not_include_identifiers_or_queries(self) -> None:
        self.assertEqual(
            safe_route("/api/v1/history/12345678?student=someone@example.edu"),
            "/api/v1/history/:id",
        )
        self.assertEqual(redact({"token": "secret", "status": "ok"})["token"], "[REDACTED]")

        record_request(
            method="GET",
            route="/api/v1/history/12345678?student=someone@example.edu",
            status_code=500,
            duration_seconds=0.02,
        )
        exposition = render_prometheus()

        self.assertIn("curriculum_http_requests_total", exposition)
        self.assertNotIn("12345678", exposition)
        self.assertNotIn("someone@example.edu", exposition)

    def test_readiness_returns_safe_503_when_database_is_unavailable(self) -> None:
        with patch("config.api.connection.cursor", side_effect=DatabaseError("secret db details")):
            response = self.client.get("/api/v1/health/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "NOT_READY")
        self.assertNotIn("secret db details", response.content.decode())

    @override_settings(DEBUG=True)  # type: ignore[untyped-decorator]
    def test_metrics_health_is_aggregate_and_has_no_academic_payload(self) -> None:
        response = self.client.get("/api/v1/health/metrics")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIsInstance(payload["metrics"], dict)
        self.assertNotIn("student_id", json.dumps(payload))

    @override_settings(DEBUG=False, OBSERVABILITY_METRICS_TOKEN="metrics-test-token")  # type: ignore[untyped-decorator]
    def test_metrics_health_requires_configured_production_token(self) -> None:
        unauthorized = self.client.get("/api/v1/health/metrics")
        authorized = self.client.get(
            "/api/v1/health/metrics",
            HTTP_X_METRICS_TOKEN="metrics-test-token",
        )

        self.assertEqual(unauthorized.status_code, 404)
        self.assertEqual(authorized.status_code, 200)
