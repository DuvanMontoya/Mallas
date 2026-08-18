from __future__ import annotations

from datetime import datetime

from django.db import transaction
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


@transaction.atomic  # type: ignore[untyped-decorator]
def purge_expired_raw_artifacts(*, as_of: datetime | None = None) -> int:
    """Delete expired source bytes while retaining their hash and audit metadata."""

    cutoff = as_of or timezone.now()
    artifacts = list(
        RawArtifact.objects.select_for_update().filter(
            content_expires_at__lte=cutoff,
            content_purged_at__isnull=True,
        )
    )
    for artifact in artifacts:
        delete_artifact(artifact.storage_key)
        artifact.storage_key = ""
        artifact.status = ImportArtifactStatus.PURGED.value
        artifact.content_purged_at = cutoff
        artifact.save(update_fields=["storage_key", "status", "content_purged_at", "updated_at"])
    return len(artifacts)
