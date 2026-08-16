from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from domain.enums import UserRole, enum_choices
from domain.errors import AuditEventImmutableError
from modules.common.models import UUIDTimestampedModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra_fields: object) -> User:
        if not email:
            raise ValueError("The email field is required.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: object
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email


class RoleAssignment(UUIDTimestampedModel):
    """Time-bounded role assignment with optional institutional scope."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="role_assignments"
    )
    role = models.CharField(max_length=24, choices=enum_choices(UserRole))
    institution = models.ForeignKey(
        "institutions.Institution",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="role_assignments",
    )
    program = models.ForeignKey(
        "institutions.Program",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="role_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="granted_role_assignments",
    )
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    rationale = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "role", "active"], name="role_user_active_idx"),
            models.Index(fields=["institution", "role"], name="role_institution_idx"),
            models.Index(fields=["program", "role"], name="role_program_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_to__isnull=True)
                | Q(valid_from__isnull=True)
                | Q(valid_to__gte=F("valid_from")),
                name="role_assignment_valid_range",
            ),
        ]

    def clean(self) -> None:
        if self.program_id and not self.institution_id:
            raise ValidationError({"institution": "A program-scoped role requires an institution."})
        if (
            self.program_id
            and self.institution_id
            and self.program
            and self.program.faculty.campus.institution_id != self.institution_id
        ):
            raise ValidationError(
                {"program": "The program must belong to the selected institution."}
            )

    def __str__(self) -> str:
        scope = self.program or self.institution or "global"
        return f"{self.user.email} — {self.role} — {scope}"


class AuditEvent(UUIDTimestampedModel):
    """Append-only record for authentication, authorization and governance actions."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_events",
    )
    action = models.CharField(max_length=120)
    object_type = models.CharField(max_length=120, blank=True)
    object_id = models.CharField(max_length=80, blank=True)
    institution = models.ForeignKey(
        "institutions.Institution",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_events",
    )
    request_id = models.CharField(max_length=80, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["action", "created_at"], name="audit_event_action_idx"),
            models.Index(fields=["actor", "created_at"], name="audit_event_actor_idx"),
            models.Index(fields=["object_type", "object_id"], name="audit_event_object_idx"),
        ]

    def save(self, *args: object, **kwargs: object) -> None:
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise AuditEventImmutableError("Audit events are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise AuditEventImmutableError("Audit events cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.created_at.isoformat()} — {self.action}"


class RateLimitBucket(UUIDTimestampedModel):
    """Database-backed fixed-window counter shared across API workers."""

    key_hash = models.CharField(max_length=64)
    action = models.CharField(max_length=80)
    window_started_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["key_hash", "action", "window_started_at"],
                name="rate_limit_bucket_identity_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["action", "window_started_at"], name="rate_limit_action_window_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.action}:{self.key_hash[:12]}"
