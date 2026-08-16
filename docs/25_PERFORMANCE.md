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
