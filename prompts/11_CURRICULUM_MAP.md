# P10 — Malla curricular interactiva

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/12_UX_INFORMATION_ARCHITECTURE.md`.
4. Lee `docs/13_DESIGN_SYSTEM.md`.
4. Lee `data/layouts/plan_2514_layout_policy.json`.

## Skills obligatorias
- carga `feature-delivery`

## Objetivo

Construir malla moderna, intuitiva y limpia que distinga plan oficial, layout no normativo y escenario personal.

## Entregables obligatorios

1. CurriculumGrid con layouts intercambiables.
2. Layout dependency-depth sin llamarlo semestre.
3. Vista por componentes/agrupaciones.
4. Estado individual por CourseCard.
5. Filtros por component/group/status/credits/offering.
6. Selección contextual que resalta sólo dependencias relevantes.
7. Panel curso completo.
8. Leyenda accesible.
9. Mobile roadmap vertical.
10. Print/export view.
11. Persistencia de preferencias de vista.
12. No afirmar una malla semestral oficial inexistente.

## Gates de aceptación

- [ ] sin spaghetti de flechas en vista principal
- [ ] ningún layout no oficial rotulado como oficial
- [ ] CourseCard incluye contexto esencial
- [ ] keyboard/focus
- [ ] mobile real
- [ ] performance aceptable

## Revisión

- Ejecuta subagente `ux-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `curriculum-auditor` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
