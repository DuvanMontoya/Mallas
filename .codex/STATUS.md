# Estado de ejecución de milestones

Este archivo es el registro operativo de la ejecución lexicográfica de `prompts/*.md`.
Un milestone sólo aparece como `done` después de ejecutar sus verificaciones y resolver los fallos reproducibles.

## P00 — Toolchain & repository bootstrap

Estado: `done`

### Implementación realizada

- Resolví y fijé Python 3.14.7, Node.js 24.19.0, pnpm 11.21.0, uv 0.11.19, Django 6.0.8, Django Ninja 1.6.2 y Next.js 16.3.1.
- Registré la incompatibilidad Django 6.1/Django Ninja y la decisión en ADR-0011 y `docs/research/TECHNOLOGY_BASELINE.md`.
- Creé el backend Django modular en `apps/api`, con usuario por correo, migración inicial, configuración segura de desarrollo, health live/readiness y OpenAPI.
- Creé el frontend Next.js App Router en `apps/web`, TypeScript strict, lint, Vitest, Playwright, build standalone y rutas de base para los dominios del producto.
- Creé `packages/api-client` con cliente TypeScript generado desde el contrato OpenAPI y verificación de frescura.
- Creé Compose canónico con PostgreSQL 18.0-alpine, healthcheck, volumen persistente y Dockerfiles no-root para API/web.
- Fijé lockfiles, archivos de versión, workspace pnpm, `pyproject.toml`, Renovate, CI inicial y `scripts/verify.py` como orquestador canónico.
- Actualicé README, documentación de infraestructura y estado permanente. Se inicializó el repositorio Git existente sin crear commit ni modificar historial.

### Pruebas ejecutadas

- `python scripts/verify.py`
- `pnpm --dir apps/web build`
- `pnpm --dir apps/web e2e` (2 proyectos: desktop y mobile)
- `uv run --project apps/api python apps/api/manage.py check`
- `uv run --project apps/api python apps/api/manage.py makemigrations --check --dry-run`
- `uv run --project apps/api python apps/api/manage.py migrate --check`
- `DATABASE_URL=postgresql://... uv run --project apps/api python apps/api/manage.py migrate --noinput`
- `docker compose -f infra/docker-compose.yml config`
- Arranque real de Next standalone y GET `/` (HTTP 200, contenido esperado)
- Arranque real de Django con PostgreSQL y GET `/api/v1/health/live`, `/api/v1/health/ready`, `/api/v1/openapi.json` (HTTP 200)

### Resultados

- Invariantes curriculares: PASS (`courses=102`, `memberships=97`, `requirements=73`).
- OpenAPI fresco: PASS.
- Django checks: PASS; migraciones en SQLite y PostgreSQL: PASS.
- Backend: 3 tests PASS, Ruff PASS, formato PASS, mypy PASS.
- Frontend: lint PASS, typecheck PASS, 1 archivo/1 test unitario PASS, build PASS.
- E2E: 2/2 PASS en desktop y mobile.
- PostgreSQL Compose: contenedor `infra-postgres-1` healthy y conexión de Django verificada.
- Revisión estática de P00: sin TODO/FIXME/stub en el código nuevo de producto. Los reviewers especializados no están disponibles como herramientas en este entorno; se realizó revisión manual de arquitectura/código y se dejó la limitación documentada.

### Problemas pendientes

- P00 no deja problemas funcionales pendientes. El catálogo completo y las reglas de dominio se implementarán en los milestones posteriores; no se inventó lógica académica en este scaffold.
- No se creó un commit Git porque AGENTS.md requiere autorización para commits automáticos.

### Siguiente

Ejecutar estrictamente `prompts/02_DOMAIN_AND_BACKEND_FOUNDATION.md` como P01, comenzando por el dominio puro y sus invariantes.

