from __future__ import annotations

from django.db import migrations

TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION validate_curriculum_scope()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    parent_revision_id uuid;
    group_revision_id uuid;
    course_institution_id uuid;
    program_institution_id uuid;
BEGIN
    IF TG_TABLE_NAME = 'curriculum_requirementgroup' THEN
        IF TG_OP IN ('INSERT', 'UPDATE') AND NEW.parent_id IS NOT NULL THEN
            SELECT revision_id INTO parent_revision_id
            FROM curriculum_requirementgroup
            WHERE id = NEW.parent_id;
            IF parent_revision_id IS DISTINCT FROM NEW.revision_id THEN
                RAISE EXCEPTION 'Requirement group parent must belong to the same revision';
            END IF;
        END IF;
        RETURN NEW;
    END IF;

    IF TG_TABLE_NAME = 'curriculum_planmembership'
       AND TG_OP IN ('INSERT', 'UPDATE') THEN
        SELECT revision_id INTO group_revision_id
        FROM curriculum_requirementgroup
        WHERE id = NEW.group_id;
        IF group_revision_id IS DISTINCT FROM NEW.revision_id THEN
            RAISE EXCEPTION 'Plan membership group must belong to the membership revision';
        END IF;

        SELECT course.institution_id, campus.institution_id
        INTO course_institution_id, program_institution_id
        FROM curriculum_courseversion AS version
        JOIN curriculum_course AS course ON course.id = version.course_id
        JOIN curriculum_curriculumrevision AS revision
            ON revision.id = NEW.revision_id
        JOIN curriculum_curriculumplan AS plan ON plan.id = revision.plan_id
        JOIN institutions_program AS program ON program.id = plan.program_id
        JOIN institutions_faculty AS faculty ON faculty.id = program.faculty_id
        JOIN institutions_campus AS campus ON campus.id = faculty.campus_id
        WHERE version.id = NEW.course_version_id;
        IF course_institution_id IS DISTINCT FROM program_institution_id THEN
            RAISE EXCEPTION 'Plan membership course and program must belong to the same institution';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS validate_requirement_group_scope_trigger
    ON curriculum_requirementgroup;
CREATE TRIGGER validate_requirement_group_scope_trigger
    BEFORE INSERT OR UPDATE ON curriculum_requirementgroup
    FOR EACH ROW EXECUTE FUNCTION validate_curriculum_scope();

DROP TRIGGER IF EXISTS validate_plan_membership_scope_trigger
    ON curriculum_planmembership;
CREATE TRIGGER validate_plan_membership_scope_trigger
    BEFORE INSERT OR UPDATE ON curriculum_planmembership
    FOR EACH ROW EXECUTE FUNCTION validate_curriculum_scope();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS validate_requirement_group_scope_trigger
    ON curriculum_requirementgroup;
DROP TRIGGER IF EXISTS validate_plan_membership_scope_trigger
    ON curriculum_planmembership;
DROP FUNCTION IF EXISTS validate_curriculum_scope();
"""


def install_triggers(apps: object, schema_editor: object) -> None:
    del apps
    connection = schema_editor.connection  # type: ignore[attr-defined]
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(TRIGGER_SQL)


def remove_triggers(apps: object, schema_editor: object) -> None:
    del apps
    connection = schema_editor.connection  # type: ignore[attr-defined]
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(REVERSE_SQL)


class Migration(migrations.Migration):
    dependencies = [("curriculum", "0005_published_revision_children_immutable")]
    operations = [migrations.RunPython(install_triggers, remove_triggers)]
