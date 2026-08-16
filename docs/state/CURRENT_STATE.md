# Current State

## Snapshot

P00 (`Toolchain & repository bootstrap`) está terminado y verificado. El repositorio ya tiene backend Django modular, frontend Next.js, cliente TypeScript generado, Compose de PostgreSQL y verificaciones ejecutables. El dominio académico completo todavía se construirá en P01–P26.

## Terminado en P00

- Toolchain fijado: Python 3.14.7, Node 24.19.0, pnpm 11.21.0, uv 0.11.19.
- Stack fijado: Django 6.0.8 + Django Ninja 1.6.2, Next 16.3.1 + React 19.2.8, PostgreSQL 18.0-alpine.
- ADR-0011 registra la decisión Django 6.0 por incompatibilidad declarada de Django Ninja 1.6.2 con Django 6.1.
- `apps/api` ejecuta checks, health live/readiness, OpenAPI, migraciones y tests; `identity.User` tiene migración inicial.
- `apps/web` compila a standalone, arranca y tiene rutas de base para curriculum, audit, graph, planner, offerings, history, sources.
- `packages/api-client` se genera desde `artifacts/openapi.json` y tiene verificación de frescura.
- `infra/docker-compose.yml` fue validado, PostgreSQL arrancó healthy y Django conectó y migró contra esa instancia.
- `scripts/verify.py` ejecuta invariantes, API, Ruff, mypy, lint, typecheck y Vitest.
- Playwright Chromium fue instalado en el entorno y el smoke E2E pasó en desktop y mobile.

## Verificaciones que pasaron

```text
python scripts/verify.py                         PASS
pnpm --dir apps/web build                        PASS
pnpm --dir apps/web e2e                          PASS (2/2)
manage.py check                                  PASS
makemigrations --check --dry-run                 PASS
migrate --check                                  PASS
PostgreSQL Compose + migrate + health endpoints  PASS
```

## Problemas y riesgos conocidos

- No se creó un commit nuevo: AGENTS.md exige autorización explícita para commits automáticos. El repositorio ya contiene un commit inicial.
- Los reviewers `architecture-reviewer` y `code-reviewer` exigidos por los prompts no están expuestos como herramientas instaladas en esta sesión; la revisión de P00 fue manual y de solo lectura.
- El backend usa SQLite por defecto sólo como fallback de desarrollo/tests; el objetivo transaccional sigue siendo PostgreSQL y ya fue probado.
- No hay `docs/SPEC.md` ni `docs/REQUIREMENTS.md` en el kit original; la revisión final deberá usar los documentos normativos existentes y registrar explícitamente esta ausencia.

## Siguiente acción exacta

Leer de nuevo y ejecutar completamente `prompts/02_DOMAIN_AND_BACKEND_FOUNDATION.md` (P01): crear el dominio puro, value objects, entidades versionadas e invariantes sin depender del ORM.

## Comandos para reanudar

```bash
docker compose -f infra/docker-compose.yml up -d postgres
python scripts/verify.py
pnpm --dir apps/web build
pnpm --dir apps/web e2e
```
