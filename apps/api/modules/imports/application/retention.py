from __future__ import annotations

from datetime import datetime

from django.db import models, transaction
from django.utils import timezone

from domain.enums import ImportArtifactStatus
from modules.imports.application.storage import delete_artifact
from modules.imports.models import CandidateRecord, RawArtifact


@transaction.atomic  # type: ignore[untyped-decorator]
def purge_expired_candidate_payloads(*, as_of: datetime | None = None) -> int:
    """Irreversibly clear minimized raw rows after their bounded review window."""

    cutoff = as_of or timezone.now()
    candidates = CandidateRecord.objects.select_for_update().filter(
        raw_payload_expires_at__lte=cutoff,
        raw_payload_purged_at__isnull=True,
    )
    return candidates.update(raw_payload={}, raw_payload_purged_at=cutoff, updated_at=cutoff)


@transaction.atomic  # type: ignore[untyped-decorator]
def purge_applied_batch_payloads(*, batch_id: object, as_of: datetime | None = None) -> int:
    """Raw row values expire immediately once authoritative evidence is created."""

    cutoff = as_of or timezone.now()
    candidates = CandidateRecord.objects.select_for_update().filter(
        batch_id=batch_id,
        raw_payload_purged_at__isnull=True,
    )
    return candidates.update(raw_payload={}, raw_payload_purged_at=cutoff, updated_at=cutoff)


def purge_expired_raw_artifacts(*, as_of: datetime | None = None) -> int:
    """Delete expired bytes with a retryable two-phase database state."""

    cutoff = as_of or timezone.now()
    with transaction.atomic():
        artifacts = list(
            RawArtifact.objects.select_for_update()
            .filter(content_purged_at__isnull=True)
            .filter(
                models.Q(content_expires_at__lte=cutoff)
                | models.Q(status=ImportArtifactStatus.PURGE_PENDING.value)
            )
            .order_by("content_expires_at", "id")
        )
        RawArtifact.objects.filter(pk__in=[artifact.pk for artifact in artifacts]).update(
            status=ImportArtifactStatus.PURGE_PENDING.value,
            updated_at=cutoff,
        )
    purged = 0
    for artifact in artifacts:
        delete_artifact(artifact.storage_key)
        with transaction.atomic():
            locked = RawArtifact.objects.select_for_update().get(pk=artifact.pk)
            if locked.content_purged_at is not None:
                continue
            locked.storage_key = ""
            locked.status = ImportArtifactStatus.PURGED.value
            locked.content_purged_at = cutoff
            locked.save(update_fields=["storage_key", "status", "content_purged_at", "updated_at"])
            locked.batch.storage_key = ""
            locked.batch.save(update_fields=["storage_key", "updated_at"])
            purged += 1
    return purged
