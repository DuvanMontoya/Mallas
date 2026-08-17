from django.contrib import admin

from .models import AcademicTerm, CourseOffering, Meeting, Section


@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ("code", "institution", "campus", "starts_at", "ends_at", "status")
    list_filter = ("status", "institution", "campus")
    search_fields = ("code", "institution__display_name", "campus__name")
    readonly_fields = ("source_snapshot", "created_at", "updated_at")


@admin.register(CourseOffering)
class CourseOfferingAdmin(admin.ModelAdmin):
    list_display = ("course_version", "term", "status", "source_snapshot")
    list_filter = ("status", "term")
    search_fields = ("course_version__course__code", "course_version__name", "term__code")
    readonly_fields = ("source_snapshot", "created_at", "updated_at")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("offering", "group_code", "modality", "capacity", "enrolled_count")
    list_filter = ("modality", "offering__term")
    search_fields = ("group_code", "offering__course_version__course__code")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("section", "day_of_week", "starts_at", "ends_at", "timezone", "is_alternate")
    list_filter = ("day_of_week", "is_alternate", "timezone")
    search_fields = ("section__group_code", "section__offering__course_version__course__code")
    readonly_fields = ("created_at", "updated_at")
