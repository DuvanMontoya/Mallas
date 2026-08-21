from __future__ import annotations

import os
import socket
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from django.conf import settings
from django.db import connection
from django.test import Client, SimpleTestCase, TestCase, override_settings

from config.settings import _default_web_origins
from domain.errors import AuditEventImmutableError
from modules.governance.application.source_fetch import (
    SafeSourceFetcher,
    SourceFetchError,
    SourceFetchPolicy,
    SourceFetchResponse,
    validate_source_url,
)
from modules.identity.models import AuditEvent
from modules.imports.application.storage import (
    ArtifactValidationError,
    read_artifact,
    store_artifact,
    validate_artifact,
)


def _public_resolver(hostname: str, port: int) -> list[tuple[object, ...]]:
    del hostname
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def _literal_resolver(hostname: str, port: int) -> list[tuple[object, ...]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (hostname, port))]


class SourceFetchSecurityTests(SimpleTestCase):
    def setUp(self) -> None:
        self.policy = SourceFetchPolicy(
            allowed_hosts=frozenset(
                {"official.example.edu", "127.0.0.1", "10.0.0.1", "169.254.169.254"}
            )
        )

    def test_public_https_source_is_allowlisted_and_normalized(self) -> None:
        validated = validate_source_url(
            "HTTPS://official.example.edu/path?download=1",
            policy=SourceFetchPolicy(allowed_hosts=frozenset({"official.example.edu"})),
            resolver=_public_resolver,
        )

        self.assertEqual(validated.url, "https://official.example.edu/path?download=1")
        self.assertEqual(validated.host_header, "official.example.edu")

    def test_private_ipv4_and_metadata_ranges_are_rejected(self) -> None:
        for url in (
            "https://127.0.0.1/",
            "https://10.0.0.1/",
            "https://100.64.0.1/",
            "https://169.254.169.254/",
        ):
            with self.subTest(url=url), self.assertRaisesRegex(SourceFetchError, "private"):
                validate_source_url(url, policy=self.policy, resolver=_literal_resolver)

    def test_credentials_local_names_non_default_ports_and_fragments_are_rejected(self) -> None:
        cases = (
            "https://user:password@official.example.edu/",
            "https://localhost/",
            "https://official.example.edu:8443/",
            "https://official.example.edu/document.pdf#page=1",
        )
        for url in cases:
            with self.subTest(url=url), self.assertRaises(SourceFetchError):
                validate_source_url(url, policy=self.policy, resolver=_public_resolver)

    def test_redirect_cannot_bypass_private_network_or_host_allowlist(self) -> None:
        transport = Mock(
            side_effect=[
                SourceFetchResponse(
                    status=302,
                    headers={"Location": "https://127.0.0.1/admin"},
                    body=b"",
                )
            ]
        )
        fetcher = SafeSourceFetcher(transport=transport)

        def mixed_resolver(hostname: str, port: int) -> list[tuple[object, ...]]:
            return (
                _literal_resolver(hostname, port)
                if hostname == "127.0.0.1"
                else _public_resolver(hostname, port)
            )

        with self.assertRaisesRegex(SourceFetchError, "private"):
            fetcher.fetch(
                "https://official.example.edu/source.pdf",
                policy=self.policy,
                resolver=mixed_resolver,
            )

    def test_redirects_are_explicit_bounded_and_body_is_bounded(self) -> None:
        responses = iter(
            [
                SourceFetchResponse(
                    status=302,
                    headers={"Location": "https://official.example.edu/final"},
                    body=b"",
                ),
                SourceFetchResponse(
                    status=200,
                    headers={"Content-Type": "application/pdf"},
                    body=b"%PDF-safe",
                ),
            ]
        )
        fetched = SafeSourceFetcher(transport=lambda target, policy: next(responses)).fetch(
            "https://official.example.edu/source.pdf",
            policy=self.policy,
            resolver=_public_resolver,
        )
        self.assertEqual(fetched.redirect_count, 1)
        self.assertEqual(fetched.mime_type, "application/pdf")
        self.assertEqual(
            fetched.sha256, "40cf6c8c77d623ad23e5259ec2dde1db97fc1a09c1f02c9975485ec4e73126de"
        )

        oversized = SafeSourceFetcher(
            transport=lambda target, policy: SourceFetchResponse(
                status=200, headers={}, body=b"0123456789"
            )
        )
        with self.assertRaisesRegex(SourceFetchError, "size limit"):
            oversized.fetch(
                "https://official.example.edu/source.pdf",
                policy=SourceFetchPolicy(
                    allowed_hosts=frozenset({"official.example.edu"}), max_bytes=5
                ),
                resolver=_public_resolver,
            )


