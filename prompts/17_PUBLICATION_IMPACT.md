# P16 — Publicación e impacto

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/07_CURRICULUM_VERSIONING.md`.
4. Lee `docs/08_DATA_PROVENANCE_GOVERNANCE.md`.
4. Lee `docs/23_ADMIN_BACKOFFICE.md`.

## Skills obligatorias
- carga `curriculum-change`
- carga `feature-delivery`
- carga `db-migration`

## Objetivo

Implementar publicación transaccional de revisiones y análisis de impacto sin alterar retrospectivamente auditorías.

## Entregables obligatorios

1. Pre-publication validation gate.
2. Impact analysis: changed rules/courses/groups.
3. Identify affected enrollments/audits.
4. Transaction + immutable content hash.
5. PublicationEvent.
6. Supersession relation.
7. Background recompute plan.
8. Preserve old audit reproducibility.
9. Notify affected users sólo tras publication.
10. Rollback semantics mediante nueva revisión/corrección, no mutación histórica.

## Gates de aceptación

- [ ] publicación falla si invalid
- [ ] old audit remains explainable
- [ ] new revision immutable
- [ ] affected users identified
- [ ] transactional consistency
- [ ] no LLM auto-publish

## Revisión

- Ejecuta subagente `curriculum-auditor` y resuelve todos los Critical/High.
- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `security-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
