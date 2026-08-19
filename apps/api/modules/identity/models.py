from __future__ import annotations

from datetime import date

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import connection, models
from django.db.models import F, Q
from django.utils import timezone

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
    must_change_password = models.BooleanField(default=False)
    initial_password_expires_at = models.DateTimeField(null=True, blank=True)
    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email


class IdentityDataStatus(models.TextChoices):
    CONFIRMED = "CONFIRMED", "Confirmed"
    LEGACY_UNSTRUCTURED = "LEGACY_UNSTRUCTURED", "Legacy unstructured"
    NEEDS_REVIEW = "NEEDS_REVIEW", "Needs review"


class BirthDatePurpose(models.TextChoices):
    ACADEMIC_ADMINISTRATION = "ACADEMIC_ADMINISTRATION", "Academic administration"


class IdentityVerificationMethod(models.TextChoices):
    LEGACY_UNKNOWN = "LEGACY_UNKNOWN", "Legacy or unknown"
    PREEXISTING_UNCLASSIFIED = "PREEXISTING_UNCLASSIFIED", "Preexisting unclassified"
    SELF_DECLARED = "SELF_DECLARED", "Self declared"
    INSTITUTION_VERIFIED = "INSTITUTION_VERIFIED", "Institution verified"


class PersonProfile(UUIDTimestampedModel):
    """Private person identity, separate from authentication and academic records."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="person_profile"
    )
    first_name = models.CharField(max_length=80, blank=True)
    middle_names = models.CharField(max_length=160, blank=True)
    first_surname = models.CharField(max_length=80, blank=True)
    second_surname = models.CharField(max_length=80, blank=True)
    preferred_name = models.CharField(max_length=160, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    birth_date_purpose = models.CharField(
        max_length=48, choices=BirthDatePurpose.choices, blank=True
    )
    birth_date_retention_until = models.DateField(null=True, blank=True)
    data_status = models.CharField(
        max_length=32,
        choices=IdentityDataStatus.choices,
        default=IdentityDataStatus.NEEDS_REVIEW,
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    verification_method = models.CharField(
        max_length=32,
        choices=IdentityVerificationMethod.choices,
        default=IdentityVerificationMethod.LEGACY_UNKNOWN,
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["first_surname", "second_surname", "first_name", "user__email"]
        indexes = [
            models.Index(fields=["first_surname", "first_name"], name="person_surname_name_idx"),
            models.Index(fields=["data_status"], name="person_data_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~Q(data_status=IdentityDataStatus.CONFIRMED)
                    | (
                        ~Q(first_name="")
                        & ~Q(first_surname="")
                        & Q(confirmed_at__isnull=False)
                        & ~Q(verification_method=IdentityVerificationMethod.LEGACY_UNKNOWN)
                    )
                ),
                name="person_confirmed_identity_complete",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        birth_date__isnull=True,
                        birth_date_purpose="",
                        birth_date_retention_until__isnull=True,
                    )
                    | (Q(birth_date__isnull=False) & ~Q(birth_date_purpose=""))
                ),
                name="person_birth_date_has_purpose",
            ),
        ]

    @staticmethod
    def _normalize_part(value: str) -> str:
        return " ".join(value.split())

    @property
    def full_name(self) -> str:
        return " ".join(
            part
            for part in (
                self.first_name,
                self.middle_names,
                self.first_surname,
                self.second_surname,
            )
            if part
        )

    def age_on(self, reference_date: date | None = None) -> int | None:
        if self.birth_date is None:
            return None
        reference = reference_date or timezone.localdate()
        return (
            reference.year
            - self.birth_date.year
            - ((reference.month, reference.day) < (self.birth_date.month, self.birth_date.day))
        )

    def clean(self) -> None:
        for field in (
            "first_name",
            "middle_names",
            "first_surname",
            "second_surname",
            "preferred_name",
        ):
            setattr(self, field, self._normalize_part(getattr(self, field)))
        if self.data_status == IdentityDataStatus.CONFIRMED and (
            not self.first_name or not self.first_surname
        ):
            raise ValidationError(
                {"data_status": "Confirmed identity requires first name and first surname."}
            )
        if (
            self.data_status == IdentityDataStatus.CONFIRMED
            and self.verification_method == IdentityVerificationMethod.LEGACY_UNKNOWN
        ):
            raise ValidationError(
                {"verification_method": "Confirmed identity requires a verification method."}
            )
        if self.data_status == IdentityDataStatus.CONFIRMED and self.confirmed_at is None:
            self.confirmed_at = timezone.now()
        if self.birth_date is not None:
            today = timezone.localdate()
            if self.birth_date > today:
                raise ValidationError({"birth_date": "Birth date cannot be in the future."})
            calculated_age = self.age_on(today)
            if calculated_age is not None and calculated_age > 120:
                raise ValidationError({"birth_date": "Birth date is outside the supported range."})
            if not self.birth_date_purpose:
                raise ValidationError(
                    {"birth_date_purpose": "A collection purpose is required for birth date."}
                )
        elif self.birth_date_purpose or self.birth_date_retention_until:
            raise ValidationError(
                {"birth_date": "Birth date is required when retention or purpose is recorded."}
            )
        if (
            self.birth_date_retention_until is not None
            and self.birth_date_retention_until < timezone.localdate()
        ):
            raise ValidationError(
                {"birth_date_retention_until": "Retention date cannot already be expired."}
            )

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.full_name or self.preferred_name or self.user.email


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

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        scope = self.program or self.institution or "global"
        return f"{self.user.email} — {self.role} — {scope}"


class AuditEventQuerySet(models.QuerySet):
    """Prevent ORM bulk APIs from bypassing the append-only model contract."""

    def update(self, **kwargs: object) -> int:
        if connection.vendor == "postgresql":
            return super().update(**kwargs)
        del kwargs
        raise AuditEventImmutableError("Audit events are append-only.")

    def delete(self) -> tuple[int, dict[str, int]]:
        if connection.vendor == "postgresql":
            return super().delete()
        raise AuditEventImmutableError("Audit events cannot be deleted.")


class AuditEventManager(models.Manager):
    """Manager exposing only append-only query operations."""

    def get_queryset(self) -> AuditEventQuerySet:
        return AuditEventQuerySet(self.model, using=self._db)


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
    objects = AuditEventManager()

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
