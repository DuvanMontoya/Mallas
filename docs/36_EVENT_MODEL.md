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

## Publicación implementada

`PublicationEvent` es el registro inmutable de
`curriculum.revision.published`. Usa `schema_version`, `event_key` idempotente,
la revisión publicada, la relación de supersesión, los buckets del diff
semántico, el resumen de impacto y los planes de trabajos y notificación. Su
payload no contiene datos personales innecesarios.

`PublicationImpact` enlaza el evento con cada `ProgramEnrollment` que tenía la
revisión sustituida, conserva la auditoría previa y su hash, y expone un
`recompute_job_key` con estado explícito. No cambia por sí solo la revisión
base de la matrícula ni la auditoría histórica.

`NotificationOutbox` es una solicitud durable creada en la transacción de
publicación. El despachador sólo puede intentar entregarla después del commit,
usa `dedupe_key` y estados `QUEUED/SENDING/SENT/FAILED/SUPPRESSED`, y no
convierte una notificación en evidencia normativa. `NotificationEvent` es
inmutable y se materializa una sola vez por `PublicationEvent`; cada canal y
destinatario queda protegido por una unicidad de entrega. La entrega in-app
mantiene `read_at`; email usa backoff, una clave de idempotencia estable y un
adaptador reemplazable. Las preferencias se evalúan antes del fan-out y una
supresión no borra el evento. Si la publicación falla, ninguno de estos
registros queda persistido; si falla sólo un proveedor, el evento y su delivery
permanecen auditables para reintento.
