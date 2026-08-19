from __future__ import annotations

from django.db import migrations

TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION protect_curriculum_assignment_policy()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.status IN ('PUBLISHED', 'SUPERSEDED', 'RETIRED') THEN
            RAISE EXCEPTION 'Published curriculum assignment policies cannot be deleted';
        END IF;
        RETURN OLD;
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

DROP TRIGGER IF EXISTS protect_curriculum_assignment_policy_trigger
    ON curriculum_curriculumassignmentpolicy;
CREATE TRIGGER protect_curriculum_assignment_policy_trigger
    BEFORE UPDATE OR DELETE ON curriculum_curriculumassignmentpolicy
    FOR EACH ROW EXECUTE FUNCTION protect_curriculum_assignment_policy();

CREATE OR REPLACE FUNCTION protect_curriculum_assignment_policy_evidence()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    policy_status varchar(24);
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        SELECT status INTO policy_status
          FROM curriculum_curriculumassignmentpolicy
         WHERE id = OLD.policy_id;
        IF policy_status IN ('PUBLISHED', 'SUPERSEDED', 'RETIRED') THEN
            RAISE EXCEPTION 'Evidence cannot be removed from a published curriculum assignment policy';
        END IF;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        SELECT status INTO policy_status
          FROM curriculum_curriculumassignmentpolicy
         WHERE id = NEW.policy_id;
        IF policy_status IN ('PUBLISHED', 'SUPERSEDED', 'RETIRED') THEN
            RAISE EXCEPTION 'Evidence cannot be added to a published curriculum assignment policy';
        END IF;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS protect_curriculum_assignment_policy_evidence_trigger
    ON curriculum_curriculumassignmentpolicyevidence;
CREATE TRIGGER protect_curriculum_assignment_policy_evidence_trigger
    BEFORE INSERT OR UPDATE OR DELETE ON curriculum_curriculumassignmentpolicyevidence
    FOR EACH ROW EXECUTE FUNCTION protect_curriculum_assignment_policy_evidence();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS protect_curriculum_assignment_policy_evidence_trigger
    ON curriculum_curriculumassignmentpolicyevidence;
DROP FUNCTION IF EXISTS protect_curriculum_assignment_policy_evidence();
DROP TRIGGER IF EXISTS protect_curriculum_assignment_policy_trigger
    ON curriculum_curriculumassignmentpolicy;
DROP FUNCTION IF EXISTS protect_curriculum_assignment_policy();
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
    dependencies = [("curriculum", "0007_curriculumassignmentpolicy_and_more")]
    operations = [migrations.RunPython(install_triggers, remove_triggers)]
