from __future__ import annotations

import datetime
from typing import Any

from django.contrib.auth import get_user_model

from domain.enums import RequirementGroupKind
from modules.curriculum.models import (
    Course,
    CourseVersion,
    CurriculumPlan,
    CurriculumRevision,
    RequirementGroup,
)
from modules.institutions.models import Campus, Faculty, Institution, Program
from modules.offerings.models import AcademicTerm
from modules.student_records.models import ProgramEnrollment, StudentProfile


def foundation(*, suffix: str = "") -> dict[str, Any]:
    institution = Institution.objects.create(
        slug=f"test-university{suffix}",
        legal_name="Test University S.A.",
        display_name="Test University",
    )
    campus = Campus.objects.create(institution=institution, code=f"BOG{suffix}", name="Bogotá")
    faculty = Faculty.objects.create(campus=campus, code=f"SCI{suffix}", name="Sciences")
    program = Program.objects.create(
        faculty=faculty,
        code=f"STAT{suffix}",
        name="Statistics",
        degree_name="Statistician",
        estimated_terms=9,
    )
    plan = CurriculumPlan.objects.create(program=program, code=f"2514{suffix}", title="Plan 2514")
    revision = CurriculumRevision.objects.create(
        plan=plan,
        revision_code=f"2023{suffix}",
        effective_from=datetime.date(2023, 1, 1),
        total_required_credits=141,
    )
    course = Course.objects.create(institution=institution, code=f"STAT101{suffix}")
    course_version = CourseVersion.objects.create(
        course=course,
        name="Introduction to Statistics",
        credits=4,
        valid_from=datetime.date(2023, 1, 1),
    )
    group = RequirementGroup.objects.create(
        revision=revision,
        code=f"CORE{suffix}",
        label="Core",
        kind=RequirementGroupKind.COMPONENT.value,
        required_credits=4,
    )
    term = AcademicTerm.objects.create(
        institution=institution,
        campus=campus,
        code=f"2026-1{suffix}",
        starts_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        ends_at=datetime.datetime(2026, 6, 30, tzinfo=datetime.UTC),
    )
    user = get_user_model().objects.create_user(
        email=f"student{suffix}@example.test", password="safe-test-password"
    )
    student = StudentProfile.objects.create(
        user=user,
        institution=institution,
        student_number=f"S{suffix or '0'}",
        display_name="Test Student",
    )
    enrollment = ProgramEnrollment.objects.create(
        student=student,
        program=program,
        plan=plan,
        revision_basis=revision,
        admission_term=term,
    )
    return locals()
