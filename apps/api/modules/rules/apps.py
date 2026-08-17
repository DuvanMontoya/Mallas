from django.apps import AppConfig
from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed


class RulesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.rules"
    label = "rules"

    def ready(self) -> None:
        from modules.curriculum.models import CurriculumRevision

        from .models import Requirement

        def protect_requirement_evidence(
            sender: object,
            instance: Requirement,
            action: str,
            **kwargs: object,
        ) -> None:
            del sender, kwargs
            if action not in {"pre_add", "pre_remove", "pre_clear"}:
                return
            status = (
                CurriculumRevision.objects.filter(pk=instance.revision_id)
                .values_list("status", flat=True)
                .first()
            )
            if status in {
                "PUBLISHED",
                "SUPERSEDED",
                "RETIRED",
            }:
                raise ValidationError(
                    "Evidence links for published, superseded, or retired requirements are immutable."
                )

        m2m_changed.connect(
            protect_requirement_evidence,
            sender=Requirement.evidence.through,
            dispatch_uid="rules.protect_published_requirement_evidence",
            weak=False,
        )
