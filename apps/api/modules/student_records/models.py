from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import F, Q

from domain.enums import (
    AttemptOrigin,
    AttemptStatus,
    CurriculumAssignmentDecisionStatus,
    CurriculumAssignmentMethod,
    EnrollmentStatus,
    ExceptionStatus,
    RecognitionType,
    enum_choices,
)
from domain.errors import CurriculumAssignmentDecisionImmutableError
from modules.common.models import UUIDTimestampedModel


class StudentProfile(UUIDTimestampedModel):
    user = models.OneToOneField(
        "identity.User", on_delete=models.PROTECT, related_name="student_profile"
    )
    institution = models.ForeignKey(
        "institutions.Institution", on_delete=models.PROTECT, related_name="student_profiles"
    )
    student_number = models.CharField(max_length=80, blank=True)
    legacy_display_name = models.CharField(max_length=240, blank=True)
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

    @property
    def display_name(self) -> str:
        try:
            person = self.user.person_profile
        except ObjectDoesNotExist:
            return self.legacy_display_name
        return person.full_name or person.preferred_name or self.legacy_display_name

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


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
        "curriculum.CurriculumPlan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="student_enrollments",
    )
    revision_basis = models.ForeignKey(
        "curriculum.CurriculumRevision",
        null=True,
        blank=True,
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
    review_reasons = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "program", "admission_term"],
                name="enrollment_student_program_term_unique",
            ),
            models.CheckConstraint(
                condition=(Q(plan__isnull=True) & Q(revision_basis__isnull=True))
                | (Q(plan__isnull=False) & Q(revision_basis__isnull=False)),
                name="enrollment_plan_revision_both_or_neither",
            ),
            models.CheckConstraint(
                condition=Q(status=EnrollmentStatus.NEEDS_REVIEW.value)
                | (Q(plan__isnull=False) & Q(revision_basis__isnull=False)),
                name="enrollment_resolved_status_has_curriculum",
            ),
            models.CheckConstraint(
                condition=(Q(status=EnrollmentStatus.NEEDS_REVIEW.value) & ~Q(review_reasons=[]))
                | (~Q(status=EnrollmentStatus.NEEDS_REVIEW.value) & Q(review_reasons=[])),
                name="enrollment_review_status_matches_reasons",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "status"], name="enrollment_student_status_idx"),
            models.Index(fields=["program", "status"], name="enrollment_program_status_idx"),
        ]

    def clean(self) -> None:
        if not isinstance(self.review_reasons, list) or any(
            not isinstance(reason, str) or not reason.strip() for reason in self.review_reasons
        ):
            raise ValidationError(
                {"review_reasons": "Review reasons must be a list of non-empty codes."}
            )
        if len(self.review_reasons) != len(set(self.review_reasons)):
            raise ValidationError({"review_reasons": "Review reasons cannot be duplicated."})
        requires_review = self.status == EnrollmentStatus.NEEDS_REVIEW.value
        if requires_review != bool(self.review_reasons):
            raise ValidationError(
                {"review_reasons": "Review reasons must match the enrollment review status."}
            )
        if self.plan_id is None and "CURRICULUM_ASSIGNMENT" not in self.review_reasons:
            raise ValidationError(
                {"review_reasons": "An unresolved curriculum requires assignment review."}
            )
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


class StudentOnboarding(UUIDTimestampedModel):
    class HistoryStepStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IMPORTED = "IMPORTED", "Imported"
        SKIPPED = "SKIPPED", "Skipped for now"

    class TourStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        SKIPPED = "SKIPPED", "Skipped"

    enrollment = models.OneToOneField(
        ProgramEnrollment, on_delete=models.PROTECT, related_name="onboarding"
    )
    identity_confirmed_at = models.DateTimeField(null=True, blank=True)
    history_step_status = models.CharField(
        max_length=16,
        choices=HistoryStepStatus.choices,
        default=HistoryStepStatus.PENDING,
    )
    current_term = models.ForeignKey(
        "offerings.AcademicTerm",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="student_onboarding_selections",
    )
    planning_load_target = models.PositiveSmallIntegerField(null=True, blank=True)
    tour_status = models.CharField(
        max_length=16,
        choices=TourStatus.choices,
        default=TourStatus.PENDING,
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(planning_load_target__isnull=True)
                | Q(planning_load_target__gte=1, planning_load_target__lte=30),
                name="onboarding_planning_load_target_range",
            )
        ]

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None


