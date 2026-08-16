# P01 — Dominio y foundation backend

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/04_DOMAIN_MODEL.md`.
4. Lee `docs/05_RULE_ENGINE_SPEC.md`.
4. Lee `docs/07_CURRICULUM_VERSIONING.md`.
4. Lee `docs/14_BACKEND_ARCHITECTURE.md`.

## Skills obligatorias
- carga `feature-delivery`
- carga `db-migration`

## Objetivo

Implementar el modelo de dominio y persistencia base que soporte multiinstitución, temporalidad, currículo, procedencia, estudiante y planificación sin acoplar el motor puro al ORM.

## Entregables obligatorios

1. Crear módulos Django por bounded context definidos en AGENTS.
2. Implementar Institution, Campus, Faculty, Program, CurriculumPlan, CurriculumRevision con constraints e índices.
3. Implementar Course y CourseVersion temporal.
4. Implementar RequirementGroup y PlanMembership.
5. Implementar NormativeDocument, SourceSnapshot, Evidence, NormRelation.
6. Implementar AcademicTerm, CourseOffering, Section, Meeting como modelos separados aunque la UI llegue después.
7. Implementar ProgramEnrollment, CourseAttempt, AcademicRecognition y AcademicException base.
8. Implementar PlanScenario/PlannedCourse base.
9. Definir enums de estado centralizados.
10. Definir inmutabilidad de revisiones publicadas con service/DB protections razonables.
11. Crear admin mínimo sólo para inspección, no como backoffice final.
12. Añadir factories/fixtures y pruebas de constraints.
13. Documentar ERD real.

## Gates de aceptación

- [ ] migraciones limpias desde cero
- [ ] no `prerequisite_id` en Course
- [ ] published revision no se edita por servicio normal
- [ ] course identity separada de membership/offering
- [ ] constraints e índices testeados
- [ ] domain package central no importa Django donde debe ser puro
- [ ] verify pasa

## Revisión

- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
