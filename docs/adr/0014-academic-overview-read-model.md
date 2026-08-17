# ADR-0014 — Read model de resumen académico

**Estado:** ACCEPTED

## Contexto

El motor de auditoría produce un resultado reproducible y explicable, pero el
dashboard necesita combinarlo con etiquetas de cursos/agrupaciones, evidencia,
estado de historia, deep links y un catálogo de cursos elegibles o bloqueados.
Duplicar esa composición en Next haría que la UI pudiera divergir del motor y
confundir créditos aprobados con créditos aplicados.

## Decisión

Se publica `GET /api/v1/academic-overview` como read model autenticado del
bounded context `audit`. `modules.audit.application.overview`:

1. resuelve el enrollment con ownership/RBAC;
2. lee el último `DegreeAuditResult` persistido y sus fingerprints/hash;
3. usa un preview determinista sin escritura sólo cuando todavía no existe un
   audit persistido;
4. enriquece grupos, cursos, requisitos y evidencia mediante consultas
   explícitas;
5. entrega estados `NO_HISTORY`, `INCOMPLETE` o `READY`, más
   `eligible_courses`, `blocked_courses`, `unknown_courses`, requisitos
   externos, advertencias y deep links.

La UI consume el contrato generado desde OpenAPI y sólo presenta los hechos.
Los requisitos externos permanecen fuera del ledger de créditos y un
`UNKNOWN` nunca se transforma en elegible, satisfecho o graduado por el
frontend.

## Consecuencias

- El dashboard tiene una fuente de verdad única y puede cachear por ETag/hash.
- La lectura normal no crea auditorías; las mutaciones que cambian historia
  siguen recalculando y persistiendo la ejecución dentro de su transacción.
- El payload es más rico que `DegreeAuditResult.payload`, pero sus conclusiones
  siguen siendo las del motor puro y conserva trazabilidad de revisión,
  fingerprint, versión y evidencia.
- La proyección de oferta, planificación y grafo se agregará en sus bounded
  contexts; este read model no inventa esos estados.
