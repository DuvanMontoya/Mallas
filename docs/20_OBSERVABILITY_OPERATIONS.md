# 20 — Observabilidad y operación

## Alcance y principios

La observabilidad describe el estado operativo del producto sin convertirse en
una fuente alternativa de reglas académicas. Los datos de telemetría son
agregados, acotados y reemplazables: el motor de dominio sigue siendo la
autoridad determinista y la base transaccional conserva la auditoría.

La implementación local no requiere un collector. En un entorno operacional se
configura un collector OpenTelemetry mediante `OTEL_EXPORTER_OTLP_ENDPOINT` o
los endpoints específicos de traces/metrics. Si el collector no está
configurado, el API conserva el health snapshot y los logs JSON locales, pero
no intenta realizar llamadas salientes.

## Telemetría

- logs estructurados JSON en `stdout`;
- `X-Request-ID` y `X-Trace-ID` en respuestas API;
- spans de servidor OpenTelemetry con propagación W3C `traceparent`;
- métricas RED para API: requests, status class y duración;
- métricas de jobs para optimización y dispatcher de notificaciones;
- duración/resultado de auditoría, grafo y operaciones de dominio;
- health checks de base de datos;
- Web Vitals frontend mediante un adaptador opt-in.

Las operaciones instrumentadas son `degree_audit`, `dependency_graph`,
`optimizer` y `notifications_dispatch`. El decorador de timing sólo mide y
re-lanza la excepción original; no cambia transacciones, resultados ni
semántica de jobs.

### Correlación y logs

`OriginAndSecurityMiddleware` valida o genera el request id antes de cualquier
respuesta API. `ObservabilityMiddleware` conserva el mismo valor en el
contexto de logging, añade el trace id cuando existe y registra únicamente:

- método;
- ruta normalizada sin query string ni identificadores;
- código/status class;
- duración;
- tipo de excepción, nunca su mensaje.

El formatter `modules.observability.logging.JsonFormatter` elimina traceback y
aplica redacción adicional a campos estructurados. Un `X-Request-ID` recibido
por el cliente sólo se acepta si coincide con el conjunto ASCII acotado
`[A-Za-z0-9._-]{1,80}`.

### Métricas y cardinalidad

El registro local acotado puede representarse como Prometheus mediante
`render_prometheus()` y como agregados sin etiquetas en
`GET /api/v1/health/metrics`. El endpoint devuelve 404 fuera de desarrollo si
no se configura `OBSERVABILITY_METRICS_TOKEN`; con token se usa el header
`X-Metrics-Token`. El snapshot no contiene PII, ids de estudiantes ni payloads
académicos.

Nombres operativos del registro Prometheus:

- `curriculum_http_requests_total`;
- `curriculum_http_duration_seconds`;
- `curriculum_db_health_checks_total`;
- `curriculum_jobs_total` y `curriculum_job_duration_seconds`;
- `curriculum_domain_operations_total` y `curriculum_domain_duration_seconds`.

Las etiquetas se limitan a vocabularios controlados: método, ruta normalizada,
status class, tipo de job/operación y resultado. No se etiquetan estudiantes,
emails, cursos introducidos libremente, excepciones, queries ni hashes de
documentos.

### OpenTelemetry

La resolución del backend fija `opentelemetry-sdk==1.44.0` y
`opentelemetry-exporter-otlp-proto-http==1.44.0`. El API crea un
`TracerProvider`/`MeterProvider` con `service.name`, `service.version` y
`deployment.environment`. El exportador HTTP sólo se activa con un endpoint
OTLP configurado. `OTEL_TRACE_CAPTURE=true` queda reservado para pruebas o
diagnóstico local y mantiene spans en memoria; no debe habilitarse como
almacenamiento de producción.

## Nunca loguear

- contraseñas;
- session tokens;
- secrets;
- cookies, CSRF, Authorization o API keys;
- archivos académicos completos;
- PII innecesaria.

La defensa combina allowlist en cada evento con redacción recursiva de claves y
patrones (emails, Bearer/JWT, UUIDs, ids numéricos extensos). Los errores de
frontend no envían el mensaje original: sólo el tipo, digest acotado, ruta
normalizada y fase controlada.

## SLO y baseline

No se publica un SLO numérico antes de reunir un baseline real. Durante el
primer período operacional se deben conservar al menos siete días de métricas
por endpoint normalizado y job, junto con volumen, horario y cambios de
versión. Después se propone el SLO con percentiles observados, presupuesto de
error, ventana y exclusiones explícitas. No inventar 99.99% sin capacidad
operacional.

Métricas de producto y gobierno:

- audit latency;
- graph compute latency;
- optimizer latency;
- import error rate;
- source freshness;
- unknown-rule count;
- failed publication attempts.

Las cuatro primeras tienen instrumentación de proceso/request. Source
freshness, unknown-rule count y publication failures se consultan desde sus
read models y eventos auditables; no se derivan de logs libres. Las definiciones
y ventanas deben quedar en el dashboard operativo antes de activar alertas.

## Health

- `/api/v1/health/live`: liveness puro; no toca la base de datos y responde si
  el proceso puede aceptar trabajo HTTP.
- `/api/v1/health/ready`: readiness; ejecuta `SELECT 1`, devuelve `200` con
  `database=ok` cuando está listo y `503 NOT_READY` con Problem Details seguro
  cuando la base de datos falla.
- `/api/v1/health/metrics`: snapshot agregado para operación; requiere token
  en producción y no reemplaza el collector.

La distinción es deliberada: un orquestador puede reiniciar un proceso que no
está vivo, mientras que un proceso vivo pero no ready debe retirarse del tráfico
sin perder la evidencia de la falla.

## Frontend

`ObservabilityClient` se monta una vez en el layout raíz. Escucha errores de
ventana/rechazos no manejados y PerformanceObserver para LCP, CLS y FID. El
adaptador `lib/observability.ts` no realiza requests si
`NEXT_PUBLIC_ERROR_REPORTING_ENDPOINT` está vacío; cuando se configura, usa
`credentials: omit`, elimina query/hash del endpoint y envía sólo un envelope
redactado. El error boundary usa el mismo adaptador y muestra un digest de
soporte sin revelar el mensaje.

## Smoke sintético

`python scripts/smoke.py --base-url http://localhost:8000` comprueba liveness,
readiness y el documento OpenAPI sin autenticarse ni registrar cuerpos. Puede
añadirse `--web-url http://localhost:3000` para verificar que la aplicación web
responde. El script devuelve código distinto de cero si una comprobación falla
y sólo imprime URL, status y una razón acotada.

El dashboard, las alertas y sus runbooks viven en:

- `docs/ops/OBSERVABILITY_DASHBOARD.md`;
- `docs/ops/ALERT_RUNBOOKS.md`;
- `docs/ops/SYNTHETIC_SMOKE.md`.
