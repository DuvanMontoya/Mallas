# P15 — Backoffice y gobernanza

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/23_ADMIN_BACKOFFICE.md`.
4. Lee `docs/08_DATA_PROVENANCE_GOVERNANCE.md`.
4. Lee `docs/18_AUTHORIZATION_MATRIX.md`.

## Skills obligatorias
- carga `feature-delivery`
- carga `curriculum-change`
- carga `security-change`

## Objetivo

Construir backoffice productivo para fuentes, extracción, drafts, evidencia, diff, revisión y publicación controlada.

## Entregables obligatorios

1. Source Inbox.
2. Document/Snapshot viewer.
3. Candidate extraction review.
4. Rule inspector AST + human explanation.
5. Evidence linking.
6. Semantic diff.
7. Validation report.
8. Review queue.
9. Editor/Reviewer separation.
10. Optimistic locking.
11. Audit trail.
12. Accessibility del backoffice.
13. No edición directa de published revision.
14. Bulk operations seguras con preview.

## Gates de aceptación

- [ ] editor no puede autoaprobar según role policy
- [ ] published immutable
- [ ] cada verified rule tiene evidence
- [ ] diff semantic
- [ ] concurrency conflict visible
- [ ] audit log completo

## Revisión

- Ejecuta subagente `security-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `curriculum-auditor` y resuelve todos los Critical/High.
- Ejecuta subagente `ux-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
