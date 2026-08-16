# 15 — Arquitectura frontend

## Next

App Router. Server Components por defecto.

Client Components únicamente para:
- React Flow;
- drag/drop;
- interacciones complejas;
- estado local rico.

## Data fetching

Servidor para páginas iniciales cuando sea adecuado.
Mutaciones mediante capa API tipada; no llamadas dispersas a `fetch`.

## Contrato

`packages/api-client` generado desde OpenAPI. No editar.

## State

Tres clases:
1. server state;
2. URL state;
3. UI ephemeral state.

No meter todo en un store global.

PlanScenario puede usar store local controlado con persistencia backend, pero sólo después de definir consistencia.

## URL

Filtros importantes y curso seleccionado pueden reflejarse en URL para compartir/deep-link sin exponer datos privados.

## Error handling

- route error boundaries;
- estados vacíos;
- retry donde sea seguro;
- mensajes accionables;
- correlation id para soporte.

## Performance

Virtualizar sólo si profiling lo requiere.
Lazy load del grafo pesado.
No hidratar todo el dashboard como cliente.
