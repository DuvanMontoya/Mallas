# P07 — Contrato OpenAPI y cliente generado

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/16_API_CONTRACT.md`.
4. Lee `docs/30_API_AND_DATA_VERSIONING.md`.

## Skills obligatorias
- carga `api-change`
- carga `feature-delivery`

## Objetivo

Consolidar la API v1, schemas, errores y cliente TypeScript generado para eliminar duplicación manual de tipos.

## Entregables obligatorios

1. Definir routers por bounded context.
2. Definir Problem-like error envelope consistente.
3. Generar OpenAPI determinista.
4. Configurar openapi-typescript/openapi-fetch o alternativa verificada.
5. Crear `packages/api-client` generado y comando reproducible.
6. CI falla si OpenAPI/cliente están stale.
7. Pagination, filters y sort coherentes.
8. Optimistic concurrency para edición.
9. Idempotency keys donde aplica.
10. Documentar auth/CSRF para frontend.
11. Contract tests.

## Gates de aceptación

- [ ] no tipos API duplicados manualmente
- [ ] generated client reproducible
- [ ] breaking diff detectado
- [ ] errores consistentes
- [ ] auth documented
- [ ] verify incluye freshness

## Revisión

- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
