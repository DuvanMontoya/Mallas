# P20 — Observabilidad y operación

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/20_OBSERVABILITY_OPERATIONS.md`.

## Skills obligatorias
- carga `feature-delivery`

## Objetivo

Implementar telemetría estructurada, health/readiness, tracing y métricas sin filtrar datos privados.

## Entregables obligatorios

1. Correlation IDs.
2. Structured logging.
3. OpenTelemetry backend.
4. Frontend error reporting adapter.
5. Health live/ready.
6. DB/job metrics.
7. Audit/optimizer timing.
8. PII redaction.
9. Operational dashboard spec.
10. Alerting runbooks.
11. Synthetic smoke checks.

## Gates de aceptación

- [ ] no secrets/PII en logs
- [ ] trace request end-to-end donde viable
- [ ] health distinguishes liveness/readiness
- [ ] failure observable
- [ ] runbooks exist

## Revisión

- Ejecuta subagente `security-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
