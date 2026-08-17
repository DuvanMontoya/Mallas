# ADR-0021 — Publicación transaccional, impacto y outbox

Estado: aceptado

Fecha: 2026-08-16

## Contexto

Publicar una revisión curricular cambia la fuente normativa vigente, pero no
debe reescribir las auditorías ni decidir silenciosamente qué revisión aplica a
cada estudiante. El sistema debe poder demostrar qué cambió, qué matrículas y
auditorías podrían verse afectadas, y qué trabajo queda pendiente. Las
notificaciones sólo son válidas después de que la publicación haya confirmado
su transacción.

## Decisión

La publicación se implementa como un único servicio transaccional con estos
límites:

- se bloquean la propuesta, la candidata y la revisión publicada vigente;
- se valida que la propuesta sea `APPROVED`, que no tenga candidatos
  pendientes, que la validación no tenga errores bloqueantes y que su base
  siga siendo la revisión vigente;
- `CurriculumRevisionService.publish` marca la revisión anterior como
  `SUPERSEDED`, enlaza `supersedes` y publica la candidata; el contenido
  publicado queda inmutable;
- `PublicationEvent` conserva la relación de publicación/supersesión, el diff
  semántico, el resumen de impacto, los planes de trabajo y un `event_key`
  idempotente;
- `PublicationImpact` conserva, por matrícula afectada, la revisión anterior,
  la última auditoría y su hash, los cambios relevantes y una clave estable de
  recomputación. No actualiza `ProgramEnrollment.revision_basis` ni la
  auditoría histórica;
- `NotificationOutbox` se crea dentro de la transacción, pero sólo puede ser
  despachado después del commit. Usa una clave de deduplicación y estados
  explícitos;
- una corrección o rollback funcional se publica como nueva revisión. No se
  borran ni se editan publicaciones, eventos o auditorías históricos;
- la ejecución de recomputaciones queda detrás de una interfaz de jobs y cada
  impacto exige decisión sobre la revisión aplicable antes de producir una
  nueva auditoría oficial.

La lectura editorial de estos datos se expone en
`GET /api/v1/governance/publications/{publication_id}/impact` y reutiliza el
alcance institucional/programático del backoffice.

## Alternativas descartadas

- Mutar la revisión publicada y recalcular en línea: destruye reproducibilidad,
  mezcla la fuente normativa con el estado de estudiantes y no permite explicar
  auditorías históricas.
- Cambiar automáticamente la revisión base de todas las matrículas: puede
  aplicar una regla posterior a una cohorte sin decisión normativa individual.
- Enviar notificaciones directamente desde la petición HTTP: un commit fallido
  podría dejar mensajes que anuncian una publicación inexistente y los reintentos
  no serían idempotentes.
- Publicar desde un LLM o aceptar una inferencia como `VERIFIED`: contradice la
  autoridad de la evidencia normativa y la separación editorial/revisora.
- Introducir Kafka/Redis sólo para este flujo: añade una dependencia de
  infraestructura sin necesidad demostrada; el outbox y el dispatcher
  reemplazable cubren la garantía requerida en el monolito.

## Consecuencias

### Positivas

- La transición de publicación, supersesión, impacto y solicitudes de
  notificación tiene consistencia atómica.
- Las auditorías antiguas conservan revisión, entrada y hash de resultado, por
  lo que siguen siendo explicables tras una publicación posterior.
- La UI y los operadores pueden identificar afectados y trabajos pendientes
  sin presentar una recomputación no autorizada como hecho histórico.
- El dispatcher puede reintentarse con `dedupe_key` sin duplicar notificaciones.

### Costes y límites

- La publicación escribe filas de impacto potencialmente numerosas; el trabajo
  pesado se mantiene fuera de la transacción mediante jobs posteriores.
- La tabla `NotificationOutbox` es una solicitud durable, no una garantía de
  entrega. La entrega y los reintentos requieren un worker y observabilidad.
- Una matrícula puede requerir revisión administrativa antes de que exista una
  nueva auditoría oficial; el producto debe mostrar ese estado como pendiente,
  no como aprobado o rechazado.

## Riesgos y revisión

- Si el dispatcher no se ejecuta, las filas `QUEUED` deben aparecer en
  operaciones y poder reintentarse sin alterar el evento.
- Si aparecen más de dos fuentes de verdad para la aplicabilidad de una
  revisión, debe añadirse una decisión de gobernanza antes de automatizarla.
- Si el volumen de impactos excede la capacidad de la transacción, medir y
  documentar una estrategia de partición/encolado que conserve la garantía
  atómica; no introducir un broker por anticipación.
