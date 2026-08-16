from django.db import migrations

SQLITE_TRIGGER_STATEMENTS = (
    """
CREATE TRIGGER IF NOT EXISTS protect_identity_audit_event_sqlite_update
    BEFORE UPDATE ON identity_auditevent
    BEGIN
        SELECT RAISE(ABORT, 'Audit events are append-only');
    END;
""",
    """
CREATE TRIGGER IF NOT EXISTS protect_identity_audit_event_sqlite_delete
    BEFORE DELETE ON identity_auditevent
    BEGIN
        SELECT RAISE(ABORT, 'Audit events are append-only');
    END;
""",
)

SQLITE_REVERSE_STATEMENTS = (
    "DROP TRIGGER IF EXISTS protect_identity_audit_event_sqlite_update;",
    "DROP TRIGGER IF EXISTS protect_identity_audit_event_sqlite_delete;",
)


def install_sqlite_audit_event_triggers(apps: object, schema_editor: object) -> None:
    del apps
    connection = schema_editor.connection  # type: ignore[attr-defined]
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            for statement in SQLITE_TRIGGER_STATEMENTS:
                cursor.execute(statement)


def remove_sqlite_audit_event_triggers(apps: object, schema_editor: object) -> None:
    del apps
    connection = schema_editor.connection  # type: ignore[attr-defined]
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            for statement in SQLITE_REVERSE_STATEMENTS:
                cursor.execute(statement)


class Migration(migrations.Migration):
    dependencies = [("identity", "0004_alter_auditevent_actor")]

    operations = [
        migrations.RunPython(
            install_sqlite_audit_event_triggers,
            remove_sqlite_audit_event_triggers,
        )
    ]
