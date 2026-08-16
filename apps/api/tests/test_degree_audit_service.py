from __future__ import annotations

from django.test import TestCase

from domain.enums import AttemptStatus, MembershipRole, RequirementGroupKind
from modules.audit.application.services import run_degree_audit
from modules.audit.models import CreditAllocation, DegreeAuditResult, DegreeAuditRun
from modules.curriculum.models import PlanMembership, RequirementGroup
from modules.student_records.models import CourseAttempt
from tests.factories import foundation


class DegreeAuditApplicationServiceTests(TestCase):
    def test_run_persists_reproducible_snapshot_result_and_allocations(self) -> None:
        data = foundation(suffix="audit")
        revision = data["revision"]
        revision.total_required_credits = 4
        revision.save(update_fields=["total_required_credits"])
        component = data["group"]
        component.metadata = {"source_component_id": "COREaudit"}
        component.save(update_fields=["metadata"])
        group = RequirementGroup.objects.create(
            revision=revision,
            parent=component,
            code="CORE_BUCKETaudit",
            label="Core bucket",
            kind=RequirementGroupKind.GROUP.value,
            required_credits=4,
            metadata={"source_component_id": "COREaudit"},
        )
        PlanMembership.objects.create(
            revision=revision,
            course_version=data["course_version"],
            group=group,
            role=MembershipRole.MANDATORY.value,
        )
        CourseAttempt.objects.create(
            enrollment=data["enrollment"],
            course_version=data["course_version"],
            term=data["term"],
            status=AttemptStatus.PASSED.value,
            credits_earned=4,
        )

        first, first_run, first_persisted = run_degree_audit(data["enrollment"].pk)
        second, second_run, second_persisted = run_degree_audit(data["enrollment"].pk)

        self.assertEqual(first.status.value, "SATISFIED")
        self.assertEqual(first.result_hash, second.result_hash)
        self.assertEqual(first.input_fingerprint, second.input_fingerprint)
        self.assertEqual(first_run.revision_id, revision.pk)
        self.assertTrue(first_run.history_fingerprint)
        self.assertTrue(first_run.exception_fingerprint)
        self.assertEqual(first_run.history_fingerprint, second_run.history_fingerprint)
        self.assertEqual(first_run.exception_fingerprint, second_run.exception_fingerprint)
        self.assertEqual(first_persisted.total_approved_credits, 4)
        self.assertEqual(first_persisted.total_applied_credits, 4)
        self.assertEqual(first_persisted.total_excess_credits, 0)
        self.assertEqual(first_persisted.payload["overall"]["status"], "SATISFIED")
        self.assertEqual(
            list(first_persisted.credit_allocations.values_list("allocated_credits", flat=True)),
            [4],
        )
        self.assertEqual(DegreeAuditRun.objects.filter(enrollment=data["enrollment"]).count(), 2)
        self.assertEqual(DegreeAuditResult.objects.count(), 2)
        self.assertEqual(CreditAllocation.objects.count(), 2)
        self.assertEqual(second_run.result_hash, second_persisted.payload["result_hash"])
