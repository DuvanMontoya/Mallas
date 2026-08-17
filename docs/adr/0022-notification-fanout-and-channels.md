# ADR-0022 — Fan-out idempotente de notificaciones y canales opcionales

Estado: aceptado

Fecha: 2026-08-16

## Contexto

La publicación curricular es un hecho normativo inmutable, mientras que una
notificación es una proyección privada por usuario y canal. El producto necesita
un centro in-app con lectura y preferencias, y debe poder añadir email sin
acoplar el dominio académico a un proveedor externo. Un commit abortado no
puede producir un mensaje que anuncie una publicación inexistente; los reintentos
no pueden duplicar entregas lógicas ni revelar historia académica.

## Decisión

- La publicación crea `NotificationOutbox` dentro de la misma transacción que
  `PublicationEvent`. Un comando/worker posterior al commit ejecuta el
  dispatcher; el dominio no conoce Celery, RQ, Redis ni un broker.
- El dispatcher valida que la revisión fuente esté `PUBLISHED`, materializa un
  `NotificationEvent` inmutable y crea como máximo una entrega por
  evento/usuario/canal mediante unicidad y `dedupe_key`.
- `NotificationPreference` se evalúa antes del fan-out. In-app está habilitado
  por defecto; email está deshabilitado por defecto y sólo se crea como
  `QUEUED` para una cuenta con correo verificado y preferencia explícita.
- Las plantillas son locales, versionables y estáticas. El payload persistido y
  el contenido de ambos canales excluyen códigos de revisión, cursos,
  calificaciones, auditorías, PII e impacto individual.
- El adaptador email es una interfaz sustituible. Recibe el correo solamente
  en el boundary de entrega, el contenido ya renderizado y la clave estable de
  idempotencia; los fallos quedan en `FAILED` con backoff y código seguro.
- El feed HTTP sólo expone entregas in-app del usuario autenticado. La lectura
  individual y global es transaccional y no modifica la auditoría académica.

## Alternativas descartadas

- Enviar desde la petición de publicación: puede notificar un commit fallido y
  mezcla latencia/proveedor con la transacción normativa.
- Guardar un JSON de notificaciones en el usuario: impide deduplicación,
  auditoría, preferencias por canal y retención independiente.
- Dejar que el frontend construya el mensaje a partir del diff: filtra mal la
  privacidad y duplica reglas fuera del backend.
- Enviar todos los cambios preliminares: contradice la semántica de publicación
  y puede generar spam o falsa autoridad normativa.
- Introducir un broker distribuido para la primera implementación: el outbox y
  un comando idempotente cubren el volumen actual; cualquier cambio requiere
  ADR con evidencia operacional.

## Consecuencias

### Positivas

- La publicación, el outbox y la ausencia de mensajes en caso de rollback tienen
  una frontera transaccional clara.
- In-app, email y futuras salidas comparten evento, preferencias, plantillas y
  claves de deduplicación sin compartir datos académicos.
- Reintentos de proveedor son observables y seguros; la UI nunca presenta una
  entrega suprimida como recibida.

### Costes y límites

- Hace falta ejecutar `process_notifications` y observar filas `QUEUED`/
  `FAILED`; el outbox no es una promesa de entrega en ausencia de worker.
- El catálogo de eventos y plantillas debe ampliarse explícitamente antes de
  publicar un nuevo tipo. Un tipo desconocido produce error, no texto genérico
  inventado.
- La localización actual cubre `es-CO` y `en`; ampliar idiomas exige plantillas
  y pruebas de privacidad equivalentes.

## Condiciones de revisión

Revisar esta decisión si el volumen exige particionamiento, si se necesita push
con garantías distintas o si un proveedor requiere idempotencia distinta a la
clave estable por delivery. No introducir infraestructura nueva por anticipación.
