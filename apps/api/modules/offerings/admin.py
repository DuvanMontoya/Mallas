from django.contrib import admin

from .models import AcademicTerm, CourseOffering, Meeting, Section

admin.site.register([AcademicTerm, CourseOffering, Section, Meeting])
