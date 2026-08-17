from __future__ import annotations

from django.db import migrations


TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION protect_published_curriculum_child()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    old_status text;
    new_status text;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        SELECT status INTO old_status
        FROM curriculum_curriculumrevision
        WHERE id = OLD.revision_id;
        IF old_status IN ('PUBLISHED', 'SUPERSEDED', 'RETIRED') THEN
            RAISE EXCEPTION 'Curriculum revision child rows are immutable after publication';
        END IF;
    END IF;

    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        SELECT status INTO new_status
        FROM curriculum_curriculumrevision
        WHERE id = NEW.revision_id;
        IF new_status IN ('PUBLISHED', 'SUPERSEDED', 'RETIRED') THEN
            RAISE EXCEPTION 'Curriculum revision child rows are immutable after publication';
        END IF;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS protect_published_requirement_group_trigger
    ON curriculum_requirementgroup;
CREATE TRIGGER protect_published_requirement_group_trigger
    BEFORE INSERT OR UPDATE OR DELETE ON curriculum_requirementgroup
    FOR EACH ROW EXECUTE FUNCTION protect_published_curriculum_child();

DROP TRIGGER IF EXISTS protect_published_plan_membership_trigger
    ON curriculum_planmembership;
CREATE TRIGGER protect_published_plan_membership_trigger
    BEFORE INSERT OR UPDATE OR DELETE ON curriculum_planmembership
    FOR EACH ROW EXECUTE FUNCTION protect_published_curriculum_child();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS protect_published_requirement_group_trigger
    ON curriculum_requirementgroup;
DROP TRIGGER IF EXISTS protect_published_plan_membership_trigger
    ON curriculum_planmembership;
DROP FUNCTION IF EXISTS protect_published_curriculum_child();
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
    dependencies = [("curriculum", "0004_published_revision_metadata_immutability")]
    operations = [migrations.RunPython(install_triggers, remove_triggers)]
