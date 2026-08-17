from __future__ import annotations

from django.test import SimpleTestCase

from domain.rules import (
    All,
    AnyOf,
    CoursePassed,
    CreditsInGroup,
    EquivalentCoursePassed,
    MandatoryCoursesCompleted,
    project_rule_graph,
    shortest_course_path,
    transitive_course_dependencies,
)


class DependencyGraphDomainTests(SimpleTestCase):
    def test_compound_and_threshold_rules_keep_condition_nodes(self) -> None:
        projection = project_rule_graph(
            {
                (
                    "D",
                    "REQ_D",
                ): All(
                    (
                        CoursePassed("A"),
                        AnyOf((CoursePassed("B"), CoursePassed("C"))),
                        CreditsInGroup("STAT", ">=", 3),
                    )
                ),
                ("E", "REQ_E"): CreditsInGroup("STAT", ">=", 6),
            }
        )

        condition_types = {
            node.condition_type for node in projection.nodes if node.kind == "CONDITION"
        }
        self.assertTrue({"ALL", "ANY", "CREDITS_IN_GROUP"}.issubset(condition_types))
        self.assertFalse(
            any(
                edge.source in {"course:A", "course:B", "course:C"}
                and edge.target == "course:D"
                and edge.edge_type == "PREREQUISITE"
                for edge in projection.edges
            )
        )
        self.assertFalse(any(edge.source == "course:E" for edge in projection.edges))
        relations = {
            (relation.source, relation.target, relation.relation_type)
            for relation in projection.course_relations
        }
        self.assertIn(("A", "D", "CONDITION_INPUT"), relations)
        self.assertIn(("B", "D", "CONDITION_INPUT"), relations)

    def test_direct_and_transitive_unlocks_are_deterministic(self) -> None:
        projection = project_rule_graph(
            {
                ("B", "REQ_B"): CoursePassed("A"),
                ("C", "REQ_C"): All((CoursePassed("B"), CreditsInGroup("STAT", ">=", 3))),
                ("D", "REQ_D"): EquivalentCoursePassed("EQUIV", ("C", "X")),
                ("E", "REQ_E"): MandatoryCoursesCompleted(("D", "Y")),
            }
        )
        descendants = transitive_course_dependencies(projection.course_relations)
        self.assertEqual(descendants["A"], ("B", "C", "D", "E"))
        self.assertEqual(
            shortest_course_path(projection.course_relations, "A", "E"), ("A", "B", "C", "D", "E")
        )
        self.assertEqual(
            [relation.target for relation in projection.course_relations if relation.source == "A"],
            ["B"],
        )

    def test_cycle_visualization_data_is_stable(self) -> None:
        projection = project_rule_graph(
            {
                ("A", "REQ_A"): CoursePassed("B"),
                ("B", "REQ_B"): CoursePassed("A"),
            }
        )
        self.assertEqual(projection.cycles, (("A", "B", "A"),))
        self.assertEqual(
            [node.node_id for node in projection.nodes],
            ["course:A", "course:B"],
        )

    def test_multiple_requirements_for_one_course_are_all_used_for_cycles(self) -> None:
        projection = project_rule_graph(
            {
                ("A", "REQ_A_1"): CoursePassed("B"),
                ("A", "REQ_A_2"): CoursePassed("C"),
                ("B", "REQ_B"): CoursePassed("A"),
            }
        )
        self.assertEqual(projection.cycles, (("A", "B", "A"),))
