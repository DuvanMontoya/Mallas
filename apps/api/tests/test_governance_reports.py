from __future__ import annotations

import json
import tempfile
from io import StringIO
from pathlib import Path
from uuid import uuid4

from django.core.management import call_command
from django.test import TestCase

from domain.enums import EpistemicStatus, RequirementPurpose
from modules.rules.models import Requirement

from .factories import foundation


class UnknownRuleQueueTests(TestCase):
    def test_queue_is_review_only_and_contains_evidence_counts(self) -> None:
        data = foundation(suffix="-queue")
        Requirement.objects.create(
            revision=data["revision"],
            owner_type="PLAN",
            owner_id=uuid4(),
            code="RULE_UNKNOWN_QUEUE",
            purpose=RequirementPurpose.GRADUATION.value,
            ast={"type": "UNKNOWN"},
            epistemic_status=EpistemicStatus.UNKNOWN.value,
        )
        output = StringIO()

        call_command("unknown_rule_queue", stdout=output)

        payload = json.loads(output.getvalue())
        self.assertEqual(payload["policy"], "human_review_required_no_auto_publish")
        self.assertEqual(payload["counts"]["total"], 1)
        self.assertTrue(payload["items"][0]["publish_blocker"])
        self.assertEqual(payload["items"][0]["review_action"], "HUMAN_REVIEW_REQUIRED")

    def test_queue_can_be_exported_as_private_csv(self) -> None:
        data = foundation(suffix="-queue-csv")
        Requirement.objects.create(
            revision=data["revision"],
            owner_type="COURSE",
            owner_id=uuid4(),
            code="RULE_DISPUTED_QUEUE",
            purpose=RequirementPurpose.ENROLLMENT_PREREQUISITE.value,
            ast={"type": "DISPUTED"},
            epistemic_status=EpistemicStatus.DISPUTED.value,
        )
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "unknown-rules.csv"
            call_command("unknown_rule_queue", "--format", "csv", "--output", output_path)
            content = output_path.read_text(encoding="utf-8")
        self.assertIn("RULE_DISPUTED_QUEUE", content)
        self.assertIn("HUMAN_REVIEW_REQUIRED", content)
