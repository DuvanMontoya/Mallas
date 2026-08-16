# P22 — Accesibilidad y E2E cross-device

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/26_ACCESSIBILITY.md`.
4. Lee `docs/12_UX_INFORMATION_ARCHITECTURE.md`.
4. Lee `docs/19_TEST_STRATEGY.md`.

## Skills obligatorias
- carga `feature-delivery`

## Objetivo

Endurecer toda la experiencia para WCAG 2.2 AA, teclado, screen reader y mobile, y cerrar flujos E2E.

## Entregables obligatorios

1. axe suites por páginas críticas.
2. Keyboard E2E.
3. Alternative text/list for graph.
4. Accessible drag/drop alternative.
5. Focus management.
6. 200% zoom.
7. Reduced motion.
8. Contrast audit.
9. Mobile viewport E2E.
10. End-to-end student journey.
11. End-to-end editor/reviewer journey.
12. Document manual checks.

## Gates de aceptación

- [ ] no serious/critical axe
- [ ] todos flujos core sin mouse
- [ ] graph information accessible without canvas interaction
- [ ] planner usable mobile
- [ ] E2E core green

## Revisión

- Ejecuta subagente `ux-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
