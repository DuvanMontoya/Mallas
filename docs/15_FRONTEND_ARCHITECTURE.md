# 15 — Arquitectura frontend

## Next

App Router. Server Components por defecto.

Client Components únicamente para:
- React Flow;
- drag/drop;
- interacciones complejas;
- estado local rico.

## Data fetching

El layout raíz es Server Component dinámico y obtiene la sesión mediante
`apps/web/lib/api.ts`, que usa exclusivamente `@curriculum-navigator/api-client`
generado. El servidor reenvía la cookie de sesión al backend; en navegador el
cliente usa `credentials: include`.

Mutaciones y lecturas de dominio pasan por la misma capa tipada (`getSessionSnapshot`,
`getCsrfToken`, `signIn`, `signOut` y los servicios que se agreguen después). No
se permiten llamadas dispersas a `fetch`, URLs API ni DTOs escritos a mano en
componentes.

El dashboard y `/audit` consumen `getAcademicOverview`, que devuelve el
read model tipado de auditoría. El componente `AcademicDashboard` sólo mapea
estados backend a etiquetas/tokens y presenta las razones/evidencias; no suma
créditos, resuelve requisitos, decide elegibilidad ni convierte un 100% de
créditos en graduación.

`/curriculum` y `/curriculum/print` consumen `getCurriculumMap`, también
generado desde OpenAPI. `CurriculumMapPage` puede controlar filtros, layout,
selección y preferencias de impresión, pero presenta `personal_status`,
`offering_state`, requisitos, AST y evidencia tal como los entrega el backend.
La selección contextual es una proyección visual de dependencias directas y no
una segunda implementación del motor. Los layouts de ruta sugerida y escenario
personal muestran un estado explícito de ausencia hasta que sus bounded
contexts publiquen un escenario real.

## Contrato

`packages/api-client` generado desde OpenAPI. No editar.

## State

Tres clases:
1. server state;
2. URL state;
3. UI ephemeral state.

No meter todo en un store global.

El shell conserva sólo estado efímero de UI (menú móvil, popovers, tema y
feedback de logout). La sesión es server state. El hook
`apps/web/lib/use-workspace-url-state.ts` implementa el patrón común para
`q`, `view` y `selected` con `router.replace(..., { scroll: false })`.

PlanScenario puede usar store local controlado con persistencia backend, pero sólo después de definir consistencia.

## URL

Filtros importantes y curso seleccionado pueden reflejarse en URL para
compartir/deep-link sin exponer datos privados. `safeInternalPath` rechaza
destinos externos para evitar open redirects en el parámetro `next` del login.

## Error handling

- route error boundaries;
- estados vacíos;
- retry donde sea seguro;
- mensajes accionables;
- correlation id para soporte.

`app/loading.tsx`, `app/error.tsx` y `app/not-found.tsx` cubren los estados de
route-level. Las respuestas `ProblemDetails` del backend conservan `code` y
`correlation_id`; la UI muestra un mensaje accionable sin exponer stack traces.

## Performance

Virtualizar sólo si profiling lo requiere.
Lazy load del grafo pesado.
No hidratar todo el dashboard como cliente.

El dashboard y las páginas de módulo son Server Components; únicamente el
shell, tema, login y controles de interacción son Client Components.

## Grafo de dependencias

`app/graph/page.tsx` obtiene el read model desde el servidor y reenvía la
cookie; `components/dependency-graph-shell.tsx` carga de forma diferida el
explorador cliente. El canvas importa React Flow y ELK sólo en ese límite y
deshabilita conexión/arrastre para que nunca se interprete como editor de
reglas. La proyección conserva nodos de condición y la misma información se
ofrece en una lista textual para lectores de pantalla, móvil y fallos de
renderizado visual.

El cliente puede filtrar por texto, componente, tipo y estado, pero no evalúa
AST, elegibilidad, graduación ni cierres transitivos. El backend entrega
relaciones directas, cierres, rutas, warnings, ciclos y links de evidencia.

## Offerings feature

`app/offerings/page.tsx` es un Server Component dinámico. Obtiene el término,
los filtros de búsqueda y los identificadores opcionales de inscripción/grupos
desde el estado de URL, llama `getOfferings` y `getOfferingSchedule` mediante el
cliente generado, y pasa los read models a
`components/offerings-explorer.tsx`. El Client Component sólo controla filtros,
selección de grupos y navegación de URL: no evalúa elegibilidad, infiere
capacidad ni detecta conflictos localmente.

La feature presenta por separado oferta/elegibilidad/agenda, timestamp y
frescura de fuente, enlaces, advertencia de cupo desconocido, reuniones y
conflictos exactos. SIA se trata como referencia de fuente; el navegador nunca
envía una inscripción ni usa scraping autenticado. La URL permite compartir
selecciones públicas de período/curso/grupo, mientras el contexto de
inscripción sigue sujeto a autorización del backend.

## Planner feature

`app/planner/page.tsx` es un Server Component dinámico: obtiene escenarios,
períodos y cursos de la malla mediante la capa tipada, conserva cookies y
prepara el escenario seleccionado y la comparación. `components/planner-board`
es el único límite cliente porque contiene drag/drop, selectores, locks,
formularios y estado efímero de feedback. No implementa reglas académicas ni
edita la historia.

Las funciones `getScenarios`, `createScenario`, `updateScenario`,
`addPlannedCourse`, `updatePlannedCourse`, `deletePlannedCourse`,
`duplicateScenario`, `archiveScenario` y `getScenarioCompare` viven en
`apps/web/lib/api.ts` y se validan contra `artifacts/openapi.json`. El
navegador usa el BFF `app/api/v1/[...path]/route.ts` cuando no se configura
`NEXT_PUBLIC_API_URL`; éste reenvía cookies, CSRF, `If-Match` y la respuesta
problem al API interno.

`components/optimizer-panel.tsx` es una extensión cliente del mismo límite:
inicia una ejecución mediante `startOptimization`, consulta estados
`QUEUED`/`RUNNING` hasta su terminación y permite solicitar cancelación. Sólo
presenta el resultado tipado por OpenAPI: estado, hashes, versión, diferencias
contra los cursos actuales, explicaciones, conflictos y supuestos. No importa
el motor Python, no interpreta el AST y no aplica automáticamente la solución
al escenario. Las funciones `startOptimization`, `getOptimizationRun` y
`cancelOptimizationRun` son la única puerta de acceso del navegador a esos
recursos.
