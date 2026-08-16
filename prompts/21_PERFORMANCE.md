# P21 — Performance y escala

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/25_PERFORMANCE.md`.

## Skills obligatorias
- carga `feature-delivery`

## Objetivo

Medir y endurecer rutas críticas con benchmarks y query analysis, sin introducir infraestructura por intuición.

## Entregables obligatorios

1. Benchmark rule engine/audit.
2. Profile DB overview/audit queries.
3. Eliminate N+1.
4. Indexes basados en explain/análisis.
5. Cache audit por fingerprint si medido.
6. Graph projection optimizations.
7. Lazy load/JS bundle audit frontend.
8. Optimizer limits.
9. Load test de endpoints críticos.
10. Document before/after.

## Gates de aceptación

- [ ] regression benchmarks
- [ ] no cache como source of truth
- [ ] no Redis sólo por performance hipotética
- [ ] p95 medido en ambiente definido
- [ ] no degradación de correctitud

## Revisión

- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
