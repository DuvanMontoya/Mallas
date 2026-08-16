# P12 — Oferta, secciones y horarios

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/10_OFFERINGS_AND_SCHEDULES.md`.
4. Lee `docs/31_CURRICULUM_2514_BASELINE.md`.

## Skills obligatorias
- carga `feature-delivery`
- carga `source-research`
- carga `api-change`

## Objetivo

Implementar oferta temporal separada del currículo, con fuentes, freshness, grupos, reuniones y conflictos.

## Entregables obligatorios

1. AcademicTerm CRUD/admin.
2. Offering/Section/Meeting APIs.
3. Importer/adaptador de oferta con SourceSnapshot/freshness.
4. Investigar fuentes públicas oficiales disponibles sin depender de scraping privado.
5. Distinguir offered/eligible/schedulable.
6. Conflict detection exacto.
7. UI de oferta por período.
8. ScheduleGrid.
9. Freshness badges.
10. No afirmar cupo real-time si no existe dato.
11. Adapter interface para futuras fuentes.

## Gates de aceptación

- [ ] cambiar oferta no crea nueva curriculum revision
- [ ] elegible puede ser no ofertada
- [ ] ofertada puede ser bloqueada
- [ ] conflictos correctos
- [ ] source timestamp visible
- [ ] sin scraping autenticado no autorizado

## Revisión

- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `ux-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `security-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
