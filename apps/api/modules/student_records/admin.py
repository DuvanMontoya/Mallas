from django.contrib import admin

from .models import (
    AcademicException,
    AcademicRecognition,
    CourseAttempt,
    ProgramEnrollment,
    StudentAdvisorAssignment,
    StudentProfile,
)

admin.site.register(
    [
        StudentProfile,
        StudentAdvisorAssignment,
        ProgramEnrollment,
        CourseAttempt,
        AcademicRecognition,
        AcademicException,
    ]
)
