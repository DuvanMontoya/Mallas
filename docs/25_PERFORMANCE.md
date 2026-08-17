# 25 — Performance

## Presupuesto inicial orientativo, validar con profiling

- overview/audit cached read: objetivo p95 < 500 ms;
- rule evaluation en memoria: milisegundos para un plan individual;
- graph projection: < 250 ms backend o local según tamaño;
- optimizer: mostrar progreso/estado; límite configurable.

No optimizar con infraestructura prematura.

## Estrategias

- precompute transitive closure por revisión si profiling lo justifica;
- cache de auditoría por fingerprint;
- DB indexes por plan/revision/course/term/student;
- select/prefetch explícitos;
- pagination;
- lazy load React Flow;
- payloads read-model;
- compression.

## Regression benchmarks

Crear benchmarks del motor y consultas críticas; CI puede alertar en degradaciones grandes.

## P21 — Baseline verificado

El baseline ejecutable y las decisiones de P21 están en
`docs/ops/PERFORMANCE_BASELINE.md` y `docs/adr/0025-performance-read-paths-and-job-bounds.md`.
La auditoría redujo el caso válido del plan 2514 de 164 a 19 consultas al
precargar evidencias, y la selección de enrollment dejó de sondear cinco
estados con consultas separadas. No se introdujo una caché académica ni un
índice sin evidencia de `EXPLAIN`. El frontend mantiene la carga diferida de
React Flow/ELK y el optimizador tiene límites explícitos de tiempo, workers y
jobs en vuelo.
