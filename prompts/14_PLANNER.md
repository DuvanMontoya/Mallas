# P13 — Planificador de escenarios

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/11_PLANNER_OPTIMIZER.md`.
4. Lee `docs/10_OFFERINGS_AND_SCHEDULES.md`.
4. Lee `docs/12_UX_INFORMATION_ARCHITECTURE.md`.

## Skills obligatorias
- carga `feature-delivery`
- carga `api-change`

## Objetivo

Construir escenarios persistentes completos con drag/drop accesible, validación incremental y comparación.

## Entregables obligatorios

1. PlanScenario versionado con ownership.
2. PlannedCourse por término.
3. Preferencias: límites créditos, disponibilidad, prioridades.
4. Drag/drop con alternativa de teclado/buttons.
5. Validación prerequisites/corequisites entre términos.
6. Warnings de oferta/conflicto/UNKNOWN.
7. Lock choices del usuario.
8. Duplicar/renombrar/archivar escenarios.
9. Compare scenarios.
10. Share view sin datos privados por defecto.
11. Recompute audit projected para cada escenario.

## Gates de aceptación

- [ ] mover curso no altera historia real
- [ ] prerequisitos respetan ordering
- [ ] corequisitos permiten same term según rule
- [ ] escenarios privados por defecto
- [ ] drag/drop tiene alternativa accesible
- [ ] compare claro

## Revisión

- Ejecuta subagente `ux-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
