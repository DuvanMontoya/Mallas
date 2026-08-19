from __future__ import annotations

import datetime
import json
from typing import Any

from django.core.exceptions import ValidationError
from django.test import Client, TestCase

from domain.enums import EpistemicStatus, OfferingStatus, RequirementPurpose, SectionModality
from modules.curriculum.models import Course, CourseVersion
from modules.offerings.application.importer import SourceDescriptor, import_offering_payload
from modules.offerings.models import AcademicTerm, CourseOffering, Section
from modules.planning.models import PlannedCourse, PlanScenario, ScenarioAuditProjection
from modules.rules.models import Requirement
from modules.student_records.models import CourseAttempt
from tests.factories import foundation


class PlanningScenarioApiTests(TestCase):
    def setUp(self) -> None:
        self.context = foundation(suffix="-planning")
        self.institution = self.context["institution"]
        self.campus = self.context["campus"]
        self.user = self.context["user"]
        self.enrollment = self.context["enrollment"]
        self.revision = self.context["revision"]
        self.base_version = self.context["course_version"]
        self.term_one = self.context["term"]
        self.term_two = AcademicTerm.objects.create(
            institution=self.institution,
            campus=self.campus,
            code="2026-2-planning",
            starts_at=datetime.datetime(2026, 7, 1, tzinfo=datetime.UTC),
            ends_at=datetime.datetime(2026, 12, 31, tzinfo=datetime.UTC),
        )
        self.client = Client()
        self.client.force_login(self.user)

    def _json(
        self, method: str, path: str, payload: dict[str, Any] | None = None, **kwargs: Any
    ) -> Any:
        body = json.dumps(payload) if payload is not None else None
        return getattr(self.client, method.lower())(
            path, data=body, content_type="application/json", **kwargs
        )

    def _course(self, code: str, *, credits: int | None = 3) -> CourseVersion:
        course = Course.objects.create(institution=self.institution, code=code)
        return CourseVersion.objects.create(
            course=course,
            name=f"{code} course",
            credits=credits,
            valid_from=datetime.date(2023, 1, 1),
        )

    def _requirement(self, course: CourseVersion, ast: dict[str, Any], code: str) -> None:
        Requirement.objects.create(
            revision=self.revision,
            owner_type="COURSE",
            owner_id=course.course_id,
            code=code,
            purpose=RequirementPurpose.ENROLLMENT_PREREQUISITE.value,
            ast=ast,
            epistemic_status=EpistemicStatus.VERIFIED.value,
        )

    def _create_scenario(self, name: str = "Ruta base") -> dict[str, Any]:
        response = self._json(
            "post",
            "/api/v1/scenarios",
            {
                "name": name,
                "enrollment_id": str(self.enrollment.pk),
                "target_term_id": str(self.term_two.pk),
                "preferences": {
                    "max_credits_per_term": 12,
                    "min_credits_per_term": 3,
                    "unavailable_weekdays": [6],
                },
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def _add_course(
        self,
        scenario: dict[str, Any],
        course_version: CourseVersion,
        term: AcademicTerm,
        *,
        section_id: str | None = None,
    ) -> dict[str, Any]:
        response = self._json(
            "post",
            f"/api/v1/scenarios/{scenario['id']}/courses",
            {
                "course_version_id": str(course_version.pk),
                "term_id": str(term.pk),
                "section_id": section_id,
            },
            HTTP_IF_MATCH=f'"{scenario["version"]}"',
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_scenario_is_private_versioned_and_projects_without_mutating_history(self) -> None:
        before_attempts = CourseAttempt.objects.filter(enrollment=self.enrollment).count()
        scenario = self._create_scenario()

        self.assertFalse(scenario["sharing_enabled"])
        self.assertIsNone(scenario["share_token"])
        self.assertEqual(scenario["preferences"]["max_credits_per_term"], 12)
        self.assertTrue(scenario["audit_projection"]["payload"]["projection"])
        self.assertTrue(ScenarioAuditProjection.objects.filter(scenario_id=scenario["id"]).exists())
        self.assertEqual(
            CourseAttempt.objects.filter(enrollment=self.enrollment).count(), before_attempts
        )

        changed = self._add_course(scenario, self.base_version, self.term_two)
        self.assertEqual(len(changed["planned_courses"]), 1)
        self.assertEqual(
            changed["planned_courses"][0]["course_code"], self.base_version.course.code
        )
        self.assertGreater(changed["version"], scenario["version"])
        self.assertEqual(
            CourseAttempt.objects.filter(enrollment=self.enrollment).count(), before_attempts
        )

        listed = self.client.get("/api/v1/scenarios")
        self.assertEqual(listed.status_code, 200, listed.content)
        self.assertEqual([item["id"] for item in listed.json()["items"]], [scenario["id"]])

        stale = self._json(
            "patch",
            f"/api/v1/scenarios/{scenario['id']}",
            {"name": "stale edit"},
            HTTP_IF_MATCH='"1"',
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["code"], "STALE_RESOURCE")

    def test_pending_curriculum_rejects_scenario_without_null_dereference(self) -> None:
        self.enrollment.status = "NEEDS_REVIEW"
        self.enrollment.plan = None
        self.enrollment.revision_basis = None
        self.enrollment.review_reasons = ["CURRICULUM_ASSIGNMENT"]
        self.enrollment.save(
            update_fields=(
                "status",
                "plan",
                "revision_basis",
                "review_reasons",
                "updated_at",
            )
        )
        response = self._json(
            "post",
            "/api/v1/scenarios",
            {
                "name": "No puede crearse",
                "enrollment_id": str(self.enrollment.pk),
                "target_term_id": str(self.term_two.pk),
                "preferences": {},
            },
        )
        self.assertEqual(response.status_code, 422, response.content)
        self.assertEqual(response.json()["code"], "ENROLLMENT_NEEDS_REVIEW")
        self.assertFalse(PlanScenario.objects.filter(enrollment=self.enrollment).exists())

    def test_prerequisite_ordering_and_same_term_corequisite_are_explicit(self) -> None:
        prerequisite = self._course("STAT201-PLANNING")
        corequisite = self._course("STAT202-PLANNING")
        self._requirement(
            prerequisite,
            {"type": "COURSE_PASSED", "course_code": self.base_version.course.code},
            "PREREQ_STAT201",
        )
        self._requirement(
            corequisite,
            {"type": "COREQUISITE", "course_code": self.base_version.course.code},
            "COREQ_STAT202",
        )
        scenario = self._create_scenario("Prerequisitos")
        scenario = self._add_course(scenario, self.base_version, self.term_one)
        scenario = self._add_course(scenario, prerequisite, self.term_one)
        scenario = self._add_course(scenario, corequisite, self.term_one)

        warnings = scenario["validation"]["warnings"]
        warning_codes = {warning["code"] for warning in warnings}
        self.assertIn("PREREQUISITE_BLOCKED", warning_codes)
        prerequisite_row = next(
            row
            for row in scenario["validation"]["courses"]
            if row["course_code"] == prerequisite.course.code
        )
        corequisite_row = next(
            row
            for row in scenario["validation"]["courses"]
            if row["course_code"] == corequisite.course.code
        )
        self.assertEqual(prerequisite_row["prerequisite_state"], "UNSATISFIED")
        self.assertIn("PREREQUISITE_ORDERING", prerequisite_row["reasons"][0])
        self.assertEqual(corequisite_row["prerequisite_state"], "SATISFIED")
        self.assertNotIn("COREQUISITE_MISSING", " ".join(corequisite_row["reasons"]))

    def test_offering_conflict_and_unknown_states_are_visible(self) -> None:
        first = self._course("STAT301-PLANNING")
        second = self._course("STAT302-PLANNING")
        payload = {
            "schema_version": "offerings/1.0.0",
            "term": {
                "code": self.term_one.code,
                "starts_at": "2026-01-01T00:00:00Z",
                "ends_at": "2026-06-30T23:59:59Z",
                "status": "OPEN",
            },
            "offerings": [
                {
                    "course_code": first.course.code,
                    "status": "PUBLISHED",
                    "sections": [
                        {
                            "group_code": "1",
                            "modality": SectionModality.IN_PERSON.value,
                            "meetings": [
                                {"day_of_week": 0, "starts_at": "08:00", "ends_at": "10:00"}
                            ],
                        }
                    ],
                },
                {
                    "course_code": second.course.code,
                    "status": "PUBLISHED",
                    "sections": [
                        {
                            "group_code": "1",
                            "modality": SectionModality.IN_PERSON.value,
                            "meetings": [
                                {"day_of_week": 0, "starts_at": "09:00", "ends_at": "11:00"}
                            ],
                        }
                    ],
                },
            ],
        }
        result = import_offering_payload(
            payload,
            institution=self.institution,
            campus=self.campus,
            descriptor=SourceDescriptor(
                key="fixture.planning.offerings",
                name="Planning fixture",
                url="https://example.test/planning-offerings.json",
            ),
            captured_at=datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC),
        )
        sections = list(
            Section.objects.filter(offering__term_id=result.term_id)
            .select_related("offering__course_version")
            .order_by("offering__course_version__course__code")
        )
        scenario = self._create_scenario("Horarios")
        scenario = self._add_course(scenario, first, self.term_one, section_id=str(sections[0].pk))
        scenario = self._add_course(scenario, second, self.term_one, section_id=str(sections[1].pk))
        warning_codes = {warning["code"] for warning in scenario["validation"]["warnings"]}
        self.assertIn("SCHEDULE_CONFLICT", warning_codes)
        self.assertNotIn("OFFERING_UNKNOWN", warning_codes)

        unknown_term = self.term_two
        scenario = self._add_course(scenario, self.base_version, unknown_term)
        warning_codes = {warning["code"] for warning in scenario["validation"]["warnings"]}
        self.assertIn("OFFERING_UNKNOWN", warning_codes)

    def test_lock_duplicate_compare_archive_and_redacted_share_view(self) -> None:
        scenario = self._create_scenario("Original")
        scenario = self._add_course(scenario, self.base_version, self.term_one)
        planned = scenario["planned_courses"][0]
        locked = self._json(
            "patch",
            f"/api/v1/scenarios/{scenario['id']}/courses/{planned['id']}",
            {"is_locked": True},
            HTTP_IF_MATCH=f'"{scenario["version"]}"',
        )
        self.assertEqual(locked.status_code, 200, locked.content)
        locked_scenario = locked.json()
        move_locked = self._json(
            "patch",
            f"/api/v1/scenarios/{scenario['id']}/courses/{planned['id']}",
            {"term_id": str(self.term_two.pk)},
            HTTP_IF_MATCH=f'"{locked_scenario["version"]}"',
        )
        self.assertEqual(move_locked.status_code, 409)
        self.assertEqual(move_locked.json()["code"], "PLANNED_COURSE_LOCKED")

        duplicate = self._json(
            "post",
            f"/api/v1/scenarios/{scenario['id']}/duplicate",
            {"name": "Comparación"},
        )
        self.assertEqual(duplicate.status_code, 201, duplicate.content)
        duplicate_payload = duplicate.json()
        self.assertFalse(duplicate_payload["sharing_enabled"])
        self.assertFalse(duplicate_payload["planned_courses"][0]["is_locked"])

        compare = self.client.get(
            "/api/v1/scenarios/compare",
            {"left_id": scenario["id"], "right_id": duplicate_payload["id"]},
        )
        self.assertEqual(compare.status_code, 200, compare.content)
        self.assertEqual(compare.json()["unchanged"], [self.base_version.course.code])

        share = self._json(
            "patch",
            f"/api/v1/scenarios/{scenario['id']}",
            {"sharing_enabled": True},
            HTTP_IF_MATCH=f'"{locked_scenario["version"]}"',
        )
        self.assertEqual(share.status_code, 200, share.content)
        share_token = share.json()["share_token"]
        public = self.client.get(f"/api/v1/shared/scenarios/{share_token}")
        self.assertEqual(public.status_code, 200, public.content)
        public_payload = public.json()
        self.assertEqual(
            public_payload["privacy"],
            "No incluye enrollment, estudiante, historial ni auditoría personal.",
        )
        self.assertNotIn("enrollment_id", public_payload)
        self.assertNotIn("audit_projection", public_payload)
        self.assertNotIn("share_token", public_payload)

        unshare = self._json(
            "patch",
            f"/api/v1/scenarios/{scenario['id']}",
            {"sharing_enabled": False},
            HTTP_IF_MATCH=f'"{share.json()["version"]}"',
        )
        self.assertEqual(unshare.status_code, 200, unshare.content)
        self.assertIsNone(unshare.json()["share_token"])
        self.assertEqual(
            self.client.get(f"/api/v1/shared/scenarios/{share_token}").status_code, 404
        )

        archive = self._json(
            "post",
            f"/api/v1/scenarios/{scenario['id']}/archive",
            HTTP_IF_MATCH=f'"{unshare.json()["version"]}"',
        )
        self.assertEqual(archive.status_code, 200, archive.content)
        self.assertEqual(archive.json()["status"], "ARCHIVED")
        active = self.client.get("/api/v1/scenarios")
        self.assertEqual(active.status_code, 200)
        self.assertEqual([item["name"] for item in active.json()["items"]], ["Comparación"])

    def test_institution_and_owner_scoping_are_enforced(self) -> None:
        scenario = self._create_scenario("Privado")
        other = foundation(suffix="-planning-other")
        other_client = Client()
        other_client.force_login(other["user"])
        detail = other_client.get(f"/api/v1/scenarios/{scenario['id']}")
        self.assertEqual(detail.status_code, 403, detail.content)
        public = self.client.get(f"/api/v1/shared/scenarios/{scenario['id']}")
        self.assertEqual(public.status_code, 404)


class PlanningModelInvariantTests(TestCase):
    def test_section_and_offering_invariants_are_enforced_before_persistence(self) -> None:
        context = foundation(suffix="-planning-model")
        other_version = CourseVersion.objects.create(
            course=context["course"],
            name="Future version",
            credits=4,
            valid_from=datetime.date(2027, 1, 1),
        )
        offering = CourseOffering.objects.create(
            course_version=context["course_version"],
            term=context["term"],
            status=OfferingStatus.PUBLISHED.value,
        )
        section = Section.objects.create(
            offering=offering,
            group_code="1",
            modality=SectionModality.IN_PERSON.value,
        )
        scenario = PlanScenario.objects.create(
            enrollment=context["enrollment"],
            created_by=context["user"],
            name="Invariant",
        )
        item = PlannedCourse(
            scenario=scenario,
            course_version=other_version,
            term=context["term"],
            section=section,
        )
        with self.assertRaises(ValidationError):
            item.full_clean()
