from __future__ import annotations

from typing import Any
from uuid import UUID

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.security import django_auth

from modules.common.api import ApiProblemError, with_problem_responses

from .application.services import (
    NotificationError,
    list_in_app_notifications,
    list_preferences,
    mark_all_notifications_read,
    mark_notification_read,
    update_preference,
)

router = Router(tags=["Notifications"])


class NotificationView(Schema):
    id: UUID
    event_id: UUID
    event_type: str
    channel: str
    status: str
    title: str
    body: str
    locale: str
    link_path: str
    read_at: Any
    created_at: Any
    delivered_at: Any


class NotificationCollectionView(Schema):
    items: list[NotificationView]
    unread_count: int
    next_cursor: str | None


class NotificationPreferenceView(Schema):
    event_type: str
    in_app_enabled: bool
    email_enabled: bool
    locale: str


class NotificationPreferenceCollectionView(Schema):
    items: list[NotificationPreferenceView]


class NotificationPreferencePayload(Schema):
    in_app_enabled: bool
    email_enabled: bool
    locale: str = "es-CO"


class NotificationReadAllView(Schema):
    marked_read: int


def _error(error: NotificationError) -> ApiProblemError:
    status = 404 if error.code == "notification_not_found" else 400
    return ApiProblemError(
        status=status,
        code=error.code.upper(),
        title="Notification request failed",
        detail=str(error),
    )


@router.get(
    "/notifications", auth=django_auth, response=with_problem_responses(NotificationCollectionView)
)
def notifications(
    request: HttpRequest,
    unread_only: bool = False,
    limit: int = 50,
    before: str | None = None,
) -> dict[str, Any]:
    if limit < 1 or limit > 100:
        raise ApiProblemError(
            status=400,
            code="NOTIFICATION_LIMIT_INVALID",
            title="Invalid notification limit",
            detail="limit must be between 1 and 100.",
        )
    try:
        return list_in_app_notifications(
            request.auth, unread_only=unread_only, limit=limit, before=before
        )
    except NotificationError as error:
        raise _error(error) from error


@router.post(
    "/notifications/read-all",
    auth=django_auth,
    response=with_problem_responses(NotificationReadAllView),
)
def notifications_read_all(request: HttpRequest) -> dict[str, int]:
    return {"marked_read": mark_all_notifications_read(request.auth)}


@router.post(
    "/notifications/{delivery_id}/read",
    auth=django_auth,
    response=with_problem_responses(NotificationView),
)
def notification_read(request: HttpRequest, delivery_id: UUID) -> dict[str, Any]:
    try:
        return mark_notification_read(request.auth, delivery_id)
    except NotificationError as error:
        raise _error(error) from error


@router.get(
    "/notifications/preferences",
    auth=django_auth,
    response=with_problem_responses(NotificationPreferenceCollectionView),
)
def notification_preferences(request: HttpRequest) -> dict[str, Any]:
    return {"items": list_preferences(request.auth)}


@router.put(
    "/notifications/preferences/{event_type}",
    auth=django_auth,
    response=with_problem_responses(NotificationPreferenceView),
)
def notification_preference_update(
    request: HttpRequest,
    event_type: str,
    payload: NotificationPreferencePayload,
) -> dict[str, Any]:
    try:
        return update_preference(
            request.auth,
            event_type,
            in_app_enabled=payload.in_app_enabled,
            email_enabled=payload.email_enabled,
            locale=payload.locale,
        )
    except NotificationError as error:
        raise _error(error) from error
