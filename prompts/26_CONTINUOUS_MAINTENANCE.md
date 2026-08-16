# P26 — Mantenimiento continuo

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/32_TECH_UPDATE_POLICY.md`.
4. Lee `docs/08_DATA_PROVENANCE_GOVERNANCE.md`.

## Skills obligatorias
- carga `dependency-upgrade`
- carga `curriculum-change`
- carga `source-research`

## Objetivo

Configurar el producto para mantenerse actualizado técnica y normativamente sin depender de memoria humana/LLM.

## Entregables obligatorios

1. Renovate production-ready.
2. Scheduled CI dependency checks.
3. Security advisories workflow.
4. Normative source watch design/job where source permits.
5. Source freshness reports.
6. Unknown rule queue.
7. Tech baseline update command/process.
8. Release cadence/runbook.
9. Database maintenance.
10. Backup restore schedule.
11. Periodic accessibility/security audits.
12. Agent memory/state maintenance.

## Gates de aceptación

- [ ] no auto-publish normative changes
- [ ] dependency updates gated by CI
- [ ] freshness observable
- [ ] runbooks complete
- [ ] state recovery verified

## Revisión

- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `security-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `curriculum-auditor` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