class CurriculumAssignmentOverrideAuthorization(UUIDTimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    enrollment = models.ForeignKey(
        ProgramEnrollment,
        on_delete=models.PROTECT,
        related_name="assignment_override_authorizations",
    )
    plan = models.ForeignKey(
        "curriculum.CurriculumPlan",
        on_delete=models.PROTECT,
        related_name="assignment_override_authorizations",
    )
    revision_basis = models.ForeignKey(
        "curriculum.CurriculumRevision",
        on_delete=models.PROTECT,
        related_name="assignment_override_authorizations",
    )
    reason_code = models.CharField(max_length=120)
    evidence = models.ForeignKey(
        "governance.Evidence",
        on_delete=models.PROTECT,
        related_name="assignment_override_authorizations",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="prepared_assignment_override_authorizations",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approved_assignment_override_authorizations",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    revision_content_hash = models.CharField(max_length=128, blank=True)
    revision_source_set_hash = models.CharField(max_length=128, blank=True)
    sealed_snapshot_id = models.UUIDField(null=True, blank=True)
    sealed_snapshot_sha256 = models.CharField(max_length=64, blank=True)
    sealed_storage_key_hash = models.CharField(max_length=64, blank=True)
    sealed_excerpt_hash = models.CharField(max_length=128, blank=True)
    content_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["enrollment", "status"], name="asg_ovr_auth_enroll_idx"
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(status="APPROVED")
                | (
                    Q(approved_by__isnull=False)
                    & Q(approved_at__isnull=False)
                    & ~Q(content_hash="")
                    & ~Q(revision_content_hash="")
                    & ~Q(revision_source_set_hash="")
                    & Q(sealed_snapshot_id__isnull=False)
                    & ~Q(sealed_snapshot_sha256="")
                    & ~Q(sealed_storage_key_hash="")
                    & ~Q(sealed_excerpt_hash="")
                ),
                name="assignment_override_approved_is_sealed",
            ),
            models.CheckConstraint(
                condition=Q(approved_by__isnull=True) | ~Q(approved_by=F("prepared_by")),
                name="assignment_override_separates_approval",
            ),
        ]

    def clean(self) -> None:
        if self.plan_id and self.plan.program_id != self.enrollment.program_id:
            raise ValidationError({"plan": "Override plan must belong to the enrollment program."})
        if self.revision_basis_id and self.revision_basis.plan_id != self.plan_id:
            raise ValidationError({"revision_basis": "Override revision must belong to its plan."})
        if self.approved_by_id and self.approved_by_id == self.prepared_by_id:
            raise ValidationError({"approved_by": "A different person must approve the override."})

    def save(self, *args: object, **kwargs: object) -> None:
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).first()
            if previous and previous.status == self.Status.APPROVED:
                raise ValidationError("An approved curriculum override authorization is immutable.")
        self.full_clean()
        super().save(*args, **kwargs)


class CurriculumAssignmentDecision(UUIDTimestampedModel):
    enrollment = models.ForeignKey(
        ProgramEnrollment, on_delete=models.PROTECT, related_name="assignment_decisions"
    )
    policy = models.ForeignKey(
        "curriculum.CurriculumAssignmentPolicy",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assignment_decisions",
    )
    status = models.CharField(
        max_length=24, choices=enum_choices(CurriculumAssignmentDecisionStatus)
    )
    method = models.CharField(max_length=24, choices=enum_choices(CurriculumAssignmentMethod))
    resolver_version = models.CharField(max_length=32)
    input_data = models.JSONField()
    reason_codes = models.JSONField(default=list)
    candidates = models.JSONField(default=list, blank=True)
    selected_plan = models.ForeignKey(
        "curriculum.CurriculumPlan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assignment_decisions",
    )
    selected_revision = models.ForeignKey(
        "curriculum.CurriculumRevision",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assignment_decisions",
    )
    decision_hash = models.CharField(max_length=64)
    override_reason_code = models.CharField(max_length=120, blank=True)
    override_evidence = models.ForeignKey(
        "governance.Evidence",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="curriculum_assignment_override_decisions",
    )
    override_authorization = models.ForeignKey(
        "student_records.CurriculumAssignmentOverrideAuthorization",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assignment_decisions",
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="curriculum_assignment_decisions",
    )

    class Meta:
        ordering = ["enrollment", "created_at", "id"]
        indexes = [
            models.Index(
                fields=["enrollment", "-created_at"], name="assignment_decision_enroll_idx"
            ),
            models.Index(fields=["decision_hash"], name="assignment_decision_hash_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(status=CurriculumAssignmentDecisionStatus.RESOLVED.value)
                | (
                    Q(selected_plan__isnull=False)
                    & Q(selected_revision__isnull=False)
                    & (
                        Q(policy__isnull=False)
                        | (
                            Q(method=CurriculumAssignmentMethod.ADMIN_OVERRIDE.value)
                            & Q(override_evidence__isnull=False)
                            & Q(override_authorization__isnull=False)
                        )
                    )
                ),
                name="assignment_resolved_has_policy_target",
            ),
            models.CheckConstraint(
                condition=~Q(method=CurriculumAssignmentMethod.AUTOMATIC.value)
                | Q(status=CurriculumAssignmentDecisionStatus.RESOLVED.value),
                name="assignment_automatic_is_resolved",
            ),
            models.CheckConstraint(
                condition=(Q(selected_plan__isnull=True) & Q(selected_revision__isnull=True))
                | (Q(selected_plan__isnull=False) & Q(selected_revision__isnull=False)),
                name="assignment_selected_target_both_or_neither",
            ),
            models.CheckConstraint(
                condition=~Q(method=CurriculumAssignmentMethod.ADMIN_OVERRIDE.value)
                | (
                    Q(decided_by__isnull=False)
                    & ~Q(override_reason_code="")
                    & Q(override_evidence__isnull=False)
                    & Q(override_authorization__isnull=False)
                    & Q(selected_plan__isnull=False)
                    & Q(selected_revision__isnull=False)
                ),
                name="assignment_override_has_actor_reason_target",
            ),
        ]

    def clean(self) -> None:
        if self.selected_plan_id and self.selected_plan.program_id != self.enrollment.program_id:
            raise ValidationError(
                {"selected_plan": "Assignment decision plan must belong to the enrollment program."}
            )
        if self.selected_revision_id and self.selected_revision.plan_id != self.selected_plan_id:
            raise ValidationError(
                {"selected_revision": "Assignment decision revision must belong to its plan."}
            )
        if self.policy_id and (
            self.policy.plan_id != self.selected_plan_id
            or self.policy.revision_basis_id != self.selected_revision_id
        ):
            raise ValidationError(
                {"policy": "Assignment decision target must match the selected policy."}
            )

    def save(self, *args: object, **kwargs: object) -> None:
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise CurriculumAssignmentDecisionImmutableError(
                "Curriculum assignment decisions are append-only."
            )
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise CurriculumAssignmentDecisionImmutableError(
            "Curriculum assignment decisions cannot be deleted."
        )


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

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

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
