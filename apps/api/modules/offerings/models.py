from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from domain.enums import OfferingStatus, SectionModality, TermStatus, enum_choices
from modules.common.models import UUIDTimestampedModel


class AcademicTerm(UUIDTimestampedModel):
    institution = models.ForeignKey(
        "institutions.Institution", on_delete=models.PROTECT, related_name="academic_terms"
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="academic_terms",
    )
    code = models.CharField(max_length=40)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=enum_choices(TermStatus),
        default=TermStatus.PLANNED.value,
    )
    source_snapshot = models.ForeignKey(
        "governance.SourceSnapshot",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="academic_terms",
    )

    class Meta:
        ordering = ["-starts_at", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"], name="term_institution_code_unique"
            ),
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")), name="term_date_range_valid"
            ),
        ]
        indexes = [
            models.Index(
                fields=["institution", "status", "starts_at"], name="term_inst_status_start_idx"
            ),
            models.Index(fields=["source_snapshot", "starts_at"], name="term_source_start_idx"),
        ]

    def clean(self) -> None:
        if self.campus_id and self.campus.institution_id != self.institution_id:
            raise ValidationError({"campus": "Campus must belong to the term institution."})

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.institution.display_name} — {self.code}"


class CourseOffering(UUIDTimestampedModel):
    course_version = models.ForeignKey(
        "curriculum.CourseVersion", on_delete=models.PROTECT, related_name="offerings"
    )
    term = models.ForeignKey(AcademicTerm, on_delete=models.PROTECT, related_name="offerings")
    status = models.CharField(
        max_length=20,
        choices=enum_choices(OfferingStatus),
        default=OfferingStatus.PLANNED.value,
    )
    source_snapshot = models.ForeignKey(
        "governance.SourceSnapshot",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="course_offerings",
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course_version", "term"], name="offering_course_term_unique"
            )
        ]
        indexes = [
            models.Index(fields=["term", "status"], name="offering_term_status_idx"),
            models.Index(fields=["course_version", "term"], name="offering_course_term_idx"),
        ]

    def clean(self) -> None:
        if self.course_version_id and self.term_id:
            institution_id = self.course_version.course.institution_id
            if institution_id != self.term.institution_id:
                raise ValidationError(
                    "Course and academic term must belong to the same institution."
                )

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.course_version.course.code} — {self.term.code}"


class Section(UUIDTimestampedModel):
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT, related_name="sections")
    group_code = models.CharField(max_length=40)
    modality = models.CharField(
        max_length=20,
        choices=enum_choices(SectionModality),
        default=SectionModality.UNKNOWN.value,
    )
    capacity = models.PositiveIntegerField(null=True, blank=True)
    enrolled_count = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["offering", "group_code"], name="section_offering_group_unique"
            ),
            models.CheckConstraint(
                condition=Q(capacity__isnull=True)
                | Q(enrolled_count__isnull=True)
                | Q(enrolled_count__lte=F("capacity")),
                name="section_enrollment_within_capacity",
            ),
        ]
        indexes = [
            models.Index(fields=["offering", "modality"], name="section_offering_modality_idx")
        ]

    def clean(self) -> None:
        if (
            self.capacity is not None
            and self.enrolled_count is not None
            and self.enrolled_count > self.capacity
        ):
            raise ValidationError({"enrolled_count": "Enrolled count cannot exceed capacity."})

    def __str__(self) -> str:
        return f"{self.offering} — {self.group_code}"


class Meeting(UUIDTimestampedModel):
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="meetings")
    day_of_week = models.PositiveSmallIntegerField(
        choices=[
            (0, "Monday"),
            (1, "Tuesday"),
            (2, "Wednesday"),
            (3, "Thursday"),
            (4, "Friday"),
            (5, "Saturday"),
            (6, "Sunday"),
        ]
    )
    starts_at = models.TimeField()
    ends_at = models.TimeField()
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    session_code = models.CharField(max_length=40, blank=True)
    is_alternate = models.BooleanField(default=False)
    location = models.CharField(max_length=240, blank=True)
    timezone = models.CharField(max_length=64, default="America/Bogota")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")), name="meeting_time_range_valid"
            ),
            models.CheckConstraint(
                condition=Q(ends_on__isnull=True)
                | Q(starts_on__isnull=True)
                | Q(ends_on__gte=F("starts_on")),
                name="meeting_date_range_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["section", "day_of_week", "starts_at"], name="meeting_section_time_idx"
            )
        ]

    def clean(self) -> None:
        if self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "Meeting must end after it starts."})
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValidationError({"ends_on": "Meeting date range must not end before it starts."})

    def __str__(self) -> str:
        return f"{self.section} — day {self.day_of_week}"
