from __future__ import annotations

from django.db import migrations

FORWARD_SQL = """
CREATE OR REPLACE FUNCTION protect_assignment_override_authorization()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    approval_capability text;
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.status = 'APPROVED' THEN
            RAISE EXCEPTION 'Approved assignment override authorizations cannot be deleted';
        END IF;
        RETURN OLD;
    END IF;

    IF NEW.status = 'APPROVED'
       AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM 'APPROVED') THEN
        approval_capability := current_setting('app.assignment_override_approval', true);
        IF approval_capability IS DISTINCT FROM 'allowed'
           OR NEW.approved_by_id IS NULL
           OR NEW.approved_by_id = NEW.prepared_by_id
           OR NEW.approved_at IS NULL
           OR NEW.content_hash = ''
           OR NEW.revision_content_hash = ''
           OR NEW.revision_source_set_hash = ''
           OR NEW.sealed_snapshot_id IS NULL
           OR NEW.sealed_snapshot_sha256 = ''
           OR NEW.sealed_storage_key_hash = ''
           OR NEW.sealed_excerpt_hash = '' THEN
            RAISE EXCEPTION 'Override authorization approval requires the governed service';
        END IF;
    END IF;

    IF TG_OP = 'UPDATE' AND OLD.status = 'APPROVED' AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'Approved assignment override authorizations are immutable';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS assignment_override_authorization_guard
ON student_records_curriculumassignmentoverrideauthorization;
CREATE TRIGGER assignment_override_authorization_guard
BEFORE INSERT OR UPDATE OR DELETE
ON student_records_curriculumassignmentoverrideauthorization
FOR EACH ROW EXECUTE FUNCTION protect_assignment_override_authorization();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS assignment_override_authorization_guard
ON student_records_curriculumassignmentoverrideauthorization;
DROP FUNCTION IF EXISTS protect_assignment_override_authorization();
"""


def install_guard(apps: object, schema_editor: object) -> None:
    del apps
    if schema_editor.connection.vendor == "postgresql":  # type: ignore[attr-defined]
        with schema_editor.connection.cursor() as cursor:  # type: ignore[attr-defined]
            cursor.execute(FORWARD_SQL)


def remove_guard(apps: object, schema_editor: object) -> None:
    del apps
    if schema_editor.connection.vendor == "postgresql":  # type: ignore[attr-defined]
        with schema_editor.connection.cursor() as cursor:  # type: ignore[attr-defined]
            cursor.execute(REVERSE_SQL)


class Migration(migrations.Migration):
    dependencies = [("student_records", "0016_assignment_override_authorization")]
    operations = [migrations.RunPython(install_guard, remove_guard)]
