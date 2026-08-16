# P18/P19 — Analítica estudiantil e institucional

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/22_ANALYTICS.md`.
4. Lee `docs/17_SECURITY_PRIVACY.md`.

## Skills obligatorias
- carga `feature-delivery`
- carga `security-change`

## Objetivo

Construir analítica útil sin crear perfiles opacos ni filtrar PII.

## Entregables obligatorios

1. Métricas estudiante derivadas del audit.
2. Trend de avance por snapshots.
3. Bottleneck analysis de cursos/requisitos.
4. Demand potential por planned/eligible students con autorización.
5. Aggregate institutional views.
6. Pseudonymization/minimization.
7. Role-gated analytics.
8. Export seguro.
9. Data definitions documentadas.
10. No predictive risk scoring opaco.

## Gates de aceptación

- [ ] métricas reproducibles
- [ ] no PII por defecto en agregados
- [ ] small-cell suppression si aplica
- [ ] roles correctos
- [ ] definitions visibles

## Revisión

- Ejecuta subagente `security-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
