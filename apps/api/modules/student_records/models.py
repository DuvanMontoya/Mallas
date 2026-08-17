from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from domain.enums import (
    AttemptOrigin,
    AttemptStatus,
    EnrollmentStatus,
    ExceptionStatus,
    RecognitionType,
    enum_choices,
)
from modules.common.models import UUIDTimestampedModel


class StudentProfile(UUIDTimestampedModel):
    user = models.OneToOneField(
        "identity.User", on_delete=models.PROTECT, related_name="student_profile"
    )
    institution = models.ForeignKey(
        "institutions.Institution", on_delete=models.PROTECT, related_name="student_profiles"
    )
    student_number = models.CharField(max_length=80, blank=True)
    display_name = models.CharField(max_length=240, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "student_number"],
                condition=~Q(student_number=""),
                name="student_institution_number_unique",
            )
        ]
        indexes = [
            models.Index(fields=["institution", "student_number"], name="student_inst_number_idx")
        ]

    def __str__(self) -> str:
        return self.display_name or self.user.email


class StudentAdvisorAssignment(UUIDTimestampedModel):
    """Explicit, time-bounded ownership delegation for advisor access."""

    student = models.ForeignKey(
        StudentProfile, on_delete=models.PROTECT, related_name="advisor_assignments"
    )
    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="student_assignments"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="created_student_assignments",
    )
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    rationale = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["advisor", "active"], name="advisor_assignment_active_idx"),
            models.Index(fields=["student", "active"], name="student_assignment_active_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_to__isnull=True)
                | Q(valid_from__isnull=True)
                | Q(valid_to__gte=F("valid_from")),
                name="advisor_assignment_valid_range",
            ),
        ]

    def clean(self) -> None:
        if self.student_id and self.advisor_id and self.student.user_id == self.advisor_id:
            raise ValidationError("A student cannot be assigned as their own advisor.")

    def __str__(self) -> str:
        return f"{self.advisor} → {self.student}"


class ProgramEnrollment(UUIDTimestampedModel):
    student = models.ForeignKey(
        StudentProfile, on_delete=models.PROTECT, related_name="program_enrollments"
    )
    program = models.ForeignKey(
        "institutions.Program", on_delete=models.PROTECT, related_name="student_enrollments"
    )
    plan = models.ForeignKey(
        "curriculum.CurriculumPlan", on_delete=models.PROTECT, related_name="student_enrollments"
    )
    revision_basis = models.ForeignKey(
        "curriculum.CurriculumRevision",
        on_delete=models.PROTECT,
        related_name="student_enrollments",
    )
    admission_term = models.ForeignKey(
        "offerings.AcademicTerm", on_delete=models.PROTECT, related_name="admissions"
    )
    status = models.CharField(
        max_length=24,
        choices=enum_choices(EnrollmentStatus),
        default=EnrollmentStatus.ACTIVE.value,
    )
    cohort_code = models.CharField(max_length=80, blank=True)
    transition_events = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "program", "admission_term"],
                name="enrollment_student_program_term_unique",
            )
        ]
        indexes = [
            models.Index(fields=["student", "status"], name="enrollment_student_status_idx"),
            models.Index(fields=["program", "status"], name="enrollment_program_status_idx"),
        ]

    def clean(self) -> None:
        if self.plan_id and self.plan.program_id != self.program_id:
            raise ValidationError({"plan": "Enrollment plan must belong to the selected program."})
        if self.revision_basis_id and self.revision_basis.plan_id != self.plan_id:
            raise ValidationError(
                {"revision_basis": "Revision basis must belong to the enrollment plan."}
            )
        if (
            self.student_id
            and self.program_id
            and self.student.institution_id != self.program.faculty.campus.institution_id
        ):
            raise ValidationError("Student and program must belong to the same institution.")

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.student} — {self.program.name}"


