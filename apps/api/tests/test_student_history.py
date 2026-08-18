from __future__ import annotations

import json
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest import TestCase

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TransactionTestCase, override_settings
from django.utils import timezone
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from domain.enums import AttemptStatus, CandidateStatus, ImportStatus, ReconciliationDecision
from domain.history import HISTORY_SCHEMA_VERSION, parse_history_bytes
from modules.audit.models import DegreeAuditRun
from modules.identity.models import AuditEvent, User
from modules.imports.application.history import (
    HistoryImportError,
    confirm_history_import,
    create_history_import,
    get_import_batch_for_view,
    resolve_history_candidate,
)
from modules.imports.application.retention import (
    purge_expired_candidate_payloads,
    purge_expired_raw_artifacts,
)
from modules.imports.application.storage import ArtifactValidationError, validate_artifact
from modules.imports.models import ImportBatch, ImportEvidence
from modules.student_records.application.history import (
    HistoryMutationError,
    annul_attempt,
    create_manual_attempt,
    update_attempt,
)
from modules.student_records.models import AcademicRecognition, CourseAttempt
from tests.factories import foundation


def history_payload(*, course_code: str, term_code: str, status: str = "PASSED") -> bytes:
    return json.dumps(
        {
            "schema_version": HISTORY_SCHEMA_VERSION,
            "records": [
                {
                    "course_code": course_code,
                    "term_code": term_code,
                    "status": status,
                    "grade": "4.50",
                    "source_locator": "row:2",
                }
            ],
        }
    ).encode("utf-8")


