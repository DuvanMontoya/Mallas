# 13 — Design system

## Objetivo visual

Moderno, sobrio, científico, limpio. No gamificación infantil. La densidad se maneja mediante progressive disclosure.

## Tokens

Los tokens viven en `apps/web/app/globals.css` y se consumen por nombre
semántico, no por valores de color dentro de los componentes:

- superficies: `--surface-canvas`, `--surface-0`, `--surface-1`,
  `--surface-inverse`, `--surface-accent`;
- texto/bordes: `--text-strong`, `--text-body`, `--text-muted`,
  `--text-inverse`, `--border-default`, `--border-strong`;
- estados: `--status-passed`, `--status-in-progress`, `--status-eligible`,
  `--status-blocked`, `--status-unknown`;
- componentes curriculares: `--component-foundation`,
  `--component-disciplinary`, `--component-free-elective`.

`data-theme="light|dark"` cambia el conjunto completo de tokens. Los estados
siempre combinan color con texto, icono, borde o patrón; ningún estado depende
únicamente del color.

Tema claro y oscuro si no compromete legibilidad.

## Componentes obligatorios

- CourseCard
- CourseStatusBadge
- RequirementChip
- ProgressMeter
- CreditLedger
- ComponentProgressCard
- GroupProgressTable
- EvidencePopover
- RequirementExplanation
- CurriculumGrid
- DependencyGraph
- GraphLegend
- PlannerTermColumn
- ScenarioCompare
- OfferingBadge
- ScheduleGrid
- AuditWarning
- UnknownState
- SourceViewer
- SemanticDiff

La implementación presentacional y neutral al dominio está en
`apps/web/components/ui/foundation.tsx` y se exporta desde `components/ui`.
Los componentes reciben hechos y estados ya resueltos; no calculan elegibilidad,
graduación ni reglas curriculares. La página de dominio decide qué datos pasarles.

Storybook se mantiene fuera del alcance hasta que haya suficiente variación
visual; por ahora los componentes críticos tienen tests de Testing Library y
axe, además de una ruta de shell real para revisión manual.

## Motion

Sólo para orientación espacial; respetar `prefers-reduced-motion`.
