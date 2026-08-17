from __future__ import annotations

import datetime
from typing import Any

from django.test import TestCase

from domain.enums import EpistemicStatus, RequirementPurpose
from domain.rules import AuditContext, RevisionFacts, evaluate_rule, parse_rule, serialize_rule
from modules.curriculum.models import Course, CourseVersion
from modules.rules.models import Requirement
from tests.factories import foundation


class MultiProgramArchitectureTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.statistics = foundation(suffix="-multi-statistics")
        cls.computer_science = foundation(suffix="-multi-computer-science")
        cls.computer_science["program"].code = "COMP"
        cls.computer_science["program"].name = "Computer Science"
        cls.computer_science["program"].degree_name = "Computer Scientist"
        cls.computer_science["program"].save(update_fields=["code", "name", "degree_name"])
        cls.computer_science["plan"].code = "COMP-2026"
        cls.computer_science["plan"].title = "Synthetic Computer Science Plan"
        cls.computer_science["plan"].save(update_fields=["code", "title"])

    def _requirement(self, context: dict[str, Any], *, course_code: str) -> Requirement:
        rule = {
            "type": "ALL",
            "children": [
                {"type": "COURSE_PASSED", "course_code": course_code},
                {"type": "CREDITS_IN_GROUP", "group": "CORE", "operator": ">=", "value": 4},
            ],
        }
        return Requirement.objects.create(
            revision=context["revision"],
            owner_type="COURSE",
            owner_id=context["course"].pk,
            code="GENERIC-PREREQUISITE",
            purpose=RequirementPurpose.ENROLLMENT_PREREQUISITE.value,
            ast=rule,
            epistemic_status=EpistemicStatus.VERIFIED.value,
        )

    def test_institutions_and_programs_are_isolated_without_engine_forks(self) -> None:
        statistics_course = self.statistics["course"]
        computer_course = Course.objects.create(
            institution=self.computer_science["institution"], code="COMP201"
        )
        computer_version = CourseVersion.objects.create(
            course=computer_course,
            name="Algorithms",
            credits=4,
            valid_from=datetime.date(2026, 1, 1),
        )

        statistics_requirement = self._requirement(
            self.statistics, course_code=statistics_course.code
        )
        computer_requirement = self._requirement(
            {**self.computer_science, "course": computer_course}, course_code=computer_course.code
        )

        self.assertEqual(statistics_requirement.revision_id, self.statistics["revision"].pk)
        self.assertEqual(computer_requirement.revision_id, self.computer_science["revision"].pk)
        self.assertEqual(
            Requirement.objects.filter(revision=self.statistics["revision"]).count(), 1
        )
        self.assertEqual(
            Requirement.objects.filter(revision=self.computer_science["revision"]).count(), 1
        )
        self.assertEqual(
            statistics_requirement.ast["children"][0]["course_code"], statistics_course.code
        )
        self.assertEqual(
            computer_requirement.ast["children"][0]["course_code"], computer_version.course.code
        )
        self.assertNotEqual(
            self.statistics["institution"].pk, self.computer_science["institution"].pk
        )
        self.assertNotEqual(self.statistics["program"].code, self.computer_science["program"].code)

    def test_same_ast_round_trip_and_evaluation_apply_to_both_programs(self) -> None:
        for context in (self.statistics, self.computer_science):
            course_code = context["course"].code
            payload = {
                "type": "ALL",
                "children": [
                    {"type": "COURSE_PASSED", "course_code": course_code},
                    {"type": "CREDITS_IN_GROUP", "group": "CORE", "operator": ">=", "value": 4},
                ],
            }
            parsed = parse_rule(payload)
            round_tripped = parse_rule(serialize_rule(parsed))
            result = evaluate_rule(
                round_tripped,
                AuditContext(
                    revision=RevisionFacts(
                        total_credits=context["revision"].total_required_credits,
                        group_required_credits={"CORE": 4},
                    ),
                    passed_courses=frozenset({course_code}),
                    group_credits={"CORE": 4},
                ),
            )
            self.assertEqual(result.status.value, "SATISFIED")
            self.assertEqual(serialize_rule(parsed), serialize_rule(round_tripped))
