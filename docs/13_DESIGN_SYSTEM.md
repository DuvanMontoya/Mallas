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
`CourseCard` puede exponer una acción de selección accesible (`button`,
`aria-pressed`, focus visible y estado contextual) sin dejar de ser
presentacional. `CurriculumGrid` sólo aporta la región semántica de la malla;
la página de dominio decide el layout, los filtros y el panel de ficha. La
malla combina texto, icono, borde y patrón para los estados seleccionados,
relacionados y atenuados; nunca depende sólo del color.

Storybook se mantiene fuera del alcance hasta que haya suficiente variación
visual; por ahora los componentes críticos tienen tests de Testing Library y
axe, además de una ruta de shell real para revisión manual.

## Motion

Sólo para orientación espacial; respetar `prefers-reduced-motion`.

## Grafo semántico

`DependencyGraph` distingue visual y textualmente cursos de condiciones. Los
nodos de condición usan una forma y borde alternativos, pero cada relación
también tiene etiqueta; ningún estado o tipo depende sólo del color. `GraphLegend`,
`FocusPanel` y `TextualAlternative` exponen relaciones directas, rutas
transitivas, estados y acciones de teclado. El canvas está pensado para
exploración: no conecta ni arrastra nodos, y la lista textual permanece como
superficie equivalente.

## Oferta y horarios

`OfferingBadge` distingue `OFFERED`, `NOT_OFFERED`, `ELIGIBLE`, `BLOCKED` y
`UNKNOWN` con texto y un tratamiento redundante de borde/forma. La frescura de
la fuente se presenta como `Fuente fresca`, `Fuente antigua` o `Fuente
desconocida`; no se usa un color aislado para expresar actualidad. `ScheduleGrid`
usa encabezados de día, horas y filas de grupo, mantiene foco visible y se
refluye horizontalmente en pantallas pequeñas. Los conflictos se anuncian con
texto y una lista de ocurrencias, y la capacidad no real-time incluye una
 advertencia explícita.

## Planner

Las columnas de `PlannerTermColumn` se convierten en una lista vertical en
móvil. Las tarjetas de escenario usan `GripVertical` sólo como affordance
redundante: cada una conserva un selector de término, botones con nombre
accesible para bloquear/desbloquear y retirar, y un estado de foco visible.
`planner-drop-over` comunica el destino durante drag/drop, pero el cambio se
confirma por la misma operación tipada del backend. Warnings, estados de
oferta y auditoría proyectada combinan badge con texto y nunca usan únicamente
color.
