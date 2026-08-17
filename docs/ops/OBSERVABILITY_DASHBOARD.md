# Dashboard operativo de Curriculum Navigator

Este documento es la especificación fuente del dashboard. Las consultas deben
apuntar al collector/backend compatible con OpenTelemetry o a una conversión
Prometheus del registro del API. El dashboard no presenta decisiones de grado
como si fueran métricas operativas y no muestra identificadores individuales.

## Variables y filtros

- `service.name`: `curriculum-navigator-api`;
- `deployment.environment`: `development`, `staging` o `production`;
- ventana temporal seleccionable;
- versión desplegada;
- ruta normalizada (sin ids ni query strings);
- método y status class;
- tipo de job/operación y resultado.

No se ofrece un filtro por estudiante, email, matrícula, token, hash de
documento o payload de importación.

## Paneles mínimos

| Panel | Fuente | Lectura operacional |
| --- | --- | --- |
| Requests por status class | `curriculum_http_requests_total` | volumen, 4xx y 5xx; separar fallas del cliente de fallas del servicio |
| Duración API p50/p95/p99 | `curriculum_http_duration_seconds` | comparar con baseline por ruta normalizada y método |
| Readiness/DB | `curriculum_db_health_checks_total` y checks del orquestador | distinguir proceso vivo de dependencia lista |
| Auditoría | `curriculum_domain_duration_seconds{kind="degree_audit"}` | latencia y errores del motor persistido |
| Grafo | `curriculum_domain_duration_seconds{kind="dependency_graph"}` | coste de proyección y rutas problemáticas |
| Optimización | `curriculum_job_duration_seconds{kind="optimizer"}` | ejecución, cancelación, error y tiempo de solver |
| Notificaciones | `curriculum_job_duration_seconds{kind="notifications_dispatch"}` | backlog/falla del worker; no contenido de mensajes |
| Importaciones | read model de batches y eventos auditados | tasa de filas aceptadas/rechazadas y freshness de fuente |
| Publicación | eventos de gobernanza | intentos fallidos y estado de la revisión, sin exponer borradores |
| Web Vitals | envelope frontend opt-in | LCP/CLS/FID por versión y ruta; sin sesión ni PII |

## Cálculos

1. `error_rate = 5xx / total requests` para ventanas con volumen suficiente.
2. `readiness_failures` cuenta resultados `error` de DB y no los reinicios.
3. Latencias usan histogramas y percentiles del backend, no promedios solos.
4. La tasa de importación se calcula desde el modelo de importación, no desde
   líneas de log.
5. `unknown-rule-count` se toma de resultados de auditoría y revisiones
   publicadas con su estado epistemológico.
6. Duración observada a grado sólo se publica con la advertencia de que es una
   derivación de términos disponibles, no una duración normativa.

## Baseline y SLO

Durante siete días se guarda el volumen y percentiles por ruta/job, separado
por entorno y versión. El responsable operacional propone después objetivos
con evidencia, ventana y presupuesto de error. Hasta esa revisión el dashboard
usa líneas de referencia informativas, no alertas de SLO inventadas.

## Privacidad y retención

El dashboard debe aplicar la misma política de retención del collector y del
backend de logs. No se ingieren cuerpos, query strings, cookies, tokens,
mensajes de excepción, nombres de estudiantes ni archivos académicos. Los
exports del dashboard son agregados y se auditan cuando salen del entorno
operativo.
