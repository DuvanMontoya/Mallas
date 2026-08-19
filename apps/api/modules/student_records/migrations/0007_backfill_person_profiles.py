from django.db import migrations


def backfill_person_profiles(apps, schema_editor):  # type: ignore[no-untyped-def]
    StudentProfile = apps.get_model("student_records", "StudentProfile")
    PersonProfile = apps.get_model("identity", "PersonProfile")
    for student in StudentProfile.objects.order_by("id").iterator():
        PersonProfile.objects.get_or_create(
            user_id=student.user_id,
            defaults={
                "data_status": "LEGACY_UNSTRUCTURED",
                "metadata": {
                    "backfilled_from_student_profile": str(student.pk),
                    "legacy_display_name_preserved": True,
                },
            },
        )


def reverse_backfill(apps, schema_editor):  # type: ignore[no-untyped-def]
    PersonProfile = apps.get_model("identity", "PersonProfile")
    for profile in PersonProfile.objects.order_by("id").iterator():
        if (
            profile.metadata.get("backfilled_from_student_profile")
            and profile.data_status == "LEGACY_UNSTRUCTURED"
            and not profile.first_name
            and not profile.middle_names
            and not profile.first_surname
            and not profile.second_surname
            and not profile.preferred_name
            and profile.birth_date is None
            and not profile.birth_date_purpose
            and profile.confirmed_at is None
        ):
            profile.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0009_personprofile"),
        ("student_records", "0006_rename_display_name_studentprofile_legacy_display_name"),
    ]

    operations = [migrations.RunPython(backfill_person_profiles, reverse_backfill)]
