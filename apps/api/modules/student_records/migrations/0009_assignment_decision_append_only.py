from __future__ import annotations

from django.db import migrations

TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION protect_curriculum_assignment_decision()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Curriculum assignment decisions are append-only';
END;
$$;

DROP TRIGGER IF EXISTS protect_curriculum_assignment_decision_trigger
    ON student_records_curriculumassignmentdecision;
CREATE TRIGGER protect_curriculum_assignment_decision_trigger
    BEFORE UPDATE OR DELETE ON student_records_curriculumassignmentdecision
    FOR EACH ROW EXECUTE FUNCTION protect_curriculum_assignment_decision();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS protect_curriculum_assignment_decision_trigger
    ON student_records_curriculumassignmentdecision;
DROP FUNCTION IF EXISTS protect_curriculum_assignment_decision();
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
    dependencies = [("student_records", "0008_curriculumassignmentdecision")]
    operations = [migrations.RunPython(install_trigger, remove_trigger)]
