# P11 — Grafo de dependencias y unlocks

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/05_RULE_ENGINE_SPEC.md`.
4. Lee `docs/12_UX_INFORMATION_ARCHITECTURE.md`.

## Skills obligatorias
- carga `feature-delivery`

## Objetivo

Construir proyección de grafo/hipergrafo que represente cursos y nodos de condición, con análisis directo/transitivo y explicación.

## Entregables obligatorios

1. Graph projection backend/domain desde AST.
2. Nodos de condición para thresholds/ALL/ANY cuando sea necesario.
3. Direct prerequisites, descendants, ancestors.
4. Transitive unlock analysis.
5. Shortest explanatory paths.
6. React Flow view lazy-loaded.
7. ELK auto-layout.
8. Filters y focus mode.
9. Alternative textual representation.
10. No modificar reglas arrastrando nodos en vista estudiante.
11. Cycle visualization para admin.

## Gates de aceptación

- [ ] thresholds no se falsifican como una simple arista curso→curso
- [ ] direct/transitive distinguishable
- [ ] alternative textual accessible
- [ ] large graph remains usable
- [ ] no graph data duplicates rules manually

## Revisión

- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `ux-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
