from __future__ import annotations

import json
from unittest.mock import patch

from django.test import Client, TestCase

from domain.enums import MembershipRole
from modules.curriculum.models import PlanMembership
from modules.optimization.application.runs import (
    build_optimization_input,
    execute_optimization_run,
)
from modules.optimization.models import OptimizationRun
from modules.planning.application.scenarios import create_scenario
from tests.factories import foundation


class OptimizationApiTests(TestCase):
    def setUp(self) -> None:
        self.context = foundation(suffix="-optimizer")
        self.user = self.context["user"]
        self.enrollment = self.context["enrollment"]
        self.revision = self.context["revision"]
        self.group = self.context["revision"].requirement_groups.get()
        self.membership = PlanMembership.objects.create(
            revision=self.revision,
            course_version=self.context["course_version"],
            group=self.group,
            role=MembershipRole.MANDATORY.value,
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_run_persists_snapshot_hash_solution_and_explanation(self) -> None:
        scenario = create_scenario(
            self.user,
            name="Ruta optimizable",
            enrollment_id=self.enrollment.pk,
            target_term_id=self.context["term"].pk,
        )
        input_data = build_optimization_input(scenario, time_limit_seconds=5)
        run = OptimizationRun.objects.create(
            scenario=scenario,
            input_hash=input_data.input_hash,
            input_snapshot=input_data.to_dict(),
            solver_version="cp-sat-planner/1.0.0",
            status="QUEUED",
            time_limit_seconds=5,
        )

        finished = execute_optimization_run(run.pk)

        self.assertEqual(finished.status, "OPTIMAL")
        self.assertEqual(finished.input_hash, input_data.input_hash)
        self.assertTrue(finished.output_hash)
        self.assertTrue(finished.input_snapshot["courses"])
        self.assertTrue(finished.solution["selected_courses"])
        self.assertTrue(finished.explanation["explanations"])

    def test_api_queues_run_without_mutating_planned_history(self) -> None:
        scenario = create_scenario(
            self.user,
            name="Ruta API",
            enrollment_id=self.enrollment.pk,
            target_term_id=self.context["term"].pk,
        )
        before_attempts = self.enrollment.course_attempts.count()
        with patch("modules.optimization.application.runs.submit_optimization_run") as submit:
            response = self.client.post(
                f"/api/v1/scenarios/{scenario.pk}/optimization-runs",
                data=json.dumps({"time_limit_seconds": 5}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 202, response.content)
        submit.assert_called_once()
        run = OptimizationRun.objects.get(pk=response.json()["id"])
        self.assertEqual(run.status, "QUEUED")
        self.assertEqual(self.enrollment.course_attempts.count(), before_attempts)

        execute_optimization_run(run.pk)
        detail = self.client.get(f"/api/v1/optimization-runs/{run.pk}")
        self.assertEqual(detail.status_code, 200, detail.content)
        self.assertEqual(detail.json()["status"], "OPTIMAL")
        self.assertTrue(detail.json()["output_hash"])

    def test_api_rejects_unknown_offering_policy_as_a_client_error(self) -> None:
        scenario = create_scenario(
            self.user,
            name="Ruta política inválida",
            enrollment_id=self.enrollment.pk,
            target_term_id=self.context["term"].pk,
        )
        response = self.client.post(
            f"/api/v1/scenarios/{scenario.pk}/optimization-runs",
            data=json.dumps({"time_limit_seconds": 5, "unknown_offering_policy": "GUESS"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()["code"], "OPTIMIZATION_REQUEST_INVALID")
