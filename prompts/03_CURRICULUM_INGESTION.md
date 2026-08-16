# P02 — Ingestión y gobernanza curricular

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/08_DATA_PROVENANCE_GOVERNANCE.md`.
4. Lee `docs/31_CURRICULUM_2514_BASELINE.md`.
4. Lee `docs/29_IMPORTS.md`.
4. Lee `docs/23_ADMIN_BACKOFFICE.md`.

## Skills obligatorias
- carga `curriculum-change`
- carga `source-research`
- carga `db-migration`

## Objetivo

Construir pipeline idempotente de fuentes y convertir el baseline 2514 en entidades DRAFT con evidencia, preservando ambigüedades.

## Entregables obligatorios

1. Implementar importador del JSON baseline con schema/version y fingerprint.
2. Importar documento fuente/snapshot con hash y locators por página.
3. Crear DRAFT revision 2514 sin auto-publicarla.
4. Crear Course/CourseVersion/memberships/grupos de forma idempotente.
5. Importar requisitos con epistemic_status y Evidence.
6. Crear validadores de totales, referencias, ciclos y ambigüedades.
7. Implementar ChangeProposal y semantic diff base.
8. Crear management commands `import_curriculum`, `validate_curriculum`, `diff_curriculum`.
9. Generar reporte humano de ingestión.
10. Añadir tests para reimportar dos veces sin duplicar.
11. No resolver UNKNOWN por intuición.
12. Si encuentras fuentes oficiales actuales que resuelven ambigüedades, guarda snapshot/evidencia y somete el cambio al workflow.

## Gates de aceptación

- [ ] import idempotente
- [ ] 141/52/61/28 y agrupaciones consistentes
- [ ] cada rule tiene evidence o no puede pasar a verified
- [ ] unknowns preservados
- [ ] source hash verificado
- [ ] semantic diff estable
- [ ] curriculum-auditor sin Critical/High

## Revisión

- Ejecuta subagente `curriculum-auditor` y resuelve todos los Critical/High.
- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
