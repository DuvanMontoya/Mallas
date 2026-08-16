# 04 — Modelo de dominio completo

## Identidad académica

### Institution
`id, slug, legal_name, display_name, country_code, status`

### Campus
`id, institution_id, code, name, timezone`

### Faculty
`id, campus_id, code, name`

### Program
`id, faculty_id, code, snies, name, degree_name, estimated_terms`

### CurriculumPlan
Identidad del plan: `program_id, code, title`.

### CurriculumRevision
Versión temporal:
- `plan_id`
- `revision_code`
- `effective_from`
- `effective_to`
- `status`
- `total_required_credits`
- `source_set_hash`
- `published_at`
- `supersedes_revision_id`

Una revisión publicada nunca se actualiza in-place.

## Catálogo

### Course
Identidad durable: `institution_id, code`.

### CourseVersion
`course_id, name, credits, valid_from, valid_to, metadata`.

Una asignatura puede cambiar créditos/nombre sin perder identidad.

### RequirementGroup
Árbol o jerarquía de componente/agrupación:
- `kind = COMPONENT | GROUP | GRADUATION`
- `required_credits`
- `parent_id`

### PlanMembership
`revision_id, course_version_id, group_id, role, count_policy`.

`role`: `MANDATORY | ELECTIVE_OPTION | FREE_ELECTIVE_OPTION | EXTERNAL_REFERENCE`.

## Reglas

### Requirement
- `owner_type`
- `owner_id`
- `purpose`
- `ast`
- `epistemic_status`
- `evidence_set_id`

Propósitos:
- enrollment prerequisite;
- corequisite;
- group completion;
- graduation;
- practice eligibility;
- substitution.

## Fuentes

### NormativeDocument
`issuer, document_type, number, year, title, publication_date, canonical_url, status`.

### SourceSnapshot
`document_id, captured_at, sha256, mime_type, storage_key`.

### Evidence
`snapshot_id, page, section, line/locator, excerpt_hash, annotation`.

### NormRelation
`source_document_id, relation, target_document_id, effective_date`.
Relaciones: `AMENDS`, `REPEALS`, `ADDS`, `CLARIFIES`, `SUPERSEDES`.

## Estudiante

### StudentProfile
No asumir que el usuario autenticado siempre es un estudiante.

### ProgramEnrollment
`student_id, program_id, plan_id, revision_basis, admission_term, status`.

### CourseAttempt
- course/version;
- term;
- status;
- grade;
- credits_earned;
- origin;
- evidence/import batch.

Estados mínimos:
`PLANNED, ENROLLED, PASSED, FAILED, CANCELLED, WITHDRAWN, VALIDATED, HOMOLOGATED, TRANSFERRED, ANNULLED`.

Sólo estados definidos aportan créditos.

### AcademicRecognition
Homologación/equivalencia/reconocimiento individual con resolución/evidencia.

### AcademicException
Waiver o autorización individual; auditable y temporal.

## Oferta

### AcademicTerm
`institution/campus, code, starts_at, ends_at, status`.

### CourseOffering
`course_version, term, status, source`.

### Section
`offering, group_code, modality, capacity metadata`.

### Meeting
día/fecha, hora inicial/final, location.

La elegibilidad no depende de que exista una sección.

## Auditoría

### DegreeAuditRun
Snapshot reproducible:
- revision id/hash;
- history fingerprint;
- exception fingerprint;
- engine version;
- result hash;
- generated_at.

### DegreeAuditResult
Estructura explicable; puede persistirse para caché/auditoría.

### CreditAllocation
Registra exactamente qué créditos/intentos satisfacen qué requirement/group.

## Planificación

### PlanScenario
Escenario versionado del estudiante.

### PlannedCourse
Curso + término + prioridad + source (`USER | OPTIMIZER`).

### PlanningPreference
Límite créditos, disponibilidad, carga, intereses.

### OptimizationRun
Input hash, solver version, status, objective values, solution.

## Gobernanza

### ChangeProposal
Diff semántico entre fuente/revisiones.

### Review
Autor, decisión, observaciones.

### Publication
Evento auditable.

## Restricción fundamental

No hay FK `Course.prerequisite_id`.

Los requisitos son ASTs versionados.
