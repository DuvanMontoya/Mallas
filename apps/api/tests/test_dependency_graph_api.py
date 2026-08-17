from __future__ import annotations

from pathlib import Path

from django.test import Client, TestCase

from modules.curriculum.models import CurriculumRevision
from modules.imports.application.services import import_curriculum_baseline

BASELINE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "curricula"
    / "unal"
    / "bogota"
    / "estadistica"
    / "2514"
    / "plan_2514_acuerdo_496_2023.json"
)


class DependencyGraphApiTests(TestCase):
    def setUp(self) -> None:
        imported = import_curriculum_baseline(BASELINE)
        self.revision = CurriculumRevision.objects.get(pk=imported.revision_id)
        self.client = Client()

    def test_projection_contains_semantic_conditions_and_focus_analysis(self) -> None:
        response = self.client.get("/api/v1/dependency-graph?selected=2016379")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["revision"]["status"], "DRAFT")
        self.assertGreater(len(payload["nodes"]), 102)
        self.assertGreater(len(payload["edges"]), 80)
        self.assertTrue(
            {"ALL", "ANY", "CREDITS_IN_GROUP", "CREDITS_IN_COMPONENT"}.issubset(
                {node["condition_type"] for node in payload["nodes"] if node["kind"] == "CONDITION"}
            )
        )
        self.assertTrue(all("requirement_code" in edge for edge in payload["edges"]))
        self.assertIsNotNone(response.headers.get("ETag"))

        focus = payload["focus"]
        self.assertEqual(focus["course_code"], "2016379")
        self.assertIn("2016360", {item["course_code"] for item in focus["descendants"]})
        path = next(
            item for item in focus["shortest_unlock_paths"] if item["target_course"] == "2016361"
        )
        self.assertEqual(path["node_ids"][0], "course:2016379")
        self.assertEqual(path["node_ids"][-1], "course:2016361")
        self.assertTrue(any("CONDITION" in edge_kind for edge_kind in path["edge_kinds"]))

    def test_unknown_focus_is_explainable_and_does_not_change_the_graph(self) -> None:
        response = self.client.get("/api/v1/dependency-graph?selected=DOES-NOT-EXIST")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["focus"])
        self.assertIn("GRAPH_FOCUS_NOT_FOUND", payload["warnings"])
