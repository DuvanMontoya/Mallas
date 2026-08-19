from typing import Any

from django.contrib import admin

from .models import (
    Course,
    CourseVersion,
    CurriculumAssignmentPolicy,
    CurriculumAssignmentPolicyEvidence,
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


admin.site.register(
    [
        CurriculumPlan,
        CurriculumAssignmentPolicyEvidence,
        Course,
        CourseVersion,
        RequirementGroup,
        PlanMembership,
    ]
)


@admin.register(CurriculumAssignmentPolicy)
class CurriculumAssignmentPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "policy_code",
        "version",
        "program",
        "context",
        "status",
        "epistemic_status",
    )
    list_filter = ("status", "epistemic_status", "context")
    search_fields = ("policy_code", "program__code", "plan__code")
    readonly_fields = (
        "status",
        "source_set_hash",
        "content_hash",
        "published_at",
        "approved_by",
        "prepared_by",
    )

    def save_model(
        self,
        request: Any,
        obj: CurriculumAssignmentPolicy,
        form: Any,
        change: bool,
    ) -> None:
        if not change and obj.prepared_by_id is None:
            obj.prepared_by = request.user
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request: object, obj: object | None = None) -> bool:
        del request, obj
        return False
