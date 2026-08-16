from __future__ import annotations

import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from domain.enums import RevisionStatus
from domain.errors import DomainError
from modules.curriculum.models import CurriculumRevision
from modules.identity.application.audit import record_audit_event
from modules.identity.application.authorization import (
    can_manage_revision_lifecycle,
    can_publish_revision,
)


class RevisionTransitionError(DomainError):
    """Raised when a revision transition violates the publication workflow."""


class CurriculumRevisionService:
    """Transactional entry point for revision lifecycle changes.

    Published content is never updated by the ordinary edit operation. The only
    legal post-publication transitions are explicit supersede/retire actions.
    """

    @staticmethod
    # Django's decorator lacks a strict mypy signature; the local ignore preserves strict checking elsewhere.
    @transaction.atomic  # type: ignore[untyped-decorator]
    def publish(
        revision_id: object,
        published_at: datetime.datetime | None = None,
        actor: Any | None = None,
    ) -> CurriculumRevision:
        revision = CurriculumRevision.objects.select_for_update().get(pk=revision_id)
        if actor is not None and not can_publish_revision(actor, revision):
            raise RevisionTransitionError("The actor is not authorized to publish this revision.")
        if revision.status not in {
            RevisionStatus.DRAFT.value,
            RevisionStatus.IN_REVIEW.value,
            RevisionStatus.APPROVED.value,
        }:
            raise RevisionTransitionError(f"Cannot publish revision in state {revision.status}.")
        revision.status = RevisionStatus.PUBLISHED.value
        revision.published_at = published_at or timezone.now()
        revision.save(update_fields=["status", "published_at", "updated_at"])
        if actor is not None:
            record_audit_event(
                None,
                action="CURRICULUM_REVISION_PUBLISHED",
                actor=actor,
                object_type="CurriculumRevision",
                object_id=revision.pk,
                institution_id=revision.plan.program.faculty.campus.institution_id,
                metadata={"revision_code": revision.revision_code},
            )
        return revision

    @staticmethod
    # Django's decorator lacks a strict mypy signature; the local ignore preserves strict checking elsewhere.
    @transaction.atomic  # type: ignore[untyped-decorator]
    def supersede(
        revision_id: object, successor_id: object, actor: Any | None = None
    ) -> CurriculumRevision:
        revision = CurriculumRevision.objects.select_for_update().get(pk=revision_id)
        successor = CurriculumRevision.objects.select_for_update().get(pk=successor_id)
        if revision.status != RevisionStatus.PUBLISHED.value:
            raise RevisionTransitionError("Only a published revision can be superseded.")
        if successor.plan_id != revision.plan_id or successor.supersedes_id != revision.id:
            raise RevisionTransitionError(
                "Successor must belong to the plan and name the revision it supersedes."
            )
        if actor is not None and not can_manage_revision_lifecycle(actor, successor):
            raise RevisionTransitionError("The actor is not authorized to supersede this revision.")
        revision.status = RevisionStatus.SUPERSEDED.value
        revision.save(update_fields=["status", "updated_at"])
        if actor is not None:
            record_audit_event(
                None,
                action="CURRICULUM_REVISION_SUPERSEDED",
                actor=actor,
                object_type="CurriculumRevision",
                object_id=revision.pk,
                institution_id=revision.plan.program.faculty.campus.institution_id,
                metadata={"successor_id": successor.pk},
            )
        return revision

    @staticmethod
    # Django's decorator lacks a strict mypy signature; the local ignore preserves strict checking elsewhere.
    @transaction.atomic  # type: ignore[untyped-decorator]
    def retire(revision_id: object, actor: Any | None = None) -> CurriculumRevision:
        revision = CurriculumRevision.objects.select_for_update().get(pk=revision_id)
        if actor is not None and not can_manage_revision_lifecycle(actor, revision):
            raise RevisionTransitionError("The actor is not authorized to retire this revision.")
        if revision.status not in {
            RevisionStatus.PUBLISHED.value,
            RevisionStatus.SUPERSEDED.value,
        }:
            raise RevisionTransitionError(f"Cannot retire revision in state {revision.status}.")
        revision.status = RevisionStatus.RETIRED.value
        revision.save(update_fields=["status", "updated_at"])
        if actor is not None:
            record_audit_event(
                None,
                action="CURRICULUM_REVISION_RETIRED",
                actor=actor,
                object_type="CurriculumRevision",
                object_id=revision.pk,
                institution_id=revision.plan.program.faculty.campus.institution_id,
                metadata={"revision_code": revision.revision_code},
            )
        return revision
