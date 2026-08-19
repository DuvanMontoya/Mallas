from __future__ import annotations

from django.db import migrations

FORWARD_SQL = """
CREATE OR REPLACE FUNCTION protect_curriculum_assignment_policy()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    publication_capability text;
    sealed_evidence_count integer;
    target_status varchar(24);
    target_content_hash varchar(64);
    target_source_set_hash varchar(64);
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.status IN ('PUBLISHED', 'SUPERSEDED', 'RETIRED') THEN
            RAISE EXCEPTION 'Published curriculum assignment policies cannot be deleted';
        END IF;
        RETURN OLD;
    END IF;

    IF OLD.status NOT IN ('PUBLISHED', 'SUPERSEDED', 'RETIRED')
       AND NEW.status = 'PUBLISHED' THEN
        publication_capability := current_setting('app.assignment_policy_publication', true);
        IF publication_capability IS DISTINCT FROM 'allowed' THEN
            RAISE EXCEPTION 'Assignment policies can only be published through the governance service';
        END IF;
        SELECT status, content_hash, source_set_hash
          INTO target_status, target_content_hash, target_source_set_hash
          FROM curriculum_curriculumrevision
         WHERE id = NEW.revision_basis_id;
        SELECT count(*)
          INTO sealed_evidence_count
          FROM curriculum_curriculumassignmentpolicyevidence
         WHERE policy_id = NEW.id
           AND sealed_snapshot_sha256 <> ''
           AND sealed_excerpt_hash <> ''
           AND sealed_locator_hash <> '';
        IF NEW.content_hash = '' OR NEW.source_set_hash = '' OR NEW.published_at IS NULL
           OR target_status NOT IN ('PUBLISHED', 'SUPERSEDED', 'RETIRED')
           OR target_content_hash = '' OR target_source_set_hash = ''
           OR sealed_evidence_count < 1 THEN
            RAISE EXCEPTION 'Published assignment policy is missing sealed governance material';
        END IF;
    END IF;

    IF OLD.status IN ('PUBLISHED', 'SUPERSEDED', 'RETIRED') THEN
        IF NEW.policy_code IS DISTINCT FROM OLD.policy_code
           OR NEW.version IS DISTINCT FROM OLD.version
           OR NEW.program_id IS DISTINCT FROM OLD.program_id
           OR NEW.plan_id IS DISTINCT FROM OLD.plan_id
           OR NEW.revision_basis_id IS DISTINCT FROM OLD.revision_basis_id
           OR NEW.context IS DISTINCT FROM OLD.context
           OR NEW.admission_from IS DISTINCT FROM OLD.admission_from
           OR NEW.admission_to IS DISTINCT FROM OLD.admission_to
           OR NEW.cohort_code IS DISTINCT FROM OLD.cohort_code
           OR NEW.previous_plan_id IS DISTINCT FROM OLD.previous_plan_id
           OR NEW.normative_published_on IS DISTINCT FROM OLD.normative_published_on
           OR NEW.effective_from IS DISTINCT FROM OLD.effective_from
           OR NEW.effective_to IS DISTINCT FROM OLD.effective_to
           OR NEW.epistemic_status IS DISTINCT FROM OLD.epistemic_status
           OR NEW.source_set_hash IS DISTINCT FROM OLD.source_set_hash
           OR NEW.content_hash IS DISTINCT FROM OLD.content_hash
           OR NEW.published_at IS DISTINCT FROM OLD.published_at
           OR NEW.supersedes_id IS DISTINCT FROM OLD.supersedes_id
           OR NEW.metadata IS DISTINCT FROM OLD.metadata THEN
            RAISE EXCEPTION 'Published curriculum assignment policy content cannot be edited';
        END IF;
        IF (OLD.status = 'PUBLISHED' AND NEW.status NOT IN ('PUBLISHED', 'SUPERSEDED', 'RETIRED'))
           OR (OLD.status = 'SUPERSEDED' AND NEW.status <> 'SUPERSEDED')
           OR (OLD.status = 'RETIRED' AND NEW.status <> 'RETIRED') THEN
            RAISE EXCEPTION 'Curriculum assignment policy lifecycle cannot move backwards';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
"""


def install_guard(apps: object, schema_editor: object) -> None:
    del apps
    connection = schema_editor.connection  # type: ignore[attr-defined]
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(FORWARD_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ("curriculum", "0009_curriculumassignmentpolicyevidence_sealed_excerpt_hash_and_more")
    ]
    operations = [migrations.RunPython(install_guard, migrations.RunPython.noop)]
