# 13 — Design system

## Objetivo visual

Moderno, sobrio, científico, limpio. No gamificación infantil. La densidad se maneja mediante progressive disclosure.

## Tokens

Definir semánticos, no colores hardcoded:
- `surface-*`
- `text-*`
- `border-*`
- `status-passed`
- `status-in-progress`
- `status-eligible`
- `status-blocked`
- `status-unknown`
- `component-foundation`
- `component-disciplinary`
- `component-free-elective`

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

Storybook se evalúa según costo/beneficio; si se adopta, probar componentes críticos visualmente.

## Motion

Sólo para orientación espacial; respetar `prefers-reduced-motion`.
