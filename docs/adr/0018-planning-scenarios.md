# ADR 0018 — Escenarios de planificación como proyecciones privadas

## Estado

Aceptada — 2026-08-16

## Contexto

El planificador debe permitir explorar términos, cursos, grupos y preferencias
sin convertir una intención futura en un hecho académico. La auditoría oficial
usa únicamente `CourseAttempt`, reconocimientos y excepciones autorizadas. Un
escenario debe ser auditable, versionado y compartible sólo con una vista
mínima explícita.

## Decisión

1. `PlanScenario` pertenece a una `ProgramEnrollment`, conserva `created_by`,
   `version`, estado (`ACTIVE`/`ARCHIVED`) y un `share_token` separado. El
   token se genera sólo cuando se activa el compartir y la vista pública nunca
   expone matrícula, estudiante, historial, preferencias ni proyección de
   auditoría.
2. `PlannedCourse` es una entidad separada por escenario y término. Puede
   apuntar a una sección concreta, tiene prioridad, origen, notas y
   `is_locked`. La posición visual no se usa como regla normativa.
3. La validación incremental vive en `domain.planning.validator`, Python puro:
   `CoursePassed` exige un término anterior; `Corequisite` acepta el mismo
   término; límites de créditos, oferta, días no disponibles y conflictos de
   horario producen warnings explícitos. Una regla ausente, ambigua o no
   verificable produce `UNKNOWN`.
4. Cada cambio recalcula `ScenarioAuditProjection`. El motor recibe una copia
   inmutable de la historia más registros sintéticos marcados como proyección;
   nunca se crean ni modifican `CourseAttempt`, `DegreeAuditRun` o
   `DegreeAuditResult`. Si la revisión no satisface el contrato del motor, la
   proyección se persiste como `UNKNOWN` con causa trazable, no como error 500.
5. Todas las mutaciones relevantes requieren `If-Match` con la versión actual
   y generan una nueva versión. Duplicar crea una rama nueva sin locks ni
   compartir heredados; comparar sólo admite escenarios de la misma matrícula.
6. El frontend consume OpenAPI mediante `packages/api-client`; el arrastre es
   una interacción cliente, pero mover por selector, bloquear, eliminar,
   duplicar, archivar y compartir usan los mismos endpoints tipados. La ruta
   `/api/v1/[...path]` de Next funciona como BFF para mutaciones del navegador,
   reenviando cookies y CSRF al backend interno.

## Consecuencias

- La historia real queda protegida por diseño y por pruebas de integración.
- Un escenario puede mostrar una advertencia aunque una persona decida
  conservar el cambio; no se pierde el cambio silenciosamente.
- Las preferencias se almacenan aunque el optimizador CP-SAT todavía no haya
  producido una solución; cuando se integre, deberá respetar las mismas
  restricciones y explicar sus objetivos.
- Las revisiones inválidas o incompletas son visibles como `UNKNOWN`, lo que
  obliga a resolver la calidad de la fuente antes de presentar una conclusión.
- El token compartible es un capability link; debe tratarse como sensible en
  logs y revocarse/desactivarse al apagar `sharing_enabled`.

## Rechazado

- Mutar `CourseAttempt` para representar un curso futuro.
- Evaluar AST, elegibilidad o graduación en el navegador.
- Guardar preferencias o locks como JSON global sin versionado por escenario.
- Exponer el escenario completo o identificadores de matrícula en una vista
  pública.
