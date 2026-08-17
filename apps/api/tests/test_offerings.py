from __future__ import annotations

import datetime
from unittest.mock import patch

from django.test import Client, TestCase

from domain.enums import OfferingStatus, UserRole
from domain.offerings.schedule import MeetingWindow, evaluate_schedule
from modules.curriculum.models import Course, CourseVersion, CurriculumRevision
from modules.governance.models import SourceSnapshot
from modules.identity.models import RoleAssignment
from modules.offerings.application.importer import (
    SourceDescriptor,
    import_offering_payload,
)
from modules.offerings.models import AcademicTerm, CourseOffering
from tests.factories import foundation


def offering_payload(*, course_code: str = "STAT101") -> dict[str, object]:
    return {
        "schema_version": "offerings/1.0.0",
        "term": {
            "code": "2026-1",
            "starts_at": "2026-01-01T00:00:00Z",
            "ends_at": "2026-06-30T23:59:59Z",
            "status": "OPEN",
        },
        "offerings": [
            {
                "course_code": course_code,
                "status": "PUBLISHED",
                "sections": [
                    {
                        "group_code": "1",
                        "modality": "IN_PERSON",
                        "meetings": [
                            {
                                "day_of_week": 0,
                                "starts_at": "08:00",
                                "ends_at": "10:00",
                                "timezone": "America/Bogota",
                            }
                        ],
                    },
                    {
                        "group_code": "2",
                        "modality": "HYBRID",
                        "meetings": [
                            {
                                "day_of_week": 0,
                                "starts_at": "09:00",
                                "ends_at": "11:00",
                                "timezone": "America/Bogota",
                            }
                        ],
                    },
                ],
            }
        ],
    }


class OfferingDomainTests(TestCase):
    def test_conflict_detection_respects_boundaries_and_partial_dates(self) -> None:
        base = MeetingWindow(
            meeting_id="m1",
            section_id="s1",
            day_of_week=0,
            starts_at=datetime.time(8),
            ends_at=datetime.time(10),
            timezone="America/Bogota",
        )
        touching = MeetingWindow(
            meeting_id="m2",
            section_id="s2",
            day_of_week=0,
            starts_at=datetime.time(10),
            ends_at=datetime.time(11),
            timezone="America/Bogota",
        )
        partial = MeetingWindow(
            meeting_id="m3",
            section_id="s3",
            day_of_week=0,
            starts_at=datetime.time(9),
            ends_at=datetime.time(11),
            timezone="America/Bogota",
            starts_on=datetime.date(2026, 2, 2),
            ends_on=datetime.date(2026, 2, 8),
        )

        touching_result = evaluate_schedule(
            [base, touching],
            term_start=datetime.date(2026, 1, 1),
            term_end=datetime.date(2026, 6, 30),
        )
        partial_result = evaluate_schedule(
            [base, partial],
            term_start=datetime.date(2026, 1, 1),
            term_end=datetime.date(2026, 6, 30),
        )

        self.assertEqual(touching_result.state, "SCHEDULABLE")
        self.assertEqual(partial_result.state, "CONFLICT")
        self.assertEqual(partial_result.conflicts[0].occurrence_date, datetime.date(2026, 2, 2))

    def test_invalid_timezone_is_unknown_not_free(self) -> None:
        meeting = MeetingWindow(
            meeting_id="m1",
            section_id="s1",
            day_of_week=0,
            starts_at=datetime.time(8),
            ends_at=datetime.time(10),
            timezone="Not/A_Timezone",
        )

        result = evaluate_schedule(
            [meeting], term_start=datetime.date(2026, 1, 1), term_end=datetime.date(2026, 6, 30)
        )

        self.assertEqual(result.state, "UNKNOWN")
        self.assertIn("timezone", result.unknown_reasons[0])


