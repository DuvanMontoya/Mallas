# 20 — Observabilidad y operación

## Telemetría

- structured logs JSON;
- request correlation id;
- OpenTelemetry traces;
- métricas RED para API;
- métricas de jobs;
- audit metrics;
- frontend Web Vitals.

## Nunca loguear

- contraseñas;
- session tokens;
- secrets;
- archivos académicos completos;
- PII innecesaria.

## SLO propuestos

Definir después de baseline real. No inventar 99.99% sin capacidad operacional.

Métricas de producto:
- audit latency;
- graph compute latency;
- optimizer latency;
- import error rate;
- source freshness;
- unknown-rule count;
- failed publication attempts.

## Health

- `/health/live`
- `/health/ready`
- checks de DB y dependencias esenciales.
