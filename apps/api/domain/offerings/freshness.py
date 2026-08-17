from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from domain.enums import OfferingFreshness


@dataclass(frozen=True)
class Freshness:
    state: str
    retrieved_at: datetime | None
    age_seconds: int | None
    max_age_seconds: int | None


def assess_freshness(
    retrieved_at: datetime | None,
    *,
    now: datetime | None = None,
    max_age: timedelta = timedelta(hours=24),
) -> Freshness:
    if retrieved_at is None:
        return Freshness(
            state=OfferingFreshness.UNKNOWN.value,
            retrieved_at=None,
            age_seconds=None,
            max_age_seconds=int(max_age.total_seconds()),
        )
    normalized_retrieved = (
        retrieved_at.replace(tzinfo=UTC) if retrieved_at.tzinfo is None else retrieved_at
    )
    reference = now or datetime.now(UTC)
    normalized_now = reference.replace(tzinfo=UTC) if reference.tzinfo is None else reference
    age_seconds = max(0, int((normalized_now - normalized_retrieved).total_seconds()))
    return Freshness(
        state=(
            OfferingFreshness.FRESH.value
            if age_seconds <= max_age.total_seconds()
            else OfferingFreshness.STALE.value
        ),
        retrieved_at=normalized_retrieved,
        age_seconds=age_seconds,
        max_age_seconds=int(max_age.total_seconds()),
    )
