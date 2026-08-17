from __future__ import annotations

import datetime
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import TestCase

from domain.enums import RequirementPurpose, RevisionStatus
from domain.errors import PublishedRevisionImmutableError
from modules.curriculum.application.services import CurriculumRevisionService
from modules.curriculum.models import (
    Course,
    CourseVersion,
    CurriculumRevision,
    PlanMembership,
    RequirementGroup,
)
from modules.rules.models import Requirement
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

    def test_published_revision_children_are_immutable(self) -> None:
        revision = self.data["revision"]
        group = self.data["group"]
        membership = PlanMembership.objects.create(
            revision=revision,
            course_version=self.data["course_version"],
            group=group,
            role="MANDATORY",
        )
        requirement = Requirement.objects.create(
            revision=revision,
            owner_type="COURSE",
            owner_id=self.data["course"].pk,
            code="TEST:PREREQUISITE",
            purpose=RequirementPurpose.ENROLLMENT_PREREQUISITE.value,
            ast={"type": "COURSE_PASSED", "course_code": self.data["course"].code},
            epistemic_status="VERIFIED",
        )
        CurriculumRevisionService.publish(revision.pk)

        group.label = "Changed after publication"
        with self.assertRaises(PublishedRevisionImmutableError):
            group.save(update_fields=["label", "updated_at"])
        with self.assertRaises(PublishedRevisionImmutableError):
            group.delete()

        membership.role = "ELECTIVE_OPTION"
        with self.assertRaises(PublishedRevisionImmutableError):
            membership.save(update_fields=["role", "updated_at"])
        with self.assertRaises(PublishedRevisionImmutableError):
            membership.delete()

        requirement.ast = {"type": "UNKNOWN"}
        with self.assertRaises(ValidationError):
            requirement.save(update_fields=["ast", "updated_at"])
        with self.assertRaises(ValidationError):
            requirement.delete()

        with self.assertRaises(PublishedRevisionImmutableError):
            RequirementGroup.objects.create(
                revision=revision,
                code="NEW_GROUP",
                label="No mutation",
                kind="GROUP",
            )

        if connection.vendor == "postgresql":
            with self.assertRaises(DatabaseError), transaction.atomic():
                RequirementGroup.objects.filter(pk=group.pk).update(label="Bulk mutation")
            with self.assertRaises(DatabaseError), transaction.atomic():
                PlanMembership.objects.filter(pk=membership.pk).delete()
            with self.assertRaises(DatabaseError), transaction.atomic():
                Requirement.objects.filter(pk=requirement.pk).update(ast={"type": "UNKNOWN"})

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
