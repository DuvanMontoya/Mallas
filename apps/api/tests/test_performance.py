from __future__ import annotations

import datetime
from threading import Event
from uuid import uuid4

from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext

from modules.curriculum.application.graph import build_dependency_graph
from modules.curriculum.application.map import build_curriculum_map
from modules.offerings.models import AcademicTerm
from modules.optimization.application import runs as optimization_runs
from modules.student_records.application.enrollment import preferred_enrollment_for_user
from modules.student_records.models import ProgramEnrollment
from tests.factories import foundation


class EnrollmentReadPathPerformanceTests(TestCase):
    def setUp(self) -> None:
        self.data = foundation(suffix="-performance")

    def test_preferred_enrollment_preserves_priority_in_one_query(self) -> None:
        later_term = AcademicTerm.objects.create(
            institution=self.data["institution"],
            campus=self.data["campus"],
            code="2027-1-performance",
            starts_at=datetime.datetime(2027, 1, 1, tzinfo=datetime.UTC),
            ends_at=datetime.datetime(2027, 6, 30, tzinfo=datetime.UTC),
        )
        completed = ProgramEnrollment.objects.create(
            student=self.data["student"],
            program=self.data["program"],
            plan=self.data["plan"],
            revision_basis=self.data["revision"],
            admission_term=later_term,
            status="COMPLETED",
        )

        with CaptureQueriesContext(connection) as queries:
            selected = preferred_enrollment_for_user(self.data["user"].pk)

        self.assertEqual(selected, self.data["enrollment"])
        self.assertNotEqual(selected, completed)
        self.assertEqual(len(queries), 1)

    def test_empty_preferred_enrollment_lookup_is_one_query(self) -> None:
        with CaptureQueriesContext(connection) as queries:
            selected = preferred_enrollment_for_user(-1)

        self.assertIsNone(selected)
        self.assertEqual(len(queries), 1)


class CurriculumReadPathPerformanceTests(TestCase):
    def setUp(self) -> None:
        self.data = foundation(suffix="-read-budget")
        self.data["revision"].total_required_credits = 4
        self.data["revision"].save(update_fields=["total_required_credits"])

    def test_map_and_graph_have_bounded_query_counts(self) -> None:
        with CaptureQueriesContext(connection) as map_queries:
            curriculum = build_curriculum_map(None, plan_code=self.data["plan"].code)
        with CaptureQueriesContext(connection) as graph_queries:
            graph = build_dependency_graph(None, plan_code=self.data["plan"].code)

        self.assertEqual(curriculum["revision"]["plan_code"], self.data["plan"].code)
        self.assertEqual(graph["revision"]["plan_code"], self.data["plan"].code)
        self.assertLessEqual(len(map_queries), 28)
        self.assertLessEqual(len(graph_queries), 28)


class OptimizationCapacityTests(SimpleTestCase):
    def test_submit_rejects_work_beyond_the_bounded_in_flight_queue(self) -> None:
        with optimization_runs._jobs_lock:
            previous = dict(optimization_runs._jobs)
            optimization_runs._jobs.clear()
            optimization_runs._jobs.update(
                {
                    str(index): Event()
                    for index in range(optimization_runs.MAX_IN_FLIGHT_OPTIMIZATION_JOBS)
                }
            )
        try:
            with self.assertRaises(optimization_runs.OptimizationRunError) as raised:
                optimization_runs.submit_optimization_run(uuid4())
            self.assertEqual(raised.exception.code, "optimization_capacity")
        finally:
            with optimization_runs._jobs_lock:
                optimization_runs._jobs.clear()
                optimization_runs._jobs.update(previous)
