# 36 — Eventos de dominio/aplicación

Eventos previstos, con payload versionado y sin PII innecesaria:

- `curriculum.revision.created`
- `curriculum.revision.validated`
- `curriculum.revision.published`
- `curriculum.revision.superseded`
- `student.history.changed`
- `degree_audit.recomputed`
- `offering.snapshot.imported`
- `plan_scenario.optimized`
- `notification.requested`
- `import.completed`

Inicialmente pueden resolverse dentro del monolito/outbox transaccional. No introducir broker distribuido sin ADR.
