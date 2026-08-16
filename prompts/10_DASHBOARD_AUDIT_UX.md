# P09 — Dashboard y auditoría visual

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/06_DEGREE_AUDIT_SPEC.md`.
4. Lee `docs/12_UX_INFORMATION_ARCHITECTURE.md`.
4. Lee `docs/24_BUSINESS_LOGIC_MATRIX.md`.

## Skills obligatorias
- carga `feature-delivery`
- carga `api-change`

## Objetivo

Entregar la experiencia central que explica el avance real por créditos, componentes, agrupaciones, obligatorias y requisitos.

## Entregables obligatorios

1. Endpoint/read model `academic-overview` optimizado.
2. Dashboard con required/earned/applied/unapplied.
3. Progreso por componente y agrupación.
4. Obligatorias faltantes.
5. External graduation requirements.
6. Warnings/UNKNOWN visibles.
7. RequirementExplanation con evidencia.
8. Panel 'qué puedo cursar' basado en backend.
9. Next unlocks.
10. Deep links a cursos/requisitos.
11. Estados sin historia/incompleta.
12. E2E con estudiante fixture.

## Gates de aceptación

- [ ] no mostrar 100% sólo porque créditos total >=141 si faltan requisitos
- [ ] UNKNOWN visible
- [ ] evidence accesible
- [ ] UI no recalcula audit
- [ ] responsive y keyboard
- [ ] E2E principal verde

## Revisión

- Ejecuta subagente `ux-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `curriculum-auditor` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
