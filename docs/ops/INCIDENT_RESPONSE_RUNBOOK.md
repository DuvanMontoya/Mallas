# Respuesta a incidentes de producción

**Versión:** 1.0  
**Fecha de revisión:** 2026-08-17  
**Estado del entorno durante P95:** no hay incidente de producción activo ni alerta operativa abierta en este checkout.

Este runbook complementa `ALERT_RUNBOOKS.md`, `SECURITY_RUNBOOK.md`,
`BACKUP_RESTORE_RUNBOOK.md` y `ROLLBACK_RUNBOOK.md`. No reemplaza la autoridad
del equipo institucional de infraestructura, seguridad o protección de datos.

## Prioridades

1. Proteger personas, datos académicos y evidencia.
2. Contener el impacto y conservar el servicio seguro.
3. Preservar logs, trazas, hashes, imágenes y configuración sin sobrescribirlos.
4. Restaurar desde una imagen/backup verificado, no desde un cambio manual opaco.
5. Corregir la causa raíz con un test o monitor de no regresión.

## Clasificación inicial

| Severidad | Criterio orientativo | Primera acción |
|---|---|---|
| SEV-1 | exposición de datos, pérdida/corrupción de historia o indisponibilidad total | activar incident commander, congelar writes si es seguro, preservar evidencia, escalar seguridad/datos |
| SEV-2 | degradación material del servicio, error de auditoría o publicación curricular incorrecta contenida | contener superficie, comparar hashes/revisión, abrir rollback o corrección controlada |
| SEV-3 | fallo acotado sin pérdida de integridad ni exposición | ticket, reproducción mínima, hotfix con test y ventana normal |
| SEV-4 | alerta menor, copy, observabilidad o deuda sin impacto de usuario | priorizar en backlog sin intervención impulsiva |

La severidad se basa en impacto confirmado o razonablemente probable, no en la
cantidad de ruido de logs. Si hay duda entre dos niveles, usar el más alto hasta
preservar evidencia.

## Secuencia operativa

### 1. Identificar y declarar

- Registrar hora UTC/local, quien detecta, servicio, versión de imagen por digest,
  revisión curricular activa, correlación y alcance conocido.
- Abrir un incidente con canal y responsable explícito; no coordinar cambios
  destructivos sólo por chat.
- Consultar `live`, `ready`, métricas RED, trazas, logs estructurados y alertas.

### 2. Contener sin destruir evidencia

- Detener una ruta de escritura o ponerla en mantenimiento únicamente con orden
  del responsable del incidente; no borrar filas, logs, backups ni imágenes.
- Aislar una fuente externa, archivo importado, endpoint o imagen sospechosa
  según los runbooks de seguridad.
- Si hubo secreto expuesto, rotarlo por el secret manager autorizado y registrar
  la rotación sin copiar el secreto al ticket.
- Si hay sospecha de corrupción, detener promociones y tomar backup antes de
  intentar reparar.

### 3. Preservar evidencia

Conservar de forma inmutable y con hash:

- logs y trazas del intervalo;
- `X-Request-ID`/`X-Trace-ID`, payloads sanitizados y respuestas de error;
- manifest de release, digests de imagen y configuración efectiva no secreta;
- snapshots de fuentes, `source_set_hash`, `content_hash`, AST y eventos de
  auditoría;
- backup y metadata de backup, nunca credenciales.

No ejecutar `git reset --hard`, no borrar logs y no sobreescribir un backup
existente para “reintentar”.

### 4. Diagnosticar y reproducir

- Reducir a un input mínimo y registrar el contrato/invariante violado.
- Distinguir error de UI, BFF/API, servicio de aplicación, dominio puro,
  persistencia, oferta externa o despliegue.
- Si se afecta una regla académica, solicitar revisión curricular humana y
  mantener la salida `UNKNOWN`/`DISPUTED` hasta resolver procedencia.
- Si se afecta auth, privacidad, SSRF, uploads o integridad, activar revisión de
  seguridad antes de publicar el hotfix.

### 5. Recuperar

- Para una regresión de aplicación sin migración incompatible, seguir
  `ROLLBACK_RUNBOOK.md` y promover sólo un digest ya construido y verificado.
- Para corrupción o pérdida, seguir `BACKUP_RESTORE_RUNBOOK.md`: restaurar
  primero en una base aislada, validar migraciones, conteo de tablas, integridad
  y checks de aplicación, y sólo después preparar recuperación aprobada.
- No editar una revisión curricular publicada; una corrección es una nueva
  revisión con evidencia y diff auditable.
- Ejecutar smoke de live/ready, login, dashboard, malla, auditoría, oferta,
  planner y governance antes de cerrar.

### 6. Cerrar y prevenir recurrencia

El postmortem debe ser sin culpa y contener:

- resumen, cronología y detección;
- impacto técnico, académico, de privacidad y usuarios afectados;
- causa raíz y factores contribuyentes;
- qué contuvo/recuperó el servicio y qué no funcionó;
- evidencia y enlaces al incidente/backup/release digest;
- acciones con responsable, prioridad y fecha;
- test, alerta, guard de procedencia o cambio de runbook que evite la recurrencia.

El incidente se cierra sólo cuando las verificaciones y acciones quedan
registradas; “el servicio volvió” no basta para declarar resolución.

## Estado de P95

No se creó un hotfix ni una migración porque no existe un incidente activo que
reproducir. La infraestructura de respuesta está cubierta por este runbook y
los runbooks enlazados. Las limitaciones actuales del entorno de desarrollo
(Docker, Python 3.14 y acceso a dependencias) son bloqueos de verificación del
goal, no un incidente de producción.
