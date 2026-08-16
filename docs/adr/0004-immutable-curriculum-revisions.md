# ADR-0004 — Revisiones curriculares publicadas son inmutables

**Estado:** ACCEPTED

## Decisión
`CurriculumPlan` identifica el plan lógico; `CurriculumRevision` representa su estado normativo durante una vigencia. Una revisión `PUBLISHED` no se edita. Un cambio normativo crea una revisión nueva con diff, evidencia y trazabilidad.

## Consecuencia
Una auditoría histórica puede reproducirse exactamente usando la revisión que le correspondía.
