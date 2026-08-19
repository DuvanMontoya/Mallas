# Navegador Curricular UNAL

Plataforma de producción para navegación curricular, auditoría de grado, grafo de requisitos, oferta académica, planificación y optimización de trayectorias. La primera revisión implementa Estadística de la Universidad Nacional de Colombia, Sede Bogotá, plan 2514; el dominio está diseñado para admitir más instituciones, sedes, programas y revisiones sin reescribir el motor.

## Objetivo inicial

- Institución: Universidad Nacional de Colombia
- Sede: Bogotá
- Facultad: Ciencias
- Programa: Estadística
- Plan: 2514
- Norma base verificada: Acuerdo 496 de 2023 del Consejo de Facultad de Ciencias
- Créditos del plan: 141
- Duración estimada publicada: 9 semestres

## Estructura

- `apps/api`: backend Django modular, motor de dominio y contrato OpenAPI.
- `apps/web`: frontend Next.js App Router.
- `packages/api-client`: cliente TypeScript generado desde OpenAPI.
- `data`, `schemas`, `sources`: datos versionados, esquemas y evidencia normativa.
- `scripts`: verificadores, exportadores y herramientas operativas.
- `infra`: Compose y Dockerfiles reproducibles.
- `docs`, `prompts`: especificación, decisiones, roadmap y milestones obligatorios.

## Requisitos

- Python 3.14.x
- Node.js 24.19.x y pnpm 11.21.x
- uv 0.11.19
- Docker Engine/Compose para PostgreSQL local y los servicios completos

Las versiones se fijan en `.python-version`, `.nvmrc`, `apps/api/pyproject.toml`, `apps/api/uv.lock` y `pnpm-lock.yaml`.

## Bootstrap local

1. Instale las versiones indicadas y copie `.env.example` a `.env` si necesita personalizar la configuración.

2. Instale dependencias:

```bash
uv sync --project apps/api
pnpm install --frozen-lockfile
```

3. Levante PostgreSQL y prepare la base local:

```bash
docker compose -f infra/docker-compose.yml up -d postgres
uv run --project apps/api python apps/api/manage.py migrate
```

Sin Docker, el backend usa SQLite local para desarrollo y pruebas:

```bash
uv run --project apps/api python apps/api/manage.py migrate
```

4. Cree el administrador local de primer uso (no hay credenciales compartidas ni
incluidas en Git):

```bash
uv run --project apps/api python apps/api/manage.py bootstrap_local_admin
cat var/local-admin-credentials.txt
```

El comando genera una contraseña aleatoria, crea `admin@localhost` como
superusuario y guarda las credenciales sólo en
`var/local-admin-credentials.txt` (permisos `0600`, ruta ignorada por Git).
Úsalas en `http://localhost:8000/admin/` o con el formulario de
`http://localhost:3000/login`. Si necesitas regenerarla durante desarrollo:

```bash
uv run --project apps/api python apps/api/manage.py bootstrap_local_admin --reset-password
```

El comando sólo funciona con `DJANGO_DEBUG=true`; no es un mecanismo de alta
de cuentas para producción.

5. Ejecute el backend y el frontend en terminales separadas:

```bash
uv run --project apps/api python apps/api/manage.py runserver 127.0.0.1:8000
pnpm --dir apps/web dev
```

La API publica health checks en `/api/v1/health/live` y `/api/v1/health/ready`, y OpenAPI en `/api/v1/openapi.json`.

## Verificación

La verificación canónica ejecuta invariantes de currículo, frescura de OpenAPI,
frescura exacta del cliente generado, checks y tests Django, Ruff, mypy, lint,
typecheck y tests unitarios del frontend:

```bash
python scripts/verify.py
pnpm --dir apps/web build
pnpm --dir apps/web e2e
```

Para regenerar y comprobar el cliente TypeScript:

```bash
python scripts/export_openapi.py
pnpm --dir packages/api-client generate
pnpm run verify:api
```

Para auditar compatibilidad con una revisión base de Git:

```bash
python scripts/check_openapi_breaking.py --base-revision <git-base-sha>
```

Para ejecutar todo el stack local:

```bash
docker compose -f infra/docker-compose.yml up --build
```

El servicio web queda en `http://localhost:3000` y la API en `http://localhost:8000`.

## Regla central

La memoria permanente del proyecto es el repositorio, no el contexto de la conversación del modelo. Las revisiones curriculares publicadas son inmutables; toda regla publicada debe conservar evidencia y estado epistemológico.

La autoridad se ordena así:

1. normas oficiales y evidencia,
2. datos publicados y versionados,
3. código + migraciones,
4. tests y verificadores,
5. documentación/ADRs,
6. estado del roadmap,
7. conversación del agente.

Antes de cambios estructurales, lea `AGENTS.md`, `docs/state/CURRENT_STATE.md`, `docs/state/ROADMAP_STATUS.json`, `docs/state/OPEN_DECISIONS.md` y la especificación del área correspondiente.

Si una conversación contradice una fuente oficial o un test de invariantes, la conversación pierde.