class UploadStorageSecurityTests(SimpleTestCase):
    def test_storage_is_private_bounded_and_path_contained(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            content = b'{"safe": true}'
            digest = validate_artifact(
                filename="history.json", content=content, declared_mime="application/json"
            ).content_sha256
            with override_settings(PRIVATE_IMPORT_STORAGE_ROOT=str(root)):
                storage_key = store_artifact(
                    batch_id="00000000-0000-0000-0000-000000000001",
                    content_sha256=digest,
                    content=content,
                )
                self.assertEqual(read_artifact(storage_key), content)
                with self.assertRaises(ArtifactValidationError):
                    read_artifact("../outside.bin")
                if os.name != "nt":
                    self.assertEqual((root / "imports").stat().st_mode & 0o777, 0o700)
                    self.assertEqual(
                        (root / storage_key).stat().st_mode & 0o777,
                        0o600,
                    )

    def test_executables_and_mismatched_content_are_rejected(self) -> None:
        rejected = (
            ("program.exe", b"MZbinary", "application/octet-stream"),
            ("archive.json", b"PK\x03\x04bytes", "application/json"),
            ("history.pdf", b"not-a-pdf", "application/pdf"),
        )
        for filename, content, mime in rejected:
            with self.subTest(filename=filename), self.assertRaises(ArtifactValidationError):
                validate_artifact(filename=filename, content=content, declared_mime=mime)


class SecurityHeadersAndRateLimitTests(TestCase):
    def test_security_headers_and_cors_allowlist_are_explicit(self) -> None:
        client = Client()
        expected_development_origins = (
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3100",
            "http://127.0.0.1:3100",
        )
        self.assertEqual(_default_web_origins(debug=False), "")
        self.assertEqual(
            _default_web_origins(debug=True).split(","), list(expected_development_origins)
        )
        self.assertTrue(set(expected_development_origins).issubset(settings.CSRF_TRUSTED_ORIGINS))
        for origin in expected_development_origins:
            with self.subTest(origin=origin):
                response = client.get("/api/v1/health/live", HTTP_ORIGIN=origin)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Access-Control-Allow-Origin"], origin)
                self.assertIn("script-src 'self'", response["Content-Security-Policy"])
                self.assertEqual(
                    response["Permissions-Policy"], "camera=(), microphone=(), geolocation=()"
                )
                self.assertEqual(response["Cross-Origin-Opener-Policy"], "same-origin")
                self.assertEqual(response["Cross-Origin-Resource-Policy"], "same-origin")
                self.assertIn("Idempotency-Key", response["Access-Control-Allow-Headers"])

    @override_settings(API_MUTATION_RATE_LIMIT_PER_MINUTE=1)  # type: ignore[untyped-decorator]
    def test_state_changing_api_requests_share_a_database_rate_limit(self) -> None:
        client = Client(enforce_csrf_checks=True)
        first = client.post("/api/v1/history/attempts", {}, content_type="application/json")
        second = client.post("/api/v1/history/attempts", {}, content_type="application/json")
        self.assertEqual(first.status_code, 403)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second["Retry-After"], "60")


class AuditBulkMutationSecurityTests(TestCase):
    def test_non_postgres_orm_bulk_mutation_is_blocked_before_sql(self) -> None:
        if connection.vendor == "postgresql":
            self.skipTest("PostgreSQL trigger coverage lives in test_identity_security")
        event = AuditEvent.objects.create(action="SECURITY_TEST")
        with self.assertRaises(AuditEventImmutableError):
            AuditEvent.objects.filter(pk=event.pk).update(action="tampered")
        with self.assertRaises(AuditEventImmutableError):
            AuditEvent.objects.filter(pk=event.pk).delete()
