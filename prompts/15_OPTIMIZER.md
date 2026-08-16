# P14 — Optimizador CP-SAT

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/11_PLANNER_OPTIMIZER.md`.
4. Lee `docs/06_DEGREE_AUDIT_SPEC.md`.

## Skills obligatorias
- carga `feature-delivery`

## Objetivo

Construir solver de trayectoria con OR-Tools CP-SAT, objetivos explicables, límites y manejo de incertidumbre.

## Entregables obligatorios

1. Model input canónico independiente de Django.
2. Variables x(course,term) y constraints.
3. Prerequisite ordering y corequisite.
4. Group/mandatory/credit completion.
5. Offerings conocidos y policy para unknown future offerings.
6. Credit min/max.
7. Locked user choices.
8. Schedule conflicts cuando sections selected.
9. Lexicographic objectives documentados.
10. Time limits/cancellation.
11. Statuses OPTIMAL/FEASIBLE/INFEASIBLE/UNKNOWN.
12. Explanation de cada decisión.
13. OptimizationRun persistido con input/output hash/solver version.
14. Property/golden tests con escenarios pequeños verificables.
15. UI que compara solución con escenario.

## Gates de aceptación

- [ ] solver nunca produce plan académicamente inválido según facts conocidos
- [ ] INFEASIBLE explica restricciones conflictivas
- [ ] no pesos mágicos sin docs
- [ ] determinismo razonable/configurable
- [ ] time limit manejado
- [ ] tests de casos óptimos pequeños

## Revisión

- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `ux-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
