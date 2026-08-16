from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from django.test import SimpleTestCase
from hypothesis import given, settings
from hypothesis import strategies as st

from domain.rules import (
    AST_SCHEMA_VERSION,
    All,
    AnyOf,
    AuditContext,
    AuditRule,
    CoursePassed,
    EvaluationStatus,
    ExternalRequirement,
    RevisionFacts,
    Unknown,
    ast_hash,
    canonical_rule_json,
    direct_course_dependencies,
    evaluate_rule,
    find_requirement_cycles,
    parse_rule,
    parse_rule_document,
    serialize_rule,
    serialize_rule_document,
)
from domain.rules.ast import (
    Corequisite,
    CourseInProgress,
    CoursePassedOrInProgress,
    CreditsInComponent,
    CreditsInGroup,
    EquivalentCoursePassed,
    GroupCompleted,
    MandatoryCoursesCompleted,
    MinimumGrade,
    Not,
    PercentageOfPlan,
    TotalCredits,
)
from domain.rules.errors import RuleSchemaError

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
GOLDEN = ROOT / "data" / "fixtures" / "golden_rule_cases.json"


class RuleEngineTests(SimpleTestCase):
    def test_core_has_no_django_imports(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "apps" / "api" / "domain" / "rules").glob("*.py")
        )
        self.assertNotIn("import django", source)
        self.assertNotIn("from django", source)

    def test_all_discriminated_nodes_round_trip(self) -> None:
        nodes: list[AuditRule] = [
            All((CoursePassed("A"), Unknown("pending"))),
            AnyOf((CourseInProgress("A"), CoursePassedOrInProgress("B"))),
            Not(CoursePassed("A")),
            CoursePassed("A"),
            CourseInProgress("A"),
            CoursePassedOrInProgress("A"),
            CreditsInGroup("PROGRAMMING", ">=", 3),
            CreditsInComponent("DISCIPLINARY", ">=", 20),
            TotalCredits(">=", 141),
            PercentageOfPlan(4, 5),
            GroupCompleted("STAT_CORE"),
            MandatoryCoursesCompleted(("A", "B")),
            MinimumGrade("A", Decimal("3.5")),
            ExternalRequirement("FOREIGN_LANGUAGE_B1"),
            EquivalentCoursePassed("EQUIV_A", ("A", "B")),
            Corequisite("A"),
            Unknown("not enough evidence", "raw text"),
        ]
        for node in nodes:
            round_tripped = parse_rule(serialize_rule(node))
            self.assertEqual(ast_hash(node), ast_hash(round_tripped))
            self.assertEqual(canonical_rule_json(node), canonical_rule_json(round_tripped))

    def test_document_version_is_explicit(self) -> None:
        node = CoursePassed("A")
        document = serialize_rule_document(node)
        self.assertEqual(document["schema_version"], AST_SCHEMA_VERSION)
        self.assertEqual(parse_rule_document(document), node)
        with self.assertRaises(RuleSchemaError):
            parse_rule_document({"schema_version": "9.9.9", "rule": serialize_rule(node)})

    def test_schema_errors_reject_missing_fields_unknown_fields_and_floats(self) -> None:
        with self.assertRaises(RuleSchemaError):
            parse_rule({"type": "COURSE_PASSED"})
        with self.assertRaises(RuleSchemaError):
            parse_rule({"type": "COURSE_PASSED", "course_code": "A", "extra": True})
        with self.assertRaises(RuleSchemaError):
            parse_rule({"type": "PERCENTAGE_OF_PLAN", "numerator": 0.8, "denominator": 1})

    def test_all_any_unknown_and_not_applicable_truth_tables(self) -> None:
        satisfied = CoursePassed("SAT")
        unsatisfied = CoursePassed("NO")
        unknown = Unknown("not evidenced")
        context = AuditContext(passed_courses=frozenset({"SAT"}))
        self.assertEqual(
            evaluate_rule(All((satisfied, unknown)), context).status,
            EvaluationStatus.UNKNOWN,
        )
        self.assertEqual(
            evaluate_rule(All((unsatisfied, unknown)), context).status,
            EvaluationStatus.UNSATISFIED,
        )
        self.assertEqual(
            evaluate_rule(AnyOf((unsatisfied, unknown)), context).status,
            EvaluationStatus.UNKNOWN,
        )
        self.assertEqual(
            evaluate_rule(AnyOf((satisfied, unknown)), context).status,
            EvaluationStatus.SATISFIED,
        )
        not_applicable = AuditContext(
            not_applicable_keys=frozenset({canonical_rule_json(satisfied)})
        )
        self.assertEqual(
            evaluate_rule(satisfied, not_applicable).status,
            EvaluationStatus.NOT_APPLICABLE,
        )

    def test_exact_percentage_threshold_141(self) -> None:
        rule = PercentageOfPlan(4, 5)
        revision = RevisionFacts(total_credits=141)
        self.assertEqual(
            evaluate_rule(rule, AuditContext(revision=revision, earned_credits=112)).status,
            EvaluationStatus.UNSATISFIED,
        )
        result = evaluate_rule(rule, AuditContext(revision=revision, earned_credits=113))
        self.assertEqual(result.status, EvaluationStatus.SATISFIED)
        self.assertEqual(result.progress.required, 113)
        self.assertIn(
            "112",
            evaluate_rule(rule, AuditContext(revision=revision, earned_credits=112)).facts_used[0],
        )

    def test_leaf_contexts_and_cycle_analysis(self) -> None:
        context = AuditContext(
            revision=RevisionFacts(
                total_credits=141,
                group_required_credits={"STAT_CORE": 36},
                component_required_credits={"DISCIPLINARY": 61},
            ),
            passed_courses=frozenset({"A", "B"}),
            in_progress_courses=frozenset({"C"}),
            earned_credits=141,
            group_credits={"STAT_CORE": 36, "PROGRAMMING": 3},
            component_credits={"DISCIPLINARY": 61},
            grades={"A": "4.0"},
            external_requirements={"B1": True},
            recognitions={"EQUIV": frozenset({"B"})},
        )
        rules = (
            CreditsInGroup("PROGRAMMING", ">=", 3),
            CreditsInComponent("DISCIPLINARY", "=", 61),
            TotalCredits(">=", 141),
            GroupCompleted("STAT_CORE"),
            MandatoryCoursesCompleted(("A", "B")),
            MinimumGrade("A", Decimal("3.5")),
            ExternalRequirement("B1"),
            EquivalentCoursePassed("EQUIV", ("Z",)),
            Corequisite("C"),
        )
        self.assertTrue(
            all(evaluate_rule(rule, context).status == EvaluationStatus.SATISFIED for rule in rules)
        )
        self.assertEqual(
            direct_course_dependencies(All((CoursePassed("A"), Corequisite("B")))), {"A", "B"}
        )
        self.assertEqual(
            find_requirement_cycles({"A": CoursePassed("B"), "B": CoursePassed("A")}),
            (("A", "B", "A"),),
        )

    def test_golden_plan_2514_cases(self) -> None:
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        by_course = {
            row["owner_course_code"]: parse_rule(row["ast"])
            for row in baseline["enrollment_requirements"]
        }
        by_course.update({"2028081": parse_rule(baseline["enrollment_requirements"][-1]["ast"])})
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
        for case in golden["cases"]:
            facts = case["facts"]
            revision = RevisionFacts(
                total_credits=facts.get("total_plan_credits"),
                group_required_credits=facts.get("group_required", {}),
            )
            context = AuditContext(
                revision=revision,
                passed_courses=frozenset(facts.get("passed_courses", [])),
                earned_credits=facts.get("approved_credits", 0),
                group_credits=facts.get("group_credits", {}),
            )
            result = evaluate_rule(by_course[case["focus_course"]], context)
            self.assertEqual(result.status.value, case["expected"], case["id"])


@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=0, max_value=300))
def test_percentage_property_is_exact(approved: int) -> None:
    rule = PercentageOfPlan(4, 5)
    result = evaluate_rule(
        rule,
        AuditContext(revision=RevisionFacts(total_credits=141), earned_credits=approved),
    )
    expected = (
        EvaluationStatus.SATISFIED if approved * 5 >= 141 * 4 else EvaluationStatus.UNSATISFIED
    )
    assert result.status == expected


@settings(max_examples=50, deadline=None)
@given(st.sampled_from(["A", "B", "C"]))
def test_round_trip_and_evaluation_are_deterministic(course_code: str) -> None:
    rule = AnyOf((CoursePassed(course_code), Unknown("pending")))
    restored = parse_rule(serialize_rule(rule))
    context = AuditContext(passed_courses=frozenset({"A"}))
    assert ast_hash(rule) == ast_hash(restored)
    assert evaluate_rule(rule, context) == evaluate_rule(restored, context)
