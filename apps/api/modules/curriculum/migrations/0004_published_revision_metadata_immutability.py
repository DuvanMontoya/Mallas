from __future__ import annotations

from django.db import migrations

TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION protect_published_curriculum_revision()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.status = 'PUBLISHED' THEN
            RAISE EXCEPTION 'Published curriculum revisions cannot be deleted';
        END IF;
        RETURN OLD;
    END IF;

    IF OLD.status = 'PUBLISHED' THEN
        IF NEW.plan_id IS DISTINCT FROM OLD.plan_id
           OR NEW.revision_code IS DISTINCT FROM OLD.revision_code
           OR NEW.effective_from IS DISTINCT FROM OLD.effective_from
           OR NEW.effective_to IS DISTINCT FROM OLD.effective_to
           OR NEW.total_required_credits IS DISTINCT FROM OLD.total_required_credits
           OR NEW.source_set_hash IS DISTINCT FROM OLD.source_set_hash
           OR NEW.content_hash IS DISTINCT FROM OLD.content_hash
           OR NEW.supersedes_id IS DISTINCT FROM OLD.supersedes_id
           OR NEW.metadata IS DISTINCT FROM OLD.metadata THEN
            RAISE EXCEPTION 'Published curriculum revision content cannot be edited';
        END IF;
        IF NEW.status NOT IN ('PUBLISHED', 'SUPERSEDED', 'RETIRED') THEN
            RAISE EXCEPTION 'Published curriculum revision has an invalid transition';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
"""


def update_trigger(apps: object, schema_editor: object) -> None:
    del apps
    connection = schema_editor.connection  # type: ignore[attr-defined]
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(TRIGGER_SQL)


class Migration(migrations.Migration):
    dependencies = [("curriculum", "0003_curriculumrevision_metadata")]
    operations = [migrations.RunPython(update_trigger, migrations.RunPython.noop)]
