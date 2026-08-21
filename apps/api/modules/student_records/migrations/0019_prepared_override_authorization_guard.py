from __future__ import annotations

from django.db import migrations

FORWARD_SQL = """
CREATE OR REPLACE FUNCTION protect_prepared_override_authorization_content()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.enrollment_id IS DISTINCT FROM OLD.enrollment_id
       OR NEW.plan_id IS DISTINCT FROM OLD.plan_id
       OR NEW.revision_basis_id IS DISTINCT FROM OLD.revision_basis_id
       OR NEW.reason_code IS DISTINCT FROM OLD.reason_code
       OR NEW.evidence_id IS DISTINCT FROM OLD.evidence_id
       OR NEW.prepared_by_id IS DISTINCT FROM OLD.prepared_by_id
       OR NEW.revision_content_hash IS DISTINCT FROM OLD.revision_content_hash
       OR NEW.revision_source_set_hash IS DISTINCT FROM OLD.revision_source_set_hash
       OR NEW.revision_status IS DISTINCT FROM OLD.revision_status
       OR NEW.sealed_snapshot_id IS DISTINCT FROM OLD.sealed_snapshot_id
       OR NEW.sealed_snapshot_sha256 IS DISTINCT FROM OLD.sealed_snapshot_sha256
       OR NEW.sealed_storage_key_hash IS DISTINCT FROM OLD.sealed_storage_key_hash
       OR NEW.sealed_excerpt_hash IS DISTINCT FROM OLD.sealed_excerpt_hash
       OR NEW.sealed_excerpt IS DISTINCT FROM OLD.sealed_excerpt
       OR NEW.sealed_locator_hash IS DISTINCT FROM OLD.sealed_locator_hash
       OR NEW.sealed_locator IS DISTINCT FROM OLD.sealed_locator
       OR NEW.sealed_source_title IS DISTINCT FROM OLD.sealed_source_title
       OR NEW.content_hash IS DISTINCT FROM OLD.content_hash
       OR NEW.seal_version IS DISTINCT FROM OLD.seal_version THEN
        RAISE EXCEPTION 'Prepared assignment override authorization content is immutable';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS prepared_override_authorization_guard
ON student_records_curriculumassignmentoverrideauthorization;
CREATE TRIGGER prepared_override_authorization_guard
BEFORE UPDATE ON student_records_curriculumassignmentoverrideauthorization
FOR EACH ROW EXECUTE FUNCTION protect_prepared_override_authorization_content();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS prepared_override_authorization_guard
ON student_records_curriculumassignmentoverrideauthorization;
DROP FUNCTION IF EXISTS protect_prepared_override_authorization_content();
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
    dependencies = [("student_records", "0018_enrollment_transition_and_prepared_override_seal")]
    operations = [migrations.RunPython(install_guard, remove_guard)]
