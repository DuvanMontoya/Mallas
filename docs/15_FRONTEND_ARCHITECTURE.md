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
