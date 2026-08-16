# P25 — Auditoría integral de producción

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/00_PRODUCT_SCOPE.md`.
4. Lee `docs/19_TEST_STRATEGY.md`.
4. Lee `docs/state/ROADMAP_STATUS.json`.

## Skills obligatorias
- carga `release`

## Objetivo

Demostrar que el producto completo, no un MVP, cumple alcance, correctitud, seguridad, UX y operación.

## Entregables obligatorios

1. Crear traceability matrix: cada requirement de PRODUCT_SCOPE → implementación → tests.
2. Buscar TODO/FIXME/stubs/hardcodes/mocks productivos.
3. Ejecutar suite completa.
4. Ejecutar property/golden tests.
5. Ejecutar E2E student/editor/reviewer.
6. Accessibility audit.
7. Security review.
8. Architecture review.
9. Curriculum audit.
10. Performance smoke/load.
11. OpenAPI freshness.
12. Migration from empty + representative previous state.
13. Backup restore drill.
14. Production smoke.
15. Docs clone-clean test.
16. Clasificar cualquier gap y corregirlo antes de cerrar.

## Gates de aceptación

- [ ] 100% requirements traceados o explícitamente bloqueados por dependencia externa real con fallback completo
- [ ] no Critical/High
- [ ] no scope TODO
- [ ] verify green
- [ ] E2E green
- [ ] restore green
- [ ] curriculum evidence valid

## Revisión

- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `security-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `ux-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `curriculum-auditor` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
