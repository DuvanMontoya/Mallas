from __future__ import annotations

import copy
import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from domain.enums import EpistemicStatus, RevisionStatus
from modules.curriculum.models import (
    Course,
    CurriculumRevision,
    PlanMembership,
    RequirementGroup,
)
from modules.governance.models import ChangeProposal, Evidence, SourceSnapshot
from modules.imports.application.baseline import (
    baseline_fingerprint,
    load_baseline,
    semantic_diff,
    validate_baseline,
)
from modules.imports.application.services import (
    CurriculumImportError,
    diff_curriculum_files,
    import_curriculum_baseline,
)
from modules.imports.models import ImportBatch
from modules.rules.models import Requirement

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


class CurriculumBaselineValidationTests(TestCase):
    def test_baseline_counts_totals_unknowns_and_fingerprint_are_deterministic(self) -> None:
        document = load_baseline(BASELINE)
        report = validate_baseline(document.payload)
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(report.counts["courses"], 102)
        self.assertEqual(report.counts["memberships"], 97)
        self.assertEqual(report.counts["enrollment_requirements"], 73)
        self.assertEqual(
            report.totals,
            {
                "disciplinary": 61,
                "foundation": 52,
                "free_elective": 28,
                "required_credits": 141,
            },
        )
        self.assertEqual(len(report.unknowns), 12)

        reordered = copy.deepcopy(document.payload)
        reordered["courses"] = list(reversed(reordered["courses"]))
        reordered["groups"] = list(reversed(reordered["groups"]))
        self.assertEqual(document.fingerprint, baseline_fingerprint(reordered))

    def test_semantic_diff_ignores_page_locator_changes_and_is_stable(self) -> None:
        document = load_baseline(BASELINE)
        candidate = copy.deepcopy(document.payload)
        candidate["memberships"][0]["source_page"] = 999
        diff = semantic_diff(document.payload, candidate)
        self.assertFalse(diff["has_changes"])
        self.assertEqual(diff, semantic_diff(document.payload, candidate))
        self.assertFalse(diff_curriculum_files(BASELINE, BASELINE)["has_changes"])


class CurriculumIngestionPersistenceTests(TestCase):
    def test_import_is_idempotent_draft_and_evidence_backed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = import_curriculum_baseline(BASELINE, report_path=Path(directory) / "first.md")
            second = import_curriculum_baseline(BASELINE, report_path=Path(directory) / "second.md")
            self.assertTrue(Path(first.report_path).is_file())

        self.assertEqual(first.revision_id, second.revision_id)
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(CurriculumRevision.objects.count(), 1)
        self.assertEqual(Course.objects.filter(institution__slug="unal").count(), 102)
        self.assertEqual(ImportBatch.objects.filter(source_kind="CURRICULUM_BASELINE").count(), 1)
        self.assertEqual(ChangeProposal.objects.count(), 1)
        self.assertEqual(SourceSnapshot.objects.count(), 1)
        self.assertEqual(Evidence.objects.count(), 73)

        revision = CurriculumRevision.objects.get(revision_code="2514-AC496-2023")
        self.assertEqual(revision.status, RevisionStatus.DRAFT.value)
        self.assertEqual(revision.total_required_credits, 141)
        self.assertEqual(RequirementGroup.objects.filter(revision=revision).count(), 15)
        self.assertEqual(PlanMembership.objects.filter(revision=revision).count(), 97)
        self.assertEqual(Requirement.objects.filter(revision=revision).count(), 74)
        self.assertFalse(
            Requirement.objects.filter(
                revision=revision,
                epistemic_status=EpistemicStatus.VERIFIED.value,
                evidence__isnull=True,
            ).exists()
        )
        unknown = Requirement.objects.get(
            revision=revision,
            owner_type="COURSE",
            owner_id__in=revision.plan.program.faculty.campus.institution.courses.filter(
                code="2016367"
            ).values("id"),
        )
        self.assertEqual(unknown.epistemic_status, EpistemicStatus.UNKNOWN.value)

    def test_management_commands_validate_import_and_diff(self) -> None:
        validation_output = StringIO()
        call_command("validate_curriculum", "--json", stdout=validation_output)
        validation = json.loads(validation_output.getvalue())
        self.assertTrue(validation["ok"])
        self.assertEqual(validation["totals"]["required_credits"], 141)

        diff_output = StringIO()
        call_command("diff_curriculum", str(BASELINE), "--base", str(BASELINE), stdout=diff_output)
        self.assertFalse(json.loads(diff_output.getvalue())["has_changes"])

        with tempfile.TemporaryDirectory() as directory:
            import_output = StringIO()
            call_command(
                "import_curriculum",
                "--json",
                "--report",
                str(Path(directory) / "command.md"),
                stdout=import_output,
            )
            imported = json.loads(import_output.getvalue())
        self.assertEqual(imported["counts"]["courses"], 102)

    def test_import_refuses_to_mutate_non_draft_revision(self) -> None:
        imported = import_curriculum_baseline(BASELINE)
        revision = CurriculumRevision.objects.get(pk=imported.revision_id)
        revision.status = RevisionStatus.PUBLISHED.value
        revision.save(update_fields=["status"])
        with self.assertRaisesMessage(CurriculumImportError, "only mutates DRAFT revisions"):
            import_curriculum_baseline(BASELINE)
