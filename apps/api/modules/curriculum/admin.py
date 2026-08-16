from django.contrib import admin

from .models import (
    Course,
    CourseVersion,
    CurriculumPlan,
    CurriculumRevision,
    PlanMembership,
    RequirementGroup,
)


@admin.register(CurriculumRevision)
class CurriculumRevisionAdmin(admin.ModelAdmin):
    list_display = ("plan", "revision_code", "status", "effective_from", "published_at")
    list_filter = ("status",)
    search_fields = ("plan__code", "revision_code")

    def get_readonly_fields(
        self, request: object, obj: CurriculumRevision | None = None
    ) -> tuple[str, ...]:
        del request
        if obj and obj.status == "PUBLISHED":
            return tuple(field.name for field in obj._meta.fields if field.name != "status")
        return ()


admin.site.register([CurriculumPlan, Course, CourseVersion, RequirementGroup, PlanMembership])
