from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from .enums import RevisionStatus
from .errors import PublishedRevisionImmutableError


def canonical_content_hash(content: Mapping[str, object]) -> str:
    """Hash revision content deterministically for audit and publication."""

    payload = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assert_revision_content_mutable(status: str, changed: bool) -> None:
    if status == RevisionStatus.PUBLISHED.value and changed:
        raise PublishedRevisionImmutableError("Published curriculum revisions are immutable")
