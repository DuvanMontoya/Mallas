# 04 — Modelo de dominio completo

## Identidad académica

### User y PersonProfile

`User` posee autenticación y autorización. `PersonProfile` es la identidad
personal privada 1:1: nombres y apellidos estructurados, nombre preferido,
fecha de nacimiento con propósito/retención y estado de calidad. La edad es
derivada, nunca persistida. Los nombres legacy no se dividen por heurística.
`verification_method` distingue `SELF_DECLARED`, `INSTITUTION_VERIFIED`,
`PREEXISTING_UNCLASSIFIED` y `LEGACY_UNKNOWN`. Una migración sólo clasifica
procedencia histórica cuando existe un evento auditable; no inventa
verificación institucional. Constraints de base exigen una identidad
confirmada completa y coherencia entre fecha de nacimiento y propósito incluso
ante escrituras bulk/raw.

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

### CurriculumAssignmentPolicy y CurriculumAssignmentDecision

`CurriculumAssignmentPolicy` representa la norma evidenciada que vincula un
contexto de admisión, reingreso, traslado, doble titulación o transición con un
plan y una revisión. Separa fecha de publicación normativa, entrada en vigor y
rango/cohorte de admisión; `CurriculumRevision.effective_from` no sustituye esa
política.

El resolver puro produce `RESOLVED`, `NEEDS_REVIEW` o `UNKNOWN`. Sólo una
política publicada o histórica, `VERIFIED`, evidenciada, con hashes completos y
coincidencia única produce `RESOLVED`. `CurriculumAssignmentDecision` conserva
append-only inputs y su procedencia, candidatos, razones, política, objetivo,
método, versión del resolver y hash reproducible por matrícula.

`AdmissionFact` demuestra el hecho individual de que una persona fue admitida
en un programa y período determinados. Una fuente del catálogo de períodos no
demuestra por sí sola la admisión de esa persona. El hecho verificado conserva
referencia protegida, evidencia archivada, actor, fecha, huella HMAC del número
estudiantil y hash, y es inmutable. La decisión lo consume una sola vez y el
backend compara el sujeto contra el sello, no contra metadata mutable.

El paso `DRAFT → IN_REVIEW` sella campos, revisión objetivo y evidencia tipada;
el material en revisión no puede mutar. Una persona distinta, con rol de
revisión y MFA privilegiado, puede publicar exactamente ese paquete. Una
política sin evidencia suficiente permanece no resoluble.

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
`user_id, institution_id, student_number, legacy_display_name, metadata`.
No asumir que el usuario autenticado siempre es un estudiante. El nombre
vigente se obtiene de `PersonProfile`; `legacy_display_name` es sólo fallback
para migraciones aún no confirmadas.

### ProgramEnrollment
`student_id, program_id, plan_id?, revision_basis?, admission_term, status,
review_reasons`. Plan y revisión son nulos mientras la asignación permanezca
`NEEDS_REVIEW`; no se usan identificadores ficticios.

`EnrollmentTransition` enlaza de forma append-only matrícula fuente y destino
para `REENTRY` o `PLAN_TRANSITION`, sella términos, fechas, plan/revisión
anteriores, estados y hash de decisión. Una transición de plan cierra la fuente
como `TRANSITIONED`; un reingreso parte de una vinculación histórica. El
onboarding pertenece a una matrícula concreta, no a la persona global.

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
