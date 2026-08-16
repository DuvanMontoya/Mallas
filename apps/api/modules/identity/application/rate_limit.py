from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction

from modules.identity.models import RateLimitBucket


def _digest(value: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"), value.strip().lower().encode("utf-8"), hashlib.sha256
    ).hexdigest()


def _window_start(now: datetime, window_seconds: int) -> datetime:
    timestamp = int(now.timestamp())
    return datetime.fromtimestamp(
        timestamp - timestamp % window_seconds,
        tz=UTC,
    )


@transaction.atomic  # type: ignore[untyped-decorator]
def consume_rate_limit(*, key: str, action: str, limit: int, window_seconds: int = 60) -> bool:
    """Consume one fixed-window token using a shared transactional counter."""

    if limit < 1 or window_seconds < 1:
        raise ValueError("Rate-limit limit and window must be positive")
    now = datetime.now(UTC)
    window = _window_start(now, window_seconds)
    identity = {
        "key_hash": _digest(key),
        "action": action,
        "window_started_at": window,
    }
    try:
        # A nested savepoint lets a concurrent first request lose the unique
        # insert race without poisoning the caller's outer transaction.
        with transaction.atomic():
            bucket, _ = RateLimitBucket.objects.select_for_update().get_or_create(
                **identity,
                defaults={"attempts": 0},
            )
    except IntegrityError:
        bucket = RateLimitBucket.objects.select_for_update().get(**identity)
    if bucket.attempts >= limit:
        return False
    bucket.attempts += 1
    bucket.save(update_fields=["attempts", "updated_at"])
    return True


def purge_expired_rate_limit_buckets(*, older_than_seconds: int = 3600) -> int:
    cutoff = datetime.now(UTC) - timedelta(seconds=older_than_seconds)
    deleted, _ = RateLimitBucket.objects.filter(window_started_at__lt=cutoff).delete()
    return deleted
