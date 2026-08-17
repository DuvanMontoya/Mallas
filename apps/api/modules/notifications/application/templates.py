from __future__ import annotations

from dataclasses import dataclass

from domain.enums import NotificationEventType


@dataclass(frozen=True, slots=True)
class NotificationContent:
    title: str
    body: str
    title_key: str
    body_key: str
    link_path: str


_TEMPLATES: dict[str, dict[str, NotificationContent]] = {
    NotificationEventType.CURRICULUM_REVISION_PUBLISHED.value: {
        "es-CO": NotificationContent(
            title="Cambio curricular publicado",
            body=(
                "Se publicó una revisión curricular que puede requerir una revisión "
                "de tu cohorte académica."
            ),
            title_key="notifications.curriculum_revision_published.title",
            body_key="notifications.curriculum_revision_published.body",
            link_path="/audit",
        ),
        "en": NotificationContent(
            title="Curriculum change published",
            body=(
                "A curriculum revision was published and may require a review of "
                "your academic cohort."
            ),
            title_key="notifications.curriculum_revision_published.title",
            body_key="notifications.curriculum_revision_published.body",
            link_path="/audit",
        ),
    }
}


def normalize_locale(value: str | None) -> str:
    normalized = (value or "es-CO").strip().replace("_", "-")
    if normalized.lower().startswith("en"):
        return "en"
    return "es-CO"


def render_notification(event_type: str, locale: str | None) -> NotificationContent:
    options = _TEMPLATES.get(event_type)
    if options is None:
        raise ValueError(f"Unsupported notification event type: {event_type}")
    normalized_locale = normalize_locale(locale)
    return options.get(normalized_locale, options["es-CO"])


def supported_event_types() -> tuple[str, ...]:
    return tuple(_TEMPLATES)
