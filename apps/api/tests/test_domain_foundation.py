from __future__ import annotations

import datetime
from pathlib import Path

from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import TestCase

from domain.enums import RevisionStatus
from domain.errors import PublishedRevisionImmutableError
from modules.curriculum.application.services import CurriculumRevisionService
from modules.curriculum.models import Course, CourseVersion, CurriculumRevision, PlanMembership
from tests.factories import foundation


class DomainFoundationTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.data = foundation()

    def test_course_identity_is_separate_from_temporal_versions_and_membership(self) -> None:
        course = self.data["course"]
        second_version = CourseVersion.objects.create(
            course=course,
            name="Introduction to Statistics — updated",
            credits=3,
            valid_from=datetime.date(2025, 1, 1),
        )
        self.assertEqual(Course.objects.filter(pk=course.pk).count(), 1)
        self.assertNotEqual(self.data["course_version"].pk, second_version.pk)
        self.assertNotIn("prerequisite", {field.name for field in Course._meta.get_fields()})
        membership = PlanMembership.objects.create(
            revision=self.data["revision"],
            course_version=self.data["course_version"],
            group=self.data["group"],
            role="MANDATORY",
        )
        self.assertEqual(membership.course_version.course_id, course.pk)

    def test_published_revision_content_is_immutable(self) -> None:
        revision = self.data["revision"]
        CurriculumRevisionService.publish(revision.pk)
        revision.refresh_from_db()
        self.assertEqual(revision.status, RevisionStatus.PUBLISHED.value)

        revision.total_required_credits = 142
        with self.assertRaises(PublishedRevisionImmutableError):
            revision.save(update_fields=["total_required_credits"])

        revision.refresh_from_db()
        with self.assertRaises(PublishedRevisionImmutableError):
            revision.delete()

    def test_postgresql_trigger_blocks_bulk_published_revision_mutation(self) -> None:
        if connection.vendor != "postgresql":
            self.skipTest("The database trigger is installed for PostgreSQL deployments.")
        revision = self.data["revision"]
        CurriculumRevisionService.publish(revision.pk)
        with self.assertRaises(DatabaseError), transaction.atomic():
            CurriculumRevision.objects.filter(pk=revision.pk).update(total_required_credits=999)
        revision.refresh_from_db()
        self.assertEqual(revision.total_required_credits, 141)

    def test_superseding_is_explicit_and_does_not_mutate_content(self) -> None:
        original = self.data["revision"]
        CurriculumRevisionService.publish(original.pk)
        successor = CurriculumRevision.objects.create(
            plan=self.data["plan"],
            revision_code="2024",
            effective_from=datetime.date(2024, 1, 1),
            total_required_credits=142,
            supersedes=original,
        )
        CurriculumRevisionService.supersede(original.pk, successor.pk)
        successor = CurriculumRevisionService.publish(successor.pk)
        original.refresh_from_db()
        self.assertEqual(original.status, RevisionStatus.SUPERSEDED.value)
        self.assertEqual(successor.status, RevisionStatus.PUBLISHED.value)
        self.assertEqual(successor.supersedes_id, original.pk)

    def test_database_constraints_protect_identity_and_ranges(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            Course.objects.create(
                institution=self.data["institution"], code=self.data["course"].code
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            CourseVersion.objects.create(
                course=self.data["course"],
                name="Duplicate start",
                credits=4,
                valid_from=datetime.date(2023, 1, 1),
            )

    def test_critical_constraints_and_indexes_are_declared(self) -> None:
        revision_constraints = {
            constraint.name for constraint in CurriculumRevision._meta.constraints
        }
        self.assertIn("revision_one_published_per_plan", revision_constraints)
        self.assertIn("revision_effective_range_valid", revision_constraints)
        version_indexes = {index.name for index in CourseVersion._meta.indexes}
        self.assertIn("course_version_temporal_idx", version_indexes)
        membership_constraints = {
            constraint.name for constraint in PlanMembership._meta.constraints
        }
        self.assertIn("membership_revision_course_group_unique", membership_constraints)

    def test_domain_package_has_no_django_imports(self) -> None:
        domain_root = Path(__file__).resolve().parents[1] / "domain"
        source = "\n".join(path.read_text(encoding="utf-8") for path in domain_root.rglob("*.py"))
        self.assertNotIn("import django", source)
        self.assertNotIn("from django", source)
