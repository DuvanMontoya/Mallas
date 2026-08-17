from __future__ import annotations

from django.db import migrations

TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION validate_role_assignment_scope()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    program_institution_id uuid;
BEGIN
    IF TG_OP IN ('INSERT', 'UPDATE') AND NEW.program_id IS NOT NULL THEN
        IF NEW.institution_id IS NULL THEN
            RAISE EXCEPTION 'A program-scoped role requires an institution';
        END IF;
        SELECT campus.institution_id INTO program_institution_id
        FROM institutions_program AS program
        JOIN institutions_faculty AS faculty ON faculty.id = program.faculty_id
        JOIN institutions_campus AS campus ON campus.id = faculty.campus_id
        WHERE program.id = NEW.program_id;
        IF program_institution_id IS DISTINCT FROM NEW.institution_id THEN
            RAISE EXCEPTION 'Role assignment program must belong to its institution';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS validate_role_assignment_scope_trigger
    ON identity_roleassignment;
CREATE TRIGGER validate_role_assignment_scope_trigger
    BEFORE INSERT OR UPDATE ON identity_roleassignment
    FOR EACH ROW EXECUTE FUNCTION validate_role_assignment_scope();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS validate_role_assignment_scope_trigger
    ON identity_roleassignment;
DROP FUNCTION IF EXISTS validate_role_assignment_scope();
"""


def install_trigger(apps: object, schema_editor: object) -> None:
    del apps
    connection = schema_editor.connection  # type: ignore[attr-defined]
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(TRIGGER_SQL)


def remove_trigger(apps: object, schema_editor: object) -> None:
    del apps
    connection = schema_editor.connection  # type: ignore[attr-defined]
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(REVERSE_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0006_remove_sqlite_audit_event_trigger"),
        ("institutions", "0001_initial"),
    ]
    operations = [migrations.RunPython(install_trigger, remove_trigger)]
