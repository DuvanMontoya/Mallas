# Alertas y runbooks operativos

Las alertas se habilitan sólo después del baseline definido en el dashboard.
Cada alerta incluye ventana, volumen mínimo, entorno, versión, correlation id
de un ejemplo y enlace a este runbook. Nunca se adjunta un body de request o
respuesta.

## API 5xx elevado

**Señal:** aumento sostenido de `curriculum_http_requests_total` con
`status_class="5xx"` frente al volumen de la ventana.

1. Confirmar `/health/live` y `/health/ready`.
2. Revisar logs JSON por `correlation_id`, `trace_id`, ruta normalizada y
   `error_type`; no copiar mensajes de excepción.
3. Comparar versión y cambios recientes de migración/configuración.
4. Si la causa es una release reversible, detener el tráfico nuevo y hacer
   rollback según el procedimiento de despliegue; no ejecutar `git reset` ni
   mutar datos para mitigar.
5. Repetir smoke sintético y registrar impacto, causa y evidencia.

## Readiness/DB fallando

**Señal:** `/health/ready` responde `503 NOT_READY` o aumentan los checks DB con
`outcome="error"`.

1. Mantener el proceso vivo fuera del balanceador; liveness no es una prueba de
   base de datos.
2. Confirmar conectividad, límites de conexiones, espacio y estado del
   PostgreSQL gestionado.
3. No imprimir `DATABASE_URL`, password ni SQL con valores.
4. Si la base está sana, revisar credenciales/rotación y migraciones pendientes
   en staging; en producción sólo ejecutar migraciones aprobadas.
5. Validar con `migrate --check`, readiness y smoke antes de reincorporar.

## Latencia por encima del baseline

**Señal:** percentiles de `curriculum_http_duration_seconds` o una operación
de dominio exceden la línea de referencia con volumen suficiente.

1. Separar endpoint, status class y job; no asumir que un promedio oculta la
   cola.
2. Consultar trazas por `trace_id` y revisar si el tiempo está en DB, motor
   determinista, graph projection o solver.
3. Reducir concurrencia/configuración sólo con una decisión registrada; nunca
   omitir auditoría o evidencia para acelerar.
4. Si es una regresión, detener la versión y abrir una reparación con test de
   latencia reproducible.

## Optimizer/job fallando o atascado

**Señal:** jobs `optimizer` con resultado `error`, duración anómala o estado
`RUNNING` sin progreso.

1. Verificar que el worker sigue ejecutando y que el proceso no fue reiniciado.
2. Consultar sólo estado, duración, cancelación y hashes; no exponer el
   snapshot del estudiante.
3. Cancelar de forma idempotente la ejecución atascada mediante la API
   autorizada.
4. Confirmar que el resultado no se marcó como éxito y repetir en un escenario
   mínimo reproducible.
5. Revisar límites de tiempo y memoria del solver; conservar explicación y
   estado epistemológico.

## Importación/publicación con error

**Señal:** aumenta la tasa de filas rechazadas, freshness vencida o eventos de
   publicación fallidos.

1. Mantener el batch o revisión en estado no publicable; no saltar el gate.
2. Revisar `SourceSnapshot`, evidencia, hash y errores estructurados con rol
   autorizado.
3. Confirmar si el problema es parseo, schema, evidencia faltante o conflicto
   normativo.
4. Corregir en un nuevo batch/revisión; una revisión publicada es inmutable.
5. Repetir auditoría curricular y prueba de contrato antes de publicar.

## Frontend Web Vitals/errores

**Señal:** crecimiento de `frontend.error` o degradación de LCP/CLS/FID por
   versión.

1. Confirmar si el endpoint de reporte está configurado y responde sin auth
   heredada ni cookies.
2. Agrupar por ruta normalizada, versión y tipo de error.
3. Reproducir en una sesión de prueba sin datos personales.
4. Verificar que el envelope no contiene mensaje, query string, token o PII.
5. Reparar, ejecutar unit/component/E2E y volver a comparar contra baseline.

## Escalamiento y cierre

El responsable de guardia registra timestamp, entorno, versión, señal,
correlation/trace id acotados, impacto, mitigación reversible, causa raíz y
prueba de recuperación. Incidentes de integridad curricular o privacidad se
escalan a gobierno/seguridad aunque la métrica operativa se recupere.
