# P21 — Baseline de rendimiento y escala

## Entorno medido

La medición reproducible se ejecutó el 16 de agosto de 2026 con:

- Windows local, Python 3.14.7, `uv` 0.11.19;
- PostgreSQL 18.0 en `127.0.0.1:5432`, base `curriculum`;
- API Django en modo local con plan archivado `2514-AC496-2023` y 102 cursos;
- una muestra de calentamiento, seguida de 15 iteraciones por servicio;
- `scripts/benchmark_performance.py --iterations 15 --explain`, ejecutado
  desde `apps/api` con la `DATABASE_URL` local.

Los percentiles de servicio son mediciones de proceso y base de datos, no SLO
de producción. Los tiempos HTTP concurrentes de `runserver` se reportan por
separado porque ese servidor local no representa el worker/proxy de producción.

## Resultado antes/después

| Operación | Antes | Después | Consultas después | Payload |
| --- | ---: | ---: | ---: | ---: |
| Motor de reglas, 73 evaluaciones/iteración | 16.30 µs/evaluación | p50 15.868 / p95 16.489 µs | n/a | n/a |
| Malla pública | p50 134.833 / p95 146.374 ms | p50 135.560 / p95 172.191 ms | 16 | 185,893 B |
| Grafo con foco | p50 147.504 / p95 159.863 ms | p50 146.784 / p95 168.314 ms | 16 | 113,937 B |
| Auditoría de enrollment válido | p50 681.149 / p95 713.722 ms; 164 consultas | p50 192.993 / p95 239.645 ms | 19 | 382,072 B |

La comparación de la malla y el grafo se hizo en ejecuciones separadas y por
eso no debe interpretarse como una mejora estadística concluyente de latencia;
la prueba de regresión fuerte para esas rutas es la estabilidad semántica y el
presupuesto de consultas. La mejora de auditoría sí está sustentada por la
caída de 164 a 19 consultas: `build_revision_snapshot` hacía una consulta por
requisito al resolver `requirement.evidence`; ahora precarga
`evidence__snapshot` antes de construir el AST de auditoría.

La selección automática de enrollment también pasó de hasta cinco consultas
secuenciales (una por estado prioritario) a una consulta con `CASE` y el mismo
orden explícito: `ACTIVE`, `NEEDS_REVIEW`, `COMPLETED`, `SUSPENDED`,
`WITHDRAWN`, y luego el más reciente.

## Planes e índices

Los `EXPLAIN (FORMAT JSON)` de la misma ejecución muestran:

- la búsqueda de la revisión publicada usa el índice parcial
  `revision_one_published_per_plan`; el escaneo de `curriculumplan` queda en la
  tabla pequeña de planes y no justifica otro índice;
- la última auditoría usa `audit_run_enrollment_time_idx` y el enlace one-to-one
  de `DegreeAuditResult` usa su índice único;
- las rutas ya tienen índices compuestos para `revision/status`,
  `revision/role`, `enrollment/status`, `course_version/term`,
  `term/status` y `section/day/start`.

No se añadió una migración de índices: el profiling no mostró una consulta
crítica sin cobertura y crear índices adicionales habría aumentado el coste de
escritura sin evidencia de beneficio.

## Cache y fuente de verdad

No se añadió Redis ni una caché de resultados académicos. El último
`DegreeAuditResult.payload` persistido es el read model reproducible y la
fuente de verdad de una auditoría publicada; la vista sólo calcula un preview
de lectura para un enrollment nuevo que aún no tiene un run persistido. El
ETag de malla y auditoría permite revalidación HTTP sin duplicar estado
académico. Una caché por fingerprint sólo se evaluará si las métricas de
producción muestran que el read model persistido no alcanza el presupuesto.

## Grafo, frontend y optimizador

- El foco del grafo construye una sola vez la adyacencia semántica y un índice
  `node_id → node`; la malla construye una vez el índice inverso de cursos
  desbloqueados. Esto no modifica nodos, aristas, ciclos ni explicaciones.
- `DependencyGraphShell` mantiene `dynamic(..., { ssr: false })`, por lo que
  React Flow y ELK permanecen en la ruta del grafo. `pnpm audit:bundle` midió
  19 chunks y 2,444.6 KiB comprimidos sin compresión de transporte; el mayor
  chunk fue 1,602.7 KiB y está asociado a la ruta interactiva pesada.
- CP-SAT conserva un límite máximo de 300 s por ejecución, dos workers y una
  capacidad máxima de 20 trabajos en vuelo (ejecutando o en cola). Cuando se
  alcanza la capacidad, el run queda registrado como `REJECTED` con
  `termination_reason=optimization_capacity` y la API responde 409; no se
  acepta una cola ilimitada en memoria.

## HTTP y límites de interpretación

Con la API local en `8020`, `scripts/load_test.py` ejecutó 20 requests
secuenciales (10 por endpoint):

- `/api/v1/health/live`: p50 5.148 ms, p95 32.088 ms, 20/20 HTTP 200;
- `/api/v1/curriculum-map`: p50 289.791 ms, p95 321.625 ms, 20/20 HTTP 200.

Una corrida exploratoria con concurrencia 4 tuvo p95 de 1,690.549 ms para
liveness y 3,132.235 ms para la malla bajo `runserver`. Se conserva como
señal de contención del entorno de desarrollo, no como SLO: antes de fijar
presupuestos de producción se debe repetir con el servidor de despliegue,
pool de conexiones y volumen representativo, y observar al menos siete días
de métricas agregadas.

## Regresión ejecutable

Desde `apps/api`:

```powershell
$env:DATABASE_URL = 'postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum'
uv run --frozen python ..\..\scripts\benchmark_performance.py --iterations 15 --explain
uv run --frozen python -m pytest -q tests/test_performance.py
```

Desde la raíz, con el frontend construido:

```powershell
pnpm --dir apps/web audit:bundle
python scripts/load_test.py --base-url http://127.0.0.1:8020 --requests 40 --concurrency 4
```

Los tests de rendimiento no debilitan aserciones académicas: verifican la
prioridad exacta de enrollment, una consulta para el caso vacío, presupuestos
de consultas de malla/grafo y rechazo de la capacidad de optimización.
