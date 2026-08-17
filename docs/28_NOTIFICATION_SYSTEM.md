# 28 — Notificaciones

Eventos útiles:
- nueva oferta publicada;
- curso planeado ahora ofertado;
- cambio curricular que afecta al usuario;
- requisito previamente UNKNOWN verificado;
- escenario queda inválido por cambio;
- fecha relevante configurada.

Canales:
- in-app primero;
- email opcional;
- push sólo si se justifica.

No enviar spam ni notificar cambios preliminares no publicados como si fueran oficiales.

## Implementación vigente

La primera entrega implementada cubre el evento `curriculum.revision.published`.
La publicación crea una `NotificationOutbox` dentro de la misma transacción que
la `PublicationEvent`; una revisión `DRAFT`, una transacción abortada o un
evento de publicación ausente nunca llega al centro de notificaciones. Un
worker posterior al commit ejecuta `process_notifications` y materializa, de
forma idempotente, una `NotificationEvent` inmutable y como máximo una
`NotificationDelivery` por combinación evento/usuario/canal.

El modelo separa responsabilidades:

- `NotificationEvent` identifica el hecho publicado, su versión de esquema,
  locale y un payload operacional mínimo (`publication_event_id` y
  `message_key`); no copia códigos de revisión, historia académica, correo ni
  datos de impacto personal.
- `NotificationDelivery` conserva el estado del canal (`QUEUED`, `SENDING`,
  `SENT`, `FAILED` o `SUPPRESSED`), el `dedupe_key`, los reintentos y, sólo
  para `IN_APP`, el `read_at`.
- `NotificationPreference` permite activar/desactivar in-app y email por tipo
  de evento y escoger `es-CO` o `en`. Las preferencias se consultan antes de
  crear cada entrega; desactivar un canal suprime la entrega sin borrar el
  evento auditable.

El centro autenticado usa:

- `GET /api/v1/notifications?unread_only=&limit=&before=` para el feed privado;
- `POST /api/v1/notifications/{delivery_id}/read` y
  `POST /api/v1/notifications/read-all` para el estado de lectura;
- `GET /api/v1/notifications/preferences` y
  `PUT /api/v1/notifications/preferences/{event_type}` para preferencias.

La UI muestra contador numérico accesible, lectura individual/global, estados
de carga/error, preferencias y un enlace interno controlado por el backend.
Los títulos y cuerpos proceden de un registro de plantillas localizable y son
deliberadamente generales. Los links externos, HTML recibido y payloads de
usuario no se renderizan.

Email es un adaptador opcional detrás de `NOTIFICATIONS_EMAIL_ENABLED=false`
por defecto. Si se activa, el adaptador recibe únicamente el correo del
destinatario en la frontera y el contenido estático ya localizado; el mismo
`dedupe_key` se entrega como clave de idempotencia. Un fallo de proveedor no
expone su detalle al usuario: deja la entrega en `FAILED` con backoff y permite
reintento sin duplicar el envío lógico.

La notificación enlaza el evento de publicación y el resumen de impacto, pero
no altera la auditoría, no selecciona la revisión aplicable a una matrícula y
no constituye una regla académica. Las filas de outbox y delivery son
auditables y las solicitudes fallidas quedan disponibles para reintento o
revisión operativa.
