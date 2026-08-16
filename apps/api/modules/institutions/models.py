from __future__ import annotations

from django.db import models

from domain.enums import InstitutionStatus, enum_choices
from modules.common.models import UUIDTimestampedModel


class Institution(UUIDTimestampedModel):
    slug = models.SlugField(max_length=100, unique=True)
    legal_name = models.CharField(max_length=240)
    display_name = models.CharField(max_length=160)
    country_code = models.CharField(max_length=2, default="CO")
    status = models.CharField(
        max_length=20,
        choices=enum_choices(InstitutionStatus),
        default=InstitutionStatus.ACTIVE.value,
    )

    class Meta:
        ordering = ["display_name"]
        indexes = [models.Index(fields=["status", "display_name"], name="inst_status_name_idx")]

    def __str__(self) -> str:
        return self.display_name


class Campus(UUIDTimestampedModel):
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="campuses")
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=160)
    timezone = models.CharField(max_length=64, default="America/Bogota")
    status = models.CharField(
        max_length=20,
        choices=enum_choices(InstitutionStatus),
        default=InstitutionStatus.ACTIVE.value,
    )

    class Meta:
        ordering = ["institution__display_name", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"], name="campus_institution_code_unique"
            )
        ]
        indexes = [models.Index(fields=["institution", "status"], name="campus_inst_status_idx")]

    def __str__(self) -> str:
        return f"{self.institution.display_name} — {self.name}"


class Faculty(UUIDTimestampedModel):
    campus = models.ForeignKey(Campus, on_delete=models.PROTECT, related_name="faculties")
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=160)
    status = models.CharField(
        max_length=20,
        choices=enum_choices(InstitutionStatus),
        default=InstitutionStatus.ACTIVE.value,
    )

    class Meta:
        ordering = ["campus__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["campus", "code"], name="faculty_campus_code_unique")
        ]
        indexes = [models.Index(fields=["campus", "status"], name="faculty_campus_status_idx")]

    def __str__(self) -> str:
        return f"{self.campus.name} — {self.name}"


class Program(UUIDTimestampedModel):
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="programs")
    code = models.CharField(max_length=60)
    snies = models.CharField(max_length=40, blank=True)
    name = models.CharField(max_length=200)
    degree_name = models.CharField(max_length=200)
    estimated_terms = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=enum_choices(InstitutionStatus),
        default=InstitutionStatus.ACTIVE.value,
    )

    class Meta:
        ordering = ["faculty__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["faculty", "code"], name="program_faculty_code_unique")
        ]
        indexes = [models.Index(fields=["faculty", "status"], name="program_faculty_status_idx")]

    def __str__(self) -> str:
        return self.name
