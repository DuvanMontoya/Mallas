from __future__ import annotations

from django.db import migrations

TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION protect_published_requirement()
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
            RAISE EXCEPTION 'Requirements belonging to immutable revisions cannot be changed';
        END IF;
    END IF;

    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        SELECT status INTO new_status
        FROM curriculum_curriculumrevision
        WHERE id = NEW.revision_id;
        IF new_status IN ('PUBLISHED', 'SUPERSEDED', 'RETIRED') THEN
            RAISE EXCEPTION 'Requirements belonging to immutable revisions cannot be changed';
        END IF;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS protect_published_requirement_trigger
    ON rules_requirement;
CREATE TRIGGER protect_published_requirement_trigger
    BEFORE INSERT OR UPDATE OR DELETE ON rules_requirement
    FOR EACH ROW EXECUTE FUNCTION protect_published_requirement();

CREATE OR REPLACE FUNCTION protect_published_requirement_evidence()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    revision_status text;
    requirement_id uuid;
BEGIN
    requirement_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.requirement_id ELSE NEW.requirement_id END;
    SELECT revision.status INTO revision_status
    FROM rules_requirement AS requirement
    JOIN curriculum_curriculumrevision AS revision ON revision.id = requirement.revision_id
    WHERE requirement.id = requirement_id;
    IF revision_status IN ('PUBLISHED', 'SUPERSEDED', 'RETIRED') THEN
        RAISE EXCEPTION 'Evidence links for immutable requirements cannot be changed';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS protect_published_requirement_evidence_trigger
    ON rules_requirement_evidence;
CREATE TRIGGER protect_published_requirement_evidence_trigger
    BEFORE INSERT OR UPDATE OR DELETE ON rules_requirement_evidence
    FOR EACH ROW EXECUTE FUNCTION protect_published_requirement_evidence();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS protect_published_requirement_evidence_trigger
    ON rules_requirement_evidence;
DROP FUNCTION IF EXISTS protect_published_requirement_evidence();
DROP TRIGGER IF EXISTS protect_published_requirement_trigger
    ON rules_requirement;
DROP FUNCTION IF EXISTS protect_published_requirement();
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
    dependencies = [
        ("rules", "0003_requirement_ast_schema_version"),
        ("curriculum", "0005_published_revision_children_immutable"),
    ]
    operations = [migrations.RunPython(install_triggers, remove_triggers)]
