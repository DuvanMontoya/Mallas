from __future__ import annotations

import json
from pathlib import Path

from django.test import SimpleTestCase
from hypothesis import given, settings
from hypothesis import strategies as st

from domain.audit import (
    AcademicExceptionFact,
    AcademicRecord,
    AuditContext,
    AuditInput,
    CurriculumGroup,
    MembershipSnapshot,
    RevisionSnapshot,
    audit_degree,
    build_credit_ledger,
    revision_snapshot_from_baseline,
)
from domain.rules import EvaluationStatus

ROOT = Path(__file__).resolve().parents[3]
BASELINE = (
    ROOT
    / "data"
    / "curricula"
    / "unal"
    / "bogota"
    / "estadistica"
    / "2514"
    / "plan_2514_acuerdo_496_2023.json"
)
GOLDEN = ROOT / "data" / "fixtures" / "golden_degree_audit_cases.json"


class DegreeAuditTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        cls.revision = revision_snapshot_from_baseline(cls.baseline)

    def test_four_credit_course_does_not_double_count_or_reassign_excess(self) -> None:
        revision = RevisionSnapshot(
            revision_id="r",
            content_hash="hash",
            total_required_credits=3,
            components={"FOUNDATION": 3},
            groups={
                "PROGRAMMING": CurriculumGroup(
                    code="PROGRAMMING",
                    component="FOUNDATION",
                    label="Programming",
                    required_credits=3,
                )
            },
            course_credits={"A": 4},
            memberships=(MembershipSnapshot("A", "PROGRAMMING", "ELECTIVE_OPTION"),),
        )
        result = audit_degree(
            AuditInput(revision=revision, history=(AcademicRecord("A", "PASSED", "a", 4),))
        )
        self.assertEqual(result.status, EvaluationStatus.SATISFIED)
        self.assertEqual(result.earned_credits, 4)
        self.assertEqual(result.applied_credits, 3)
        self.assertEqual(result.unapplied_credits, 1)
        self.assertEqual(len(result.ledger.allocations), 1)

    def test_repeated_attempts_are_counted_once(self) -> None:
        revision = RevisionSnapshot(
            revision_id="r",
            content_hash="hash",
            total_required_credits=4,
            components={"FOUNDATION": 4},
            groups={"G": CurriculumGroup("G", "FOUNDATION", "G", 4)},
            course_credits={"A": 4},
            memberships=(MembershipSnapshot("A", "G", "MANDATORY"),),
            mandatory_courses_by_group={"G": frozenset({"A"})},
        )
        ledger = build_credit_ledger(
            AuditInput(
                revision=revision,
                history=(
                    AcademicRecord("A", "FAILED", "failed", 0),
                    AcademicRecord("A", "PASSED", "passed", 4),
                    AcademicRecord("A", "PASSED", "passed-2", 4),
                ),
            )
        )
        self.assertEqual(ledger.total_earned_credits, 4)
        self.assertEqual(ledger.total_applied_credits, 4)
        self.assertIn("duplicate_passed_attempts:A:count=2", ledger.warnings)

    def test_plan_complete_fixture_and_material_unknown(self) -> None:
        fixture = json.loads(GOLDEN.read_text(encoding="utf-8"))
        for case in fixture["cases"]:
            if case.get("history_mode") == "all_courses_with_credits":
                history = tuple(
                    AcademicRecord(
                        course_code=code,
                        status="PASSED",
                        attempt_id=f"attempt-{code}",
                        credits_earned=credits,
                    )
                    for code, credits in self.revision.course_credits.items()
                    if credits is not None
                )
            else:
                history = tuple(AcademicRecord(**record) for record in case.get("history", []))
            result = audit_degree(
                AuditInput(
                    revision=self.revision,
                    history=history,
                    external_requirements=case.get("external_requirements", {}),
                )
            )
            self.assertEqual(result.status.value, case["expected"], case["id"])
            self.assertEqual(result.required_credits, case.get("assert_required_credits", 141))
            if "assert_applied_credits" in case:
                self.assertEqual(result.applied_credits, case["assert_applied_credits"], case["id"])
            if "assert_earned_credits" in case:
                self.assertEqual(result.earned_credits, case["assert_earned_credits"], case["id"])
            if "assert_unapplied_credits" in case:
                self.assertEqual(
                    result.unapplied_credits, case["assert_unapplied_credits"], case["id"]
                )

    def test_same_input_produces_same_result_hash_and_explanation(self) -> None:
        input_data = AuditInput(revision=self.revision, external_requirements={})
        first = audit_degree(input_data)
        second = audit_degree(input_data)
        self.assertEqual(first.result_hash, second.result_hash)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertTrue(first.remaining_requirements)
        self.assertTrue(first.unknowns)

    def test_context_recognition_and_approved_exception_are_explicit(self) -> None:
        revision = RevisionSnapshot(
            revision_id="r",
            content_hash="hash",
            total_required_credits=4,
            components={"FOUNDATION": 4},
            groups={"G": CurriculumGroup("G", "FOUNDATION", "G", 4)},
            course_credits={"A": 4},
            memberships=(MembershipSnapshot("A", "G", "MANDATORY"),),
            mandatory_courses_by_group={"G": frozenset({"A"})},
        )
        recognized_input = AuditInput(
            revision=revision,
            recognized_courses=frozenset({"A"}),
            recognized_credits={"A": 3},
            recognitions={"A": frozenset({"TRANSFER:SOURCE-A"})},
        )
        context = AuditContext.from_input(recognized_input)
        self.assertEqual(context.passed_courses, frozenset({"A"}))
        self.assertEqual(build_credit_ledger(context).total_earned_credits, 3)
        recognized_result = audit_degree(recognized_input)
        self.assertEqual(recognized_result.status, EvaluationStatus.UNSATISFIED)
        self.assertEqual(recognized_result.groups[0].remaining_credits, 1)

        waived_result = audit_degree(
            AuditInput(
                revision=revision,
                exceptions=(
                    AcademicExceptionFact(
                        exception_id="exception-1",
                        status="APPROVED",
                        scope={"waive_groups": ["G"]},
                    ),
                ),
            )
        )
        self.assertEqual(waived_result.status, EvaluationStatus.SATISFIED)
        self.assertTrue(waived_result.groups[0].waived)
        self.assertEqual(waived_result.applied_credits, 0)


@settings(max_examples=40, deadline=None)
@given(st.integers(min_value=0, max_value=8))
def test_ledger_never_applies_more_than_earned(credits: int) -> None:
    revision = RevisionSnapshot(
        revision_id="r",
        content_hash="hash",
        total_required_credits=3,
        components={"C": 3},
        groups={"G": CurriculumGroup("G", "C", "G", 3)},
        course_credits={"A": 4},
        memberships=(MembershipSnapshot("A", "G", "ELECTIVE_OPTION"),),
    )
    ledger = build_credit_ledger(
        AuditInput(revision=revision, history=(AcademicRecord("A", "PASSED", "a", credits),))
    )
    assert ledger.total_applied_credits <= ledger.total_earned_credits
