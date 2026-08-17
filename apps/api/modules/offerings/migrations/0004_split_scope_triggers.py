from __future__ import annotations

from django.db import migrations

FORWARD_SQL = """
DROP TRIGGER IF EXISTS validate_academic_term_scope_trigger
    ON offerings_academicterm;
DROP TRIGGER IF EXISTS validate_course_offering_scope_trigger
    ON offerings_courseoffering;
DROP FUNCTION IF EXISTS validate_offering_scope();

CREATE OR REPLACE FUNCTION validate_academic_term_scope()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    campus_institution_id uuid;
BEGIN
    IF NEW.campus_id IS NOT NULL THEN
        SELECT institution_id INTO campus_institution_id
        FROM institutions_campus
        WHERE id = NEW.campus_id;
        IF campus_institution_id IS DISTINCT FROM NEW.institution_id THEN
            RAISE EXCEPTION 'Academic term campus must belong to the term institution';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION validate_course_offering_scope()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    term_institution_id uuid;
    course_institution_id uuid;
BEGIN
    SELECT course.institution_id, term.institution_id
    INTO course_institution_id, term_institution_id
    FROM curriculum_courseversion AS version
    JOIN curriculum_course AS course ON course.id = version.course_id
    JOIN offerings_academicterm AS term ON term.id = NEW.term_id
    WHERE version.id = NEW.course_version_id;
    IF course_institution_id IS DISTINCT FROM term_institution_id THEN
        RAISE EXCEPTION 'Course offering course and term must belong to the same institution';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER validate_academic_term_scope_trigger
    BEFORE INSERT OR UPDATE ON offerings_academicterm
    FOR EACH ROW EXECUTE FUNCTION validate_academic_term_scope();
CREATE TRIGGER validate_course_offering_scope_trigger
    BEFORE INSERT OR UPDATE ON offerings_courseoffering
    FOR EACH ROW EXECUTE FUNCTION validate_course_offering_scope();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS validate_academic_term_scope_trigger
    ON offerings_academicterm;
DROP TRIGGER IF EXISTS validate_course_offering_scope_trigger
    ON offerings_courseoffering;
DROP FUNCTION IF EXISTS validate_academic_term_scope();
DROP FUNCTION IF EXISTS validate_course_offering_scope();
"""


def install_split_triggers(apps: object, schema_editor: object) -> None:
    del apps
    connection = schema_editor.connection  # type: ignore[attr-defined]
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(FORWARD_SQL)


def remove_split_triggers(apps: object, schema_editor: object) -> None:
    del apps
    connection = schema_editor.connection  # type: ignore[attr-defined]
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(REVERSE_SQL)


class Migration(migrations.Migration):
    dependencies = [("offerings", "0003_cross_scope_invariants")]
    operations = [migrations.RunPython(install_split_triggers, remove_split_triggers)]
