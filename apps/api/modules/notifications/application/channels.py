from __future__ import annotations

from typing import Protocol

from django.conf import settings
from django.core.mail import send_mail


class EmailAdapter(Protocol):
    """Replaceable email boundary; implementations must honor idempotency_key."""

    def send(
        self,
        *,
        recipient_email: str,
        subject: str,
        body: str,
        idempotency_key: str,
    ) -> str: ...


class DjangoEmailAdapter:
    def send(
        self,
        *,
        recipient_email: str,
        subject: str,
        body: str,
        idempotency_key: str,
    ) -> str:
        del idempotency_key
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            fail_silently=False,
        )
        return "django-email"


def configured_email_adapter() -> EmailAdapter | None:
    if not getattr(settings, "NOTIFICATIONS_EMAIL_ENABLED", False):
        return None
    return DjangoEmailAdapter()