class CourseAttempt(UUIDTimestampedModel):
    enrollment = models.ForeignKey(
        ProgramEnrollment, on_delete=models.PROTECT, related_name="course_attempts"
    )
    course_version = models.ForeignKey(
        "curriculum.CourseVersion", on_delete=models.PROTECT, related_name="course_attempts"
    )
    term = models.ForeignKey(
        "offerings.AcademicTerm", on_delete=models.PROTECT, related_name="course_attempts"
    )
    attempt_number = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(
        max_length=24,
        choices=enum_choices(AttemptStatus),
        default=AttemptStatus.PLANNED.value,
    )
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    credits_earned = models.PositiveSmallIntegerField(default=0)
    origin = models.CharField(
        max_length=20,
        choices=enum_choices(AttemptOrigin),
        default=AttemptOrigin.IMPORT.value,
    )
    import_batch = models.ForeignKey(
        "imports.ImportBatch",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="course_attempts",
    )
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="entered_course_attempts",
    )
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "course_version", "attempt_number"],
                name="attempt_enrollment_course_number_unique",
            ),
            models.CheckConstraint(
                condition=Q(attempt_number__gte=1), name="attempt_number_positive"
            ),
            models.CheckConstraint(
                condition=Q(credits_earned__gte=0), name="attempt_credits_nonnegative"
            ),
        ]
        indexes = [
            models.Index(fields=["enrollment", "status"], name="attempt_enrollment_status_idx"),
            models.Index(fields=["course_version", "status"], name="attempt_course_status_idx"),
        ]

    def clean(self) -> None:
        if (
            self.term_id
            and self.enrollment_id
            and self.term.institution_id != self.enrollment.student.institution_id
        ):
            raise ValidationError("Attempt term and student institution must match.")
        if (
            self.course_version_id
            and self.enrollment_id
            and self.course_version.course.institution_id != self.enrollment.student.institution_id
        ):
            raise ValidationError("Attempt course and student institution must match.")
        if self.grade is not None and not 0 <= self.grade <= 5:
            raise ValidationError({"grade": "Grade must be between 0 and 5."})

    def __str__(self) -> str:
        return f"{self.enrollment} — {self.course_version.course.code}"


class AcademicRecognition(UUIDTimestampedModel):
    enrollment = models.ForeignKey(
        ProgramEnrollment, on_delete=models.PROTECT, related_name="recognitions"
    )
    source_course_version = models.ForeignKey(
        "curriculum.CourseVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="source_recognitions",
    )
    target_course_version = models.ForeignKey(
        "curriculum.CourseVersion", on_delete=models.PROTECT, related_name="target_recognitions"
    )
    recognition_type = models.CharField(max_length=24, choices=enum_choices(RecognitionType))
    credits_applied = models.PositiveSmallIntegerField(default=0)
    resolution_reference = models.CharField(max_length=240, blank=True)
    evidence = models.ManyToManyField(
        "governance.Evidence", blank=True, related_name="academic_recognitions"
    )
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["enrollment", "recognition_type"], name="recognition_enroll_type_idx"
            ),
            models.Index(fields=["target_course_version"], name="recognition_target_course_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.enrollment} — {self.target_course_version.course.code}"


class AcademicException(UUIDTimestampedModel):
    enrollment = models.ForeignKey(
        ProgramEnrollment, on_delete=models.PROTECT, related_name="academic_exceptions"
    )
    exception_type = models.CharField(max_length=80)
    scope = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=enum_choices(ExceptionStatus),
        default=ExceptionStatus.REQUESTED.value,
    )
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    rationale = models.TextField()
    granted_by = models.ForeignKey(
        "identity.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="granted_academic_exceptions",
    )
    evidence = models.ManyToManyField(
        "governance.Evidence", blank=True, related_name="academic_exceptions"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_to__isnull=True)
                | Q(valid_from__isnull=True)
                | Q(valid_to__gte=F("valid_from")),
                name="exception_valid_range",
            )
        ]
        indexes = [
            models.Index(fields=["enrollment", "status"], name="exception_enroll_status_idx"),
            models.Index(fields=["valid_from", "valid_to"], name="exception_validity_idx"),
        ]

    def clean(self) -> None:
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValidationError({"valid_to": "Exception must end on or after it starts."})

    def __str__(self) -> str:
        return f"{self.enrollment} — {self.exception_type}"