def text_pdf_bytes(row: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 50 700 Td ({row}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class HistoryParserTests(TestCase):
    def test_json_and_csv_normalize_explicit_status_and_report_row_errors(self) -> None:
        report = parse_history_bytes(
            history_payload(course_code="STAT101", term_code="2026-1"),
            source_name="history.json",
            mime_type="application/json",
        )
        self.assertEqual(report.source_kind, "JSON_HISTORY")
        self.assertEqual(report.valid_candidates[0].normalized_payload["status"], "PASSED")
        csv_report = parse_history_bytes(
            b"course_code,term_code,status,grade\nSTAT101,2026-1,PASSED,4.5\nSTAT101,2026-1,PASSED,4.5\n",
            source_name="history.csv",
            mime_type="text/csv",
        )
        self.assertEqual(len(csv_report.candidates), 2)
        self.assertTrue(
            all(
                any(warning["code"] == "duplicate_in_file" for warning in candidate.warnings)
                for candidate in csv_report.candidates
            )
        )
        invalid = parse_history_bytes(
            b'{"schema_version":"student-history/1.0.0","records":[{"course_code":"","term_code":"2026-1","status":"GUESS"}]}',
            source_name="history.json",
            mime_type="application/json",
        )
        self.assertEqual(
            {error["code"] for error in invalid.candidates[0].errors},
            {"course_code_required", "status_invalid"},
        )

    def test_parser_discards_arbitrary_columns_before_they_can_persist(self) -> None:
        content = json.dumps(
            {
                "schema_version": HISTORY_SCHEMA_VERSION,
                "records": [
                    {
                        "course_code": "STAT101",
                        "term_code": "2026-1",
                        "status": "PASSED",
                        "grade": "4.5",
                        "student_email": "private@example.test",
                        "government_id": "123456789",
                        "nested_profile": {"address": "private"},
                    }
                ],
            }
        ).encode()

        candidate = parse_history_bytes(
            content,
            source_name="history.json",
            mime_type="application/json",
        ).candidates[0]

        self.assertEqual(
            candidate.raw_payload,
            {
                "course_code": "STAT101",
                "term_code": "2026-1",
                "status": "PASSED",
                "grade": "4.5",
            },
        )
        self.assertTrue(
            any(warning["code"] == "extra_columns_discarded" for warning in candidate.warnings)
        )

    def test_pdf_parser_creates_review_required_candidates(self) -> None:
        report = parse_history_bytes(
            text_pdf_bytes("STAT101  2026-1  PASSED  4.5  4"),
            source_name="history.pdf",
            mime_type="application/pdf",
        )
        self.assertEqual(report.source_kind, "PDF_HISTORY")
        self.assertEqual(len(report.candidates), 1)
        self.assertTrue(report.candidates[0].requires_confirmation)
        self.assertEqual(report.candidates[0].normalized_payload["source_metadata"]["page"], 1)

    def test_upload_validation_rejects_executable_and_traversal_is_not_stored(self) -> None:
        with self.assertRaises(ArtifactValidationError):
            validate_artifact(
                filename="history.exe", content=b"MZ...", declared_mime="application/octet-stream"
            )
        validated = validate_artifact(
            filename="..\\private\\history.json",
            content=b"{}",
            declared_mime="application/json",
        )
        self.assertEqual(validated.original_filename, "history.json")


class HistoryImportServiceTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self) -> None:
        self.storage_dir = Path(tempfile.mkdtemp(prefix="history-import-tests-"))
        self.settings_override = override_settings(
            PRIVATE_IMPORT_STORAGE_ROOT=str(self.storage_dir)
        )
        self.settings_override.enable()
        self.data = foundation(suffix="-history")
        self.data["revision"].total_required_credits = 4
        self.data["revision"].save(update_fields=["total_required_credits"])
        self.user: User = self.data["user"]
        self.enrollment = self.data["enrollment"]
        self.content = history_payload(
            course_code=self.data["course"].code,
            term_code=self.data["term"].code,
        )

    def tearDown(self) -> None:
        self.settings_override.disable()
        shutil.rmtree(self.storage_dir, ignore_errors=True)
        super().tearDown()

    def create_preview(
        self,
        *,
        content: bytes | None = None,
        filename: str = "history.json",
        idempotency_key: str | None = None,
    ) -> Any:
        return create_history_import(
            actor=self.user,
            enrollment_id=self.enrollment.pk,
            filename=filename,
            content=content or self.content,
            declared_mime="application/json" if filename.endswith("json") else "application/pdf",
            idempotency_key=idempotency_key,
        )

    def test_import_is_idempotent_and_confirm_recalculates_audit_with_evidence(self) -> None:
        first = self.create_preview()
        second = self.create_preview()
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(ImportBatch.objects.filter(enrollment=self.enrollment).count(), 1)
        self.assertEqual(first.batch.status, ImportStatus.PREVIEW.value)
        candidate = first.batch.candidate_records.get()
        self.assertEqual(candidate.status, CandidateStatus.RESOLVED.value)
        self.assertEqual(candidate.reconciliation.decision, ReconciliationDecision.ACCEPT.value)
        applied = confirm_history_import(actor=self.user, batch_id=first.batch.pk)
        self.assertEqual(applied.created_attempts, 1)
        self.assertEqual(applied.created_recognitions, 0)
        self.assertIsNotNone(applied.audit_run_id)
        self.assertEqual(CourseAttempt.objects.filter(import_batch=first.batch).count(), 1)
        self.assertEqual(ImportEvidence.objects.filter(batch=first.batch).count(), 1)
        self.assertEqual(DegreeAuditRun.objects.filter(enrollment=self.enrollment).count(), 1)
        self.assertEqual(first.batch.refresh_from_db(), None)
        self.assertEqual(first.batch.status, ImportStatus.APPLIED.value)
        replay = confirm_history_import(actor=self.user, batch_id=first.batch.pk)
        self.assertTrue(replay.idempotent)
        self.assertEqual(CourseAttempt.objects.filter(import_batch=first.batch).count(), 1)

    def test_idempotency_key_replays_same_upload_and_rejects_different_content(self) -> None:
        first = self.create_preview(idempotency_key="history-retry-1")
        replay = self.create_preview(idempotency_key="history-retry-1")
        self.assertTrue(first.created)
        self.assertFalse(replay.created)
        self.assertEqual(replay.batch.pk, first.batch.pk)
        self.assertEqual(ImportBatch.objects.filter(enrollment=self.enrollment).count(), 1)

        with self.assertRaises(HistoryImportError) as reused:
            self.create_preview(
                content=self.content + b"\n",
                idempotency_key="history-retry-1",
            )
        self.assertEqual(reused.exception.code, "idempotency_key_reused")

    def test_existing_conflict_requires_explicit_resolution_and_never_overwrites(self) -> None:
        create_manual_attempt(
            actor=self.user,
            enrollment_id=self.enrollment.pk,
            course_version_id=self.data["course_version"].pk,
            term_id=self.data["term"].pk,
            status=AttemptStatus.PASSED.value,
            grade="3.0",
            credits_earned=4,
        )
        preview = self.create_preview()
        candidate = preview.batch.candidate_records.get()
        self.assertEqual(candidate.status, CandidateStatus.CONFLICT.value)
        with self.assertRaises(HistoryImportError) as unresolved:
            confirm_history_import(actor=self.user, batch_id=preview.batch.pk)
        self.assertEqual(unresolved.exception.code, "preview_unresolved")
        with self.assertRaises(HistoryImportError) as no_note:
            from modules.imports.application.history import resolve_history_candidate

            resolve_history_candidate(
                actor=self.user,
                batch_id=preview.batch.pk,
                candidate_id=candidate.pk,
                decision=ReconciliationDecision.ACCEPT.value,
                note="",
            )
        self.assertEqual(no_note.exception.code, "conflict_note_required")
        from modules.imports.application.history import resolve_history_candidate

        resolve_history_candidate(
            actor=self.user,
            batch_id=preview.batch.pk,
            candidate_id=candidate.pk,
            decision=ReconciliationDecision.ACCEPT.value,
            note="Student confirmed this is a second attempt; retain the original record.",
        )
        applied = confirm_history_import(actor=self.user, batch_id=preview.batch.pk)
        self.assertEqual(applied.created_attempts, 1)
        attempts = list(
            CourseAttempt.objects.filter(
                enrollment=self.enrollment, course_version=self.data["course_version"]
            ).order_by("attempt_number")
        )
        self.assertEqual([attempt.attempt_number for attempt in attempts], [1, 2])
        self.assertEqual(str(attempts[0].grade), "3.00")

    def test_pdf_candidate_cannot_commit_until_user_resolves_it(self) -> None:
        preview = self.create_preview(
            content=text_pdf_bytes(
                f"{self.data['course'].code}  {self.data['term'].code}  PASSED  4.5  4"
            ),
            filename="history.pdf",
        )
        candidate = preview.batch.candidate_records.get()
        self.assertEqual(candidate.reconciliation.decision, ReconciliationDecision.PENDING.value)
        with self.assertRaises(HistoryImportError) as pending:
            confirm_history_import(actor=self.user, batch_id=preview.batch.pk)
        self.assertEqual(pending.exception.code, "preview_unresolved")
        resolve_history_candidate(
            actor=self.user,
            batch_id=preview.batch.pk,
            candidate_id=candidate.pk,
            decision=ReconciliationDecision.ACCEPT.value,
            note="Reviewed against the uploaded statement.",
        )
        applied = confirm_history_import(actor=self.user, batch_id=preview.batch.pk)
        self.assertEqual(applied.created_attempts, 1)

    def test_raw_payload_is_purged_after_apply_and_expired_previews_are_purgeable(self) -> None:
        preview = self.create_preview()
        candidate = preview.batch.candidate_records.get()
        self.assertTrue(candidate.raw_payload)
        applied = confirm_history_import(actor=self.user, batch_id=preview.batch.pk)
        self.assertEqual(applied.created_attempts, 1)
        candidate.refresh_from_db()
        self.assertEqual(candidate.raw_payload, {})
        self.assertIsNotNone(candidate.raw_payload_purged_at)

        second = self.create_preview(
            content=history_payload(
                course_code=self.data["course"].code,
                term_code=self.data["term"].code,
                status="FAILED",
            ),
            filename="expired.json",
        )
        expired = second.batch.candidate_records.get()
        expired.raw_payload_expires_at = timezone.now() - timedelta(seconds=1)
        expired.save(update_fields=["raw_payload_expires_at", "updated_at"])
        self.assertEqual(purge_expired_candidate_payloads(), 1)
        expired.refresh_from_db()
        self.assertEqual(expired.raw_payload, {})
        self.assertIsNotNone(expired.raw_payload_purged_at)

        artifact = second.batch.artifact
        stored_path = self.storage_dir / artifact.storage_key
        self.assertTrue(stored_path.is_file())
        artifact.content_expires_at = timezone.now() - timedelta(seconds=1)
        artifact.save(update_fields=["content_expires_at", "updated_at"])
        self.assertEqual(purge_expired_raw_artifacts(), 1)
        artifact.refresh_from_db()
        self.assertFalse(stored_path.exists())
        self.assertEqual(artifact.storage_key, "")
        self.assertIsNotNone(artifact.content_purged_at)

    @override_settings(HISTORY_PDF_PARSE_TIMEOUT_SECONDS=0.001)  # type: ignore[untyped-decorator]
    def test_pdf_parser_fails_closed_when_isolated_process_exceeds_timeout(self) -> None:
        with self.assertRaisesRegex(HistoryImportError, "time or memory budget"):
            self.create_preview(
                content=text_pdf_bytes(
                    f"{self.data['course'].code}  {self.data['term'].code}  PASSED  4.5  4"
                ),
                filename="timeout.pdf",
            )

    def test_external_course_code_creates_recognition_and_source_lineage(self) -> None:
        content = json.dumps(
            {
                "schema_version": HISTORY_SCHEMA_VERSION,
                "records": [
                    {
                        "course_code": "EXT-STAT-01",
                        "external_code": "UNIV-ABC-01",
                        "term_code": self.data["term"].code,
                        "status": "TRANSFERRED",
                        "credits_earned": 4,
                    }
                ],
            }
        ).encode()
        preview = self.create_preview(content=content)
        candidate = preview.batch.candidate_records.get()
        self.assertEqual(candidate.status, CandidateStatus.CONFLICT.value)
        from modules.imports.application.history import resolve_history_candidate

        resolve_history_candidate(
            actor=self.user,
            batch_id=preview.batch.pk,
            candidate_id=candidate.pk,
            decision=ReconciliationDecision.EXTERNAL.value,
            selected_course_version_id=self.data["course_version"].pk,
            external_code="UNIV-ABC-01",
            note="Resolution in transfer decision 2026-01.",
        )
        applied = confirm_history_import(actor=self.user, batch_id=preview.batch.pk)
        self.assertEqual(applied.created_recognitions, 1)
        self.assertEqual(AcademicRecognition.objects.filter(enrollment=self.enrollment).count(), 1)
        self.assertEqual(ImportEvidence.objects.filter(batch=preview.batch).count(), 1)

    def test_other_user_cannot_view_or_edit_batch(self) -> None:
        preview = self.create_preview()
        other = User.objects.create_user(
            email="other-history@example.test", password="safe-password"
        )
        with self.assertRaises(HistoryImportError) as view_error:
            get_import_batch_for_view(other, preview.batch.pk)
        self.assertEqual(view_error.exception.code, "history_forbidden")
        with self.assertRaises(HistoryImportError) as edit_error:
            confirm_history_import(actor=other, batch_id=preview.batch.pk)
        self.assertEqual(edit_error.exception.code, "history_forbidden")

    def test_row_errors_are_explainable_and_block_confirmation(self) -> None:
        invalid = json.dumps(
            {
                "schema_version": HISTORY_SCHEMA_VERSION,
                "records": [
                    {
                        "course_code": self.data["course"].code,
                        "term_code": self.data["term"].code,
                        "status": "NOT_A_STATUS",
                    }
                ],
            }
        ).encode()
        preview = self.create_preview(content=invalid)
        candidate = preview.batch.candidate_records.get()
        self.assertEqual(candidate.status, CandidateStatus.ERROR.value)
        self.assertEqual(candidate.parse_errors[0]["code"], "status_invalid")
        with self.assertRaises(HistoryImportError) as error:
            confirm_history_import(actor=self.user, batch_id=preview.batch.pk)
        self.assertEqual(error.exception.code, "preview_has_errors")


class ManualHistoryServiceTests(TransactionTestCase):
    def setUp(self) -> None:
        self.data = foundation(suffix="-manual")
        self.data["revision"].total_required_credits = 4
        self.data["revision"].save(update_fields=["total_required_credits"])
        self.user: User = self.data["user"]

    def test_manual_crud_is_owned_audited_and_recalculates(self) -> None:
        attempt, first_audit = create_manual_attempt(
            actor=self.user,
            enrollment_id=self.data["enrollment"].pk,
            course_version_id=self.data["course_version"].pk,
            term_id=self.data["term"].pk,
            status=AttemptStatus.PASSED.value,
            grade="4.0",
            credits_earned=4,
        )
        changed, second_audit = update_attempt(
            actor=self.user,
            attempt_id=attempt.pk,
            changes={"grade": "4.5", "notes": "Corrected from official transcript."},
        )
        self.assertEqual(changed.grade, Decimal("4.5"))
        self.assertNotEqual(first_audit, second_audit)
        annulled, third_audit = annul_attempt(actor=self.user, attempt_id=attempt.pk)
        self.assertEqual(annulled.status, AttemptStatus.ANNULLED.value)
        self.assertNotEqual(second_audit, third_audit)
        self.assertGreaterEqual(
            AuditEvent.objects.filter(
                object_type="CourseAttempt", object_id=str(attempt.pk)
            ).count(),
            3,
        )

    def test_annulled_status_requires_the_dedicated_operation(self) -> None:
        with self.assertRaises(HistoryMutationError) as create_error:
            create_manual_attempt(
                actor=self.user,
                enrollment_id=self.data["enrollment"].pk,
                course_version_id=self.data["course_version"].pk,
                term_id=self.data["term"].pk,
                status=AttemptStatus.ANNULLED.value,
            )
        self.assertEqual(create_error.exception.code, "annul_operation_required")

        attempt, _ = create_manual_attempt(
            actor=self.user,
            enrollment_id=self.data["enrollment"].pk,
            course_version_id=self.data["course_version"].pk,
            term_id=self.data["term"].pk,
            status=AttemptStatus.PASSED.value,
            credits_earned=4,
        )
        with self.assertRaises(HistoryMutationError) as update_error:
            update_attempt(
                actor=self.user,
                attempt_id=attempt.pk,
                changes={"status": AttemptStatus.ANNULLED.value},
            )
        self.assertEqual(update_error.exception.code, "annul_operation_required")

    def test_internal_attempt_credits_are_derived_from_normative_course_version(self) -> None:
        with self.assertRaises(HistoryMutationError) as inconsistent:
            create_manual_attempt(
                actor=self.user,
                enrollment_id=self.data["enrollment"].pk,
                course_version_id=self.data["course_version"].pk,
                term_id=self.data["term"].pk,
                status=AttemptStatus.PASSED.value,
                credits_earned=99,
            )
        self.assertEqual(inconsistent.exception.code, "credits_inconsistent")

        attempt, _ = create_manual_attempt(
            actor=self.user,
            enrollment_id=self.data["enrollment"].pk,
            course_version_id=self.data["course_version"].pk,
            term_id=self.data["term"].pk,
            status=AttemptStatus.PASSED.value,
        )
        self.assertEqual(attempt.credits_earned, self.data["course_version"].credits)
        changed, _ = update_attempt(
            actor=self.user,
            attempt_id=attempt.pk,
            changes={"status": AttemptStatus.FAILED.value},
        )
        self.assertEqual(changed.credits_earned, 0)

    def test_manual_update_is_not_an_idor(self) -> None:
        attempt, _ = create_manual_attempt(
            actor=self.user,
            enrollment_id=self.data["enrollment"].pk,
            course_version_id=self.data["course_version"].pk,
            term_id=self.data["term"].pk,
            status=AttemptStatus.PASSED.value,
            credits_earned=4,
        )
        other_data = foundation(suffix="-manual-other")
        with self.assertRaises(HistoryMutationError) as error:
            update_attempt(
                actor=other_data["user"],
                attempt_id=attempt.pk,
                changes={"grade": "1.0"},
            )
        self.assertEqual(error.exception.code, "history_forbidden")


class HistoryApiTests(TransactionTestCase):
    def setUp(self) -> None:
        self.client = Client(enforce_csrf_checks=True)
        self.data = foundation(suffix="-api-history")
        self.data["revision"].total_required_credits = 4
        self.data["revision"].save(update_fields=["total_required_credits"])
        self.user: User = self.data["user"]
        self.client.force_login(self.user)

    def headers(self) -> dict[str, str]:
        response = self.client.get("/api/v1/auth/csrf")
        self.assertEqual(response.status_code, 200)
        return {"HTTP_X_CSRFTOKEN": response.json()["csrf_token"]}

    def test_history_cursor_is_stable_when_a_new_attempt_is_inserted_between_pages(self) -> None:
        original = [
            CourseAttempt.objects.create(
                enrollment=self.data["enrollment"],
                course_version=self.data["course_version"],
                term=self.data["term"],
                attempt_number=attempt_number,
                status=AttemptStatus.PASSED.value,
                credits_earned=4,
            )
            for attempt_number in (1, 2, 3)
        ]
        first = self.client.get(
            "/api/v1/history/attempts",
            {
                "enrollment_id": str(self.data["enrollment"].pk),
                "limit": 2,
                "sort": "term",
            },
        )
        self.assertEqual(first.status_code, 200, first.content)
        self.assertIsNotNone(first.json()["next_cursor"])

        inserted = CourseAttempt.objects.create(
            enrollment=self.data["enrollment"],
            course_version=self.data["course_version"],
            term=self.data["term"],
            attempt_number=4,
            status=AttemptStatus.PASSED.value,
            credits_earned=4,
        )
        original[-1].status = AttemptStatus.ENROLLED.value
        original[-1].save(update_fields=["status", "updated_at"])
        second = self.client.get(
            "/api/v1/history/attempts",
            {
                "enrollment_id": str(self.data["enrollment"].pk),
                "limit": 2,
                "sort": "term",
                "cursor": first.json()["next_cursor"],
            },
        )
        self.assertEqual(second.status_code, 200, second.content)
        returned_ids = {item["id"] for item in [*first.json()["items"], *second.json()["items"]]}
        self.assertEqual(returned_ids, {str(attempt.pk) for attempt in original})
        self.assertNotIn(str(inserted.pk), returned_ids)
        self.assertIsNone(second.json()["next_cursor"])

        invalid = self.client.get(
            "/api/v1/history/attempts",
            {
                "enrollment_id": str(self.data["enrollment"].pk),
                "cursor": "tampered",
            },
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["code"], "HISTORY_CURSOR_INVALID")

    def test_api_upload_preview_confirm_and_ownership(self) -> None:
        content = history_payload(
            course_code=self.data["course"].code,
            term_code=self.data["term"].code,
        )
        response = self.client.post(
            "/api/v1/history/imports",
            {
                "enrollment_id": str(self.data["enrollment"].pk),
                "file": SimpleUploadedFile(
                    "history.json", content, content_type="application/json"
                ),
            },
            HTTP_IDEMPOTENCY_KEY="api-history-import-1",
            **self.headers(),
        )
        self.assertEqual(response.status_code, 200, response.content)
        batch_id = response.json()["id"]
        self.assertEqual(response.json()["status"], ImportStatus.PREVIEW.value)
        replay = self.client.post(
            "/api/v1/history/imports",
            {
                "enrollment_id": str(self.data["enrollment"].pk),
                "file": SimpleUploadedFile(
                    "history.json", content, content_type="application/json"
                ),
            },
            HTTP_IDEMPOTENCY_KEY="api-history-import-1",
            **self.headers(),
        )
        self.assertEqual(replay.status_code, 200, replay.content)
        self.assertEqual(replay.json()["id"], batch_id)
        self.assertFalse(replay.json()["created"])
        preview = self.client.get(f"/api/v1/history/imports/{batch_id}")
        self.assertEqual(preview.status_code, 200)
        confirm = self.client.post(
            f"/api/v1/history/imports/{batch_id}/confirm",
            {},
            HTTP_IF_MATCH=f'"{preview.json()["version"]}"',
            **self.headers(),
        )
        self.assertEqual(confirm.status_code, 200, confirm.content)
        self.assertEqual(confirm.json()["created_attempts"], 1)
        retry = self.client.post(
            f"/api/v1/history/imports/{batch_id}/confirm",
            {},
            HTTP_IF_MATCH=f'"{preview.json()["version"]}"',
            **self.headers(),
        )
        self.assertEqual(retry.status_code, 200, retry.content)
        self.assertTrue(retry.json()["idempotent"])
        self.assertEqual(CourseAttempt.objects.filter(import_batch_id=batch_id).count(), 1)
        attempts = self.client.get(
            f"/api/v1/history/attempts?enrollment_id={self.data['enrollment'].pk}"
        )
        self.assertEqual(attempts.status_code, 200)
        self.assertEqual(len(attempts.json()["items"]), 1)
        self.assertEqual(attempts.json()["total"], 1)
        self.assertTrue(AuditEvent.objects.filter(action="HISTORY_IMPORT_APPLIED").exists())

    def test_api_manual_resolution_refreshes_batch_version_before_confirm(self) -> None:
        create_manual_attempt(
            actor=self.user,
            enrollment_id=self.data["enrollment"].pk,
            course_version_id=self.data["course_version"].pk,
            term_id=self.data["term"].pk,
            status=AttemptStatus.PASSED.value,
            grade="3.0",
            credits_earned=4,
        )
        content = history_payload(
            course_code=self.data["course"].code,
            term_code=self.data["term"].code,
        )
        uploaded = self.client.post(
            "/api/v1/history/imports",
            {
                "enrollment_id": str(self.data["enrollment"].pk),
                "file": SimpleUploadedFile(
                    "manual-resolution.json", content, content_type="application/json"
                ),
            },
            HTTP_IDEMPOTENCY_KEY="api-history-manual-resolution",
            **self.headers(),
        )
        self.assertEqual(uploaded.status_code, 200, uploaded.content)
        original_version = uploaded.json()["version"]
        candidate = uploaded.json()["candidates"][0]
        resolved = self.client.post(
            f"/api/v1/history/imports/{uploaded.json()['id']}/candidates/{candidate['id']}/resolve",
            json.dumps(
                {
                    "decision": ReconciliationDecision.ACCEPT.value,
                    "selected_course_version_id": str(self.data["course_version"].pk),
                    "external_code": "",
                    "note": "Reviewed as a separate attempt.",
                }
            ),
            content_type="application/json",
            HTTP_IF_MATCH=f'"{candidate["version"]}"',
            **self.headers(),
        )
        self.assertEqual(resolved.status_code, 200, resolved.content)

        refreshed = self.client.get(f"/api/v1/history/imports/{uploaded.json()['id']}")
        self.assertEqual(refreshed.status_code, 200, refreshed.content)
        self.assertNotEqual(refreshed.json()["version"], original_version)
        self.assertEqual(refreshed.json()["unresolved_count"], 0)
        confirmed = self.client.post(
            f"/api/v1/history/imports/{uploaded.json()['id']}/confirm",
            {},
            HTTP_IF_MATCH=f'"{refreshed.json()["version"]}"',
            **self.headers(),
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.content)
        self.assertEqual(confirmed.json()["created_attempts"], 1)

    def test_api_edits_require_if_match_and_emit_etag(self) -> None:
        payload = json.dumps(
            {
                "enrollment_id": str(self.data["enrollment"].pk),
                "course_version_id": str(self.data["course_version"].pk),
                "term_id": str(self.data["term"].pk),
                "status": AttemptStatus.PASSED.value,
                "credits_earned": 4,
            }
        )
        created = self.client.post(
            "/api/v1/history/attempts",
            payload,
            content_type="application/json",
            **self.headers(),
        )
        self.assertEqual(created.status_code, 200, created.content)
        attempt_id = created.json()["id"]
        version = created.json()["version"]
        self.assertEqual(created["ETag"], f'"{version}"')

        missing = self.client.patch(
            f"/api/v1/history/attempts/{attempt_id}",
            json.dumps({"notes": "missing precondition"}),
            content_type="application/json",
            **self.headers(),
        )
        self.assertEqual(missing.status_code, 428)
        self.assertEqual(missing.json()["code"], "PRECONDITION_REQUIRED")

        updated = self.client.patch(
            f"/api/v1/history/attempts/{attempt_id}",
            json.dumps({"notes": "versioned edit"}),
            content_type="application/json",
            HTTP_IF_MATCH=version,
            **self.headers(),
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertNotEqual(updated.json()["version"], version)

        stale = self.client.patch(
            f"/api/v1/history/attempts/{attempt_id}",
            json.dumps({"notes": "stale edit"}),
            content_type="application/json",
            HTTP_IF_MATCH=version,
            **self.headers(),
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["code"], "STALE_RESOURCE")
