from django.db import migrations


def remove_sqlite_audit_event_triggers(apps: object, schema_editor: object) -> None:
    del apps
    connection = schema_editor.connection  # type: ignore[attr-defined]
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("DROP TRIGGER IF EXISTS protect_identity_audit_event_sqlite_update;")
            cursor.execute("DROP TRIGGER IF EXISTS protect_identity_audit_event_sqlite_delete;")


class Migration(migrations.Migration):
    dependencies = [("identity", "0005_audit_event_sqlite_trigger")]

    operations = [
        migrations.RunPython(remove_sqlite_audit_event_triggers, migrations.RunPython.noop)
    ]