class OfferingImportAndApiTests(TestCase):
    def setUp(self) -> None:
        self.context = foundation(suffix="-offerings")
        self.institution = self.context["institution"]
        self.user = self.context["user"]
        self.enrollment = self.context["enrollment"]
        self.descriptor = SourceDescriptor(
            key="fixture.offerings",
            name="Fixture public offering export",
            url="https://example.test/offerings.json",
        )
        self.client = Client()

    def test_import_is_idempotent_and_keeps_curriculum_revision_independent(self) -> None:
        revision_count = CurriculumRevision.objects.count()

        first = import_offering_payload(
            offering_payload(course_code=self.context["course"].code),
            institution=self.institution,
            campus=self.context["campus"],
            descriptor=self.descriptor,
            captured_at=datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC),
        )
        second = import_offering_payload(
            offering_payload(course_code=self.context["course"].code),
            institution=self.institution,
            campus=self.context["campus"],
            descriptor=self.descriptor,
            captured_at=datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC),
        )

        self.assertEqual(first.offerings_created, 1)
        self.assertEqual(first.sections_created, 2)
        self.assertEqual(first.meetings_created, 2)
        self.assertEqual(second.offerings_created, 0)
        self.assertEqual(second.offerings_updated, 1)
        self.assertEqual(second.sections_updated, 2)
        self.assertEqual(CourseOffering.objects.count(), 1)
        self.assertEqual(CurriculumRevision.objects.count(), revision_count)
        self.assertEqual(first.source_snapshot_id, second.source_snapshot_id)

        response = self.client.get("/api/v1/offerings?term_code=2026-1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["offerings"][0]["offered_state"], "OFFERED")
        self.assertEqual(payload["offerings"][0]["eligibility_state"], "NOT_ASSESSED")
        self.assertEqual(payload["offerings"][0]["source"]["sha256"], first.source_sha256)
        self.assertEqual(payload["offerings"][0]["sections"][0]["capacity"]["state"], "UNKNOWN")
        self.assertIn("CAPACITY_NOT_REAL_TIME", payload["warnings"])

        section_ids = [section["id"] for section in payload["offerings"][0]["sections"]]
        conflict_response = self.client.get(
            "/api/v1/offerings/schedule",
            {"term_code": "2026-1", "section_ids": ",".join(section_ids)},
        )
        self.assertEqual(conflict_response.status_code, 200)
        self.assertEqual(conflict_response.json()["state"], "CONFLICT")
        conflicts = conflict_response.json()["conflicts"]
        self.assertGreater(len(conflicts), 0)
        self.assertEqual(conflicts[0]["occurrence_date"], "2026-01-05")

    def test_offered_and_eligibility_are_independent_states(self) -> None:
        other_course = Course.objects.create(institution=self.institution, code="STAT102-offerings")
        other_version = CourseVersion.objects.create(
            course=other_course,
            name="Second Statistics Course",
            credits=3,
            valid_from=datetime.date(2023, 1, 1),
        )
        import_offering_payload(
            offering_payload(course_code=self.context["course"].code),
            institution=self.institution,
            campus=self.context["campus"],
            descriptor=self.descriptor,
        )
        term = AcademicTerm.objects.get(institution=self.institution, code="2026-1")
        CourseOffering.objects.create(
            course_version=other_version,
            term=term,
            status=OfferingStatus.CANCELLED.value,
        )
        eligibility = {
            "course_options": [
                {"code": self.context["course"].code, "eligibility": "BLOCKED", "reasons": []},
                {"code": "STAT102-offerings", "eligibility": "ELIGIBLE", "reasons": []},
            ]
        }
        with patch(
            "modules.offerings.application.services.build_academic_overview",
            return_value=eligibility,
        ):
            response = self.client.get(
                f"/api/v1/offerings?term_code=2026-1&enrollment_id={self.enrollment.pk}"
            )

        self.assertEqual(response.status_code, 200)
        rows = {item["course_code"]: item for item in response.json()["offerings"]}
        self.assertEqual(rows[self.context["course"].code]["offered_state"], "OFFERED")
        self.assertEqual(rows[self.context["course"].code]["eligibility_state"], "BLOCKED")
        self.assertEqual(rows["STAT102-offerings"]["offered_state"], "NOT_OFFERED")
        self.assertEqual(rows["STAT102-offerings"]["eligibility_state"], "ELIGIBLE")

    def test_term_crud_requires_scoped_role_and_does_not_publish_curriculum(self) -> None:
        imported = import_offering_payload(
            offering_payload(course_code=self.context["course"].code),
            institution=self.institution,
            campus=self.context["campus"],
            descriptor=self.descriptor,
            captured_at=datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC),
        )
        self.assertTrue(SourceSnapshot.objects.filter(pk=imported.source_snapshot_id).exists())
        RoleAssignment.objects.create(
            user=self.user,
            role=UserRole.ADMIN.value,
            institution=self.institution,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/v1/academic-terms",
            data={
                "institution_id": str(self.institution.pk),
                "campus_id": str(self.context["campus"].pk),
                "code": "2027-1",
                "starts_at": "2027-01-01T00:00:00Z",
                "ends_at": "2027-06-30T23:59:59Z",
                "status": "PLANNED",
                "source_snapshot_id": str(imported.source_snapshot_id),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        term_id = response.json()["id"]
        patch_response = self.client.patch(
            f"/api/v1/academic-terms/{term_id}",
            data={"status": "OPEN"},
            content_type="application/json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["status"], "OPEN")
        self.assertEqual(patch_response.json()["source"]["sha256"], imported.source_sha256)
        clear_source_response = self.client.patch(
            f"/api/v1/academic-terms/{term_id}",
            data={"source_snapshot_id": None},
            content_type="application/json",
        )
        self.assertEqual(clear_source_response.status_code, 200)
        self.assertEqual(clear_source_response.json()["source"]["freshness"], "UNKNOWN")
        self.assertEqual(CurriculumRevision.objects.count(), 1)
