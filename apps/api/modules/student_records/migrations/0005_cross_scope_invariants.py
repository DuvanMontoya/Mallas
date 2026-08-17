from __future__ import annotations

from django.db import migrations

TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION validate_student_record_scope()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    student_institution_id uuid;
    program_institution_id uuid;
    plan_program_id uuid;
    revision_plan_id uuid;
    term_institution_id uuid;
    course_institution_id uuid;
BEGIN
    IF TG_TABLE_NAME = 'student_records_programenrollment'
       AND TG_OP IN ('INSERT', 'UPDATE') THEN
        SELECT student.institution_id,
               campus.institution_id,
               plan.program_id,
               revision.plan_id,
               term.institution_id
        INTO student_institution_id,
             program_institution_id,
             plan_program_id,
             revision_plan_id,
             term_institution_id
        FROM student_records_studentprofile AS student
        JOIN institutions_program AS program ON program.id = NEW.program_id
        JOIN institutions_faculty AS faculty ON faculty.id = program.faculty_id
        JOIN institutions_campus AS campus ON campus.id = faculty.campus_id
        JOIN curriculum_curriculumplan AS plan ON plan.id = NEW.plan_id
        JOIN curriculum_curriculumrevision AS revision ON revision.id = NEW.revision_basis_id
        JOIN offerings_academicterm AS term ON term.id = NEW.admission_term_id
        WHERE student.id = NEW.student_id;
        IF student_institution_id IS DISTINCT FROM program_institution_id
           OR plan_program_id IS DISTINCT FROM NEW.program_id
           OR revision_plan_id IS DISTINCT FROM NEW.plan_id
           OR student_institution_id IS DISTINCT FROM term_institution_id THEN
            RAISE EXCEPTION 'Program enrollment crosses institution, program, plan or revision scope';
        END IF;
        RETURN NEW;
    END IF;

    IF TG_TABLE_NAME = 'student_records_courseattempt'
       AND TG_OP IN ('INSERT', 'UPDATE') THEN
        SELECT student.institution_id, term.institution_id, course.institution_id
        INTO student_institution_id, term_institution_id, course_institution_id
        FROM student_records_programenrollment AS enrollment
        JOIN student_records_studentprofile AS student ON student.id = enrollment.student_id
        JOIN offerings_academicterm AS term ON term.id = NEW.term_id
        JOIN curriculum_courseversion AS version ON version.id = NEW.course_version_id
        JOIN curriculum_course AS course ON course.id = version.course_id
        WHERE enrollment.id = NEW.enrollment_id;
        IF student_institution_id IS DISTINCT FROM term_institution_id
           OR student_institution_id IS DISTINCT FROM course_institution_id THEN
            RAISE EXCEPTION 'Course attempt crosses student, term or course institution scope';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS validate_program_enrollment_scope_trigger
    ON student_records_programenrollment;
CREATE TRIGGER validate_program_enrollment_scope_trigger
    BEFORE INSERT OR UPDATE ON student_records_programenrollment
    FOR EACH ROW EXECUTE FUNCTION validate_student_record_scope();

DROP TRIGGER IF EXISTS validate_course_attempt_scope_trigger
    ON student_records_courseattempt;
CREATE TRIGGER validate_course_attempt_scope_trigger
    BEFORE INSERT OR UPDATE ON student_records_courseattempt
    FOR EACH ROW EXECUTE FUNCTION validate_student_record_scope();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS validate_program_enrollment_scope_trigger
    ON student_records_programenrollment;
DROP TRIGGER IF EXISTS validate_course_attempt_scope_trigger
    ON student_records_courseattempt;
DROP FUNCTION IF EXISTS validate_student_record_scope();
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
        ("student_records", "0004_courseattempt_entered_by"),
        ("curriculum", "0006_cross_scope_invariants"),
        ("offerings", "0003_cross_scope_invariants"),
    ]
    operations = [migrations.RunPython(install_triggers, remove_triggers)]
