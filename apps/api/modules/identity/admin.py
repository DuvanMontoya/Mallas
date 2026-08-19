from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditEvent, PersonProfile, RateLimitBucket, RoleAssignment, User


@admin.register(User)
class IdentityUserAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "is_staff", "is_active", "date_joined"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)


@admin.register(PersonProfile)
class PersonProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "first_name", "first_surname", "data_status", "confirmed_at"]
    list_filter = ["data_status"]
    search_fields = ["user__email", "first_name", "middle_names", "first_surname", "second_surname"]
    readonly_fields = [field.name for field in PersonProfile._meta.fields]

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object | None = None) -> bool:
        return False


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "institution", "program", "active", "valid_from", "valid_to"]
    list_filter = ["role", "active"]
    search_fields = ["user__email"]

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object | None = None) -> bool:
        return False


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["created_at", "action", "actor", "object_type", "object_id"]
    list_filter = ["action", "object_type"]
    search_fields = ["object_id", "request_id"]
    readonly_fields = [field.name for field in AuditEvent._meta.fields]

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object | None = None) -> bool:
        return False


@admin.register(RateLimitBucket)
class RateLimitBucketAdmin(admin.ModelAdmin):
    list_display = ["action", "key_hash", "window_started_at", "attempts"]
    readonly_fields = [field.name for field in RateLimitBucket._meta.fields]

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object | None = None) -> bool:
        return False
