from __future__ import annotations

import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from domain.enums import (
    CurriculumLayoutNodeType,
    CurriculumLayoutStatus,
    CurriculumLayoutType,
    EpistemicStatus,
    MembershipRole,
    RequirementGroupKind,
    RequirementPurpose,
)
from domain.errors import PublishedCurriculumLayoutImmutableError
from modules.curriculum.models import (
    CourseVersion,
    CurriculumLayout,
    CurriculumRevision,
    LayoutNodeOccurrence,
    PlanMembership,
    RequirementGroup,
)
from modules.rules.models import Requirement
from tests.factories import foundation


class CurriculumLayoutLifecycleTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.context = foundation(suffix="-layout")
        cls.layout = CurriculumLayout.objects.create(
            revision=cls.context["revision"],
            layout_code="source-faithful",
            layout_type=CurriculumLayoutType.SOURCE_FAITHFUL_LAYOUT.value,
            title="Malla fuente 2514",
            epistemic_status=EpistemicStatus.INFERRED_PENDING_REVIEW.value,
        )

    def _submit_review(self, layout: CurriculumLayout) -> None:
        layout._review_submission_service_authorized = True
        layout.status = CurriculumLayoutStatus.IN_REVIEW.value
        layout.content_hash = "a" * 64
        layout.save()

    def _publish(self, layout: CurriculumLayout) -> None:
        layout._publication_service_authorized = True
        layout.status = CurriculumLayoutStatus.PUBLISHED.value
        layout.save()

    def test_draft_layout_can_be_created_and_edited(self) -> None:
        self.layout.title = "Malla fuente 2514 (borrador)"
        self.layout.full_clean()
        self.layout.save()
        self.assertEqual(
            CurriculumLayout.objects.get(pk=self.layout.pk).status,
            CurriculumLayoutStatus.DRAFT.value,
        )

    def test_draft_cannot_enter_review_without_governance(self) -> None:
        self.layout.status = CurriculumLayoutStatus.IN_REVIEW.value
        with self.assertRaises(PublishedCurriculumLayoutImmutableError):
            self.layout.save()

    def test_draft_cannot_be_published_directly_without_governance(self) -> None:
        self.layout.status = CurriculumLayoutStatus.PUBLISHED.value
        with self.assertRaises(PublishedCurriculumLayoutImmutableError):
            self.layout.save()

    def test_new_layout_cannot_start_in_governed_state(self) -> None:
        with self.assertRaises(PublishedCurriculumLayoutImmutableError):
            CurriculumLayout.objects.create(
                revision=self.context["revision"],
                layout_code="published-direct",
                layout_type=CurriculumLayoutType.SOURCE_FAITHFUL_LAYOUT.value,
                title="Direct publish",
                status=CurriculumLayoutStatus.PUBLISHED.value,
            )

    def test_review_submission_and_publication_require_separate_flags(self) -> None:
        self._submit_review(self.layout)
        self.layout.status = CurriculumLayoutStatus.PUBLISHED.value
        with self.assertRaises(PublishedCurriculumLayoutImmutableError):
            self.layout.save()
        self._publish(self.layout)
        self.assertEqual(
            CurriculumLayout.objects.get(pk=self.layout.pk).status,
            CurriculumLayoutStatus.PUBLISHED.value,
        )

    def test_published_layout_content_is_immutable(self) -> None:
        self._submit_review(self.layout)
        self._publish(self.layout)
        self.layout.title = "Intento de edición"
        with self.assertRaises(PublishedCurriculumLayoutImmutableError):
            self.layout.save()

    def test_published_layout_cannot_move_backwards(self) -> None:
        self._submit_review(self.layout)
        self._publish(self.layout)
        self.layout.status = CurriculumLayoutStatus.IN_REVIEW.value
        with self.assertRaises(PublishedCurriculumLayoutImmutableError):
            self.layout.save()
        self.layout.status = CurriculumLayoutStatus.DRAFT.value
        with self.assertRaises(PublishedCurriculumLayoutImmutableError):
            self.layout.save()

    def test_superseded_status_requires_a_finalized_predecessor(self) -> None:
        self._submit_review(self.layout)
        self._publish(self.layout)
        self.layout.status = CurriculumLayoutStatus.SUPERSEDED.value
        with self.assertRaises(ValidationError):
            self.layout.full_clean()

    def test_successor_can_supersede_published_layout_with_same_code(self) -> None:
        self._submit_review(self.layout)
        self._publish(self.layout)
        successor = CurriculumLayout.objects.create(
            revision=self.context["revision"],
            layout_code="source-faithful",
            layout_type=CurriculumLayoutType.SOURCE_FAITHFUL_LAYOUT.value,
            title="Malla fuente 2514 v2",
            layout_version=2,
            supersedes=self.layout,
        )
        self.assertEqual(successor.layout_version, 2)
        self.assertEqual(successor.supersedes_id, self.layout.pk)

    def test_successor_must_increase_layout_version(self) -> None:
        self._submit_review(self.layout)
        self._publish(self.layout)
        with self.assertRaises(ValidationError):
            CurriculumLayout.objects.create(
                revision=self.context["revision"],
                layout_code="source-faithful",
                layout_type=CurriculumLayoutType.SOURCE_FAITHFUL_LAYOUT.value,
                title="Versión repetida",
                layout_version=1,
                supersedes=self.layout,
            )

    def test_successor_must_match_code_revision_and_finalized_predecessor(self) -> None:
        draft = CurriculumLayout.objects.create(
            revision=self.context["revision"],
            layout_code="dependency-derived",
            layout_type=CurriculumLayoutType.DEPENDENCY_DERIVED_LAYOUT.value,
            title="Derivada",
        )
        with self.assertRaises(ValidationError):
            CurriculumLayout.objects.create(
                revision=self.context["revision"],
                layout_code="other-code",
                layout_type=CurriculumLayoutType.SOURCE_FAITHFUL_LAYOUT.value,
                title="Otro código",
                supersedes=draft,
            )
        with self.assertRaises(ValidationError):
            CurriculumLayout.objects.create(
                revision=self.context["revision"],
                layout_code="dependency-derived",
                layout_type=CurriculumLayoutType.DEPENDENCY_DERIVED_LAYOUT.value,
                title="Auto sucesión",
                supersedes=draft,
            )
        draft.supersedes_id = draft.pk
        with self.assertRaises(ValidationError):
            draft.full_clean()

    def test_sealed_layouts_cannot_be_deleted(self) -> None:
        self._submit_review(self.layout)
        with self.assertRaises(PublishedCurriculumLayoutImmutableError):
            self.layout.delete()
        self._publish(self.layout)
        with self.assertRaises(PublishedCurriculumLayoutImmutableError):
            self.layout.delete()


class LayoutNodeOccurrenceTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.context = foundation(suffix="-layout-node")
        cls.layout = CurriculumLayout.objects.create(
            revision=cls.context["revision"],
            layout_code="source-faithful",
            layout_type=CurriculumLayoutType.SOURCE_FAITHFUL_LAYOUT.value,
            title="Malla fuente 2514",
        )
        cls.other_revision = CurriculumRevision.objects.create(
            plan=cls.context["plan"],
            revision_code="2099-foreign",
            effective_from=datetime.date(2099, 1, 1),
            total_required_credits=100,
        )
        cls.foreign_group = RequirementGroup.objects.create(
            revision=cls.other_revision,
            code="FOREIGN-CORE",
            label="Foreign core",
            kind=RequirementGroupKind.COMPONENT.value,
            required_credits=3,
        )
        cls.foreign_requirement = Requirement.objects.create(
            revision=cls.other_revision,
            owner_type="PROGRAM",
            owner_id=cls.context["plan"].pk,
            code="FOREIGN-B1",
            purpose=RequirementPurpose.GRADUATION.value,
            ast={"type": "ALL", "children": []},
            epistemic_status=EpistemicStatus.UNKNOWN.value,
        )

    def _node(self, node_code: str = "N1", **kwargs: object) -> LayoutNodeOccurrence:
        return LayoutNodeOccurrence(layout=self.layout, node_code=node_code, **kwargs)

    def test_course_node_requires_membership_in_layout_revision(self) -> None:
        PlanMembership.objects.create(
            revision=self.context["revision"],
            course_version=self.context["course_version"],
            group=self.context["group"],
            role=MembershipRole.MANDATORY.value,
        )
        node = self._node(
            node_type=CurriculumLayoutNodeType.COURSE.value,
            target_course_version=self.context["course_version"],
        )
        node.full_clean()
        node.save()

        foreign_course_version = CourseVersion.objects.create(
            course=self.context["course"],
            name="Curso de otra revisión",
            credits=2,
            valid_from=datetime.date(2099, 1, 1),
        )
        PlanMembership.objects.create(
            revision=self.other_revision,
            course_version=foreign_course_version,
            group=self.foreign_group,
            role=MembershipRole.MANDATORY.value,
        )
        foreign = self._node(
            node_code="N2",
            node_type=CurriculumLayoutNodeType.COURSE.value,
            target_course_version=foreign_course_version,
        )
        with self.assertRaises(ValidationError):
            foreign.full_clean()

    def test_pool_node_requires_group_in_layout_revision(self) -> None:
        node = self._node(
            node_type=CurriculumLayoutNodeType.FREE_ELECTIVE_POOL.value,
            target_group=self.context["group"],
        )
        node.full_clean()
        node.save()

        foreign = self._node(
            node_code="N3",
            node_type=CurriculumLayoutNodeType.FREE_ELECTIVE_POOL.value,
            target_group=self.foreign_group,
        )
        with self.assertRaises(ValidationError):
            foreign.full_clean()

    def test_external_requirement_node_requires_requirement_in_layout_revision(self) -> None:
        requirement = Requirement.objects.create(
            revision=self.context["revision"],
            owner_type="PROGRAM",
            owner_id=self.context["plan"].pk,
            code="B1-FOREIGN-LANGUAGE",
            purpose=RequirementPurpose.GRADUATION.value,
            ast={"type": "ALL", "children": []},
            epistemic_status=EpistemicStatus.UNKNOWN.value,
        )
        node = self._node(
            node_type=CurriculumLayoutNodeType.EXTERNAL_REQUIREMENT.value,
            target_requirement=requirement,
        )
        node.full_clean()
        node.save()

        foreign = self._node(
            node_code="N4",
            node_type=CurriculumLayoutNodeType.EXTERNAL_REQUIREMENT.value,
            target_requirement=self.foreign_requirement,
        )
        with self.assertRaises(ValidationError):
            foreign.full_clean()

    def test_annotation_node_cannot_point_to_targets(self) -> None:
        node = self._node(
            node_type=CurriculumLayoutNodeType.ANNOTATION.value,
            target_course_version=self.context["course_version"],
        )
        with self.assertRaises(ValidationError):
            node.full_clean()

    def test_node_type_target_exclusivity_is_enforced(self) -> None:
        mixed = self._node(
            node_type=CurriculumLayoutNodeType.COURSE.value,
            target_course_version=self.context["course_version"],
            target_group=self.context["group"],
        )
        with self.assertRaises(ValidationError):
            mixed.full_clean()
