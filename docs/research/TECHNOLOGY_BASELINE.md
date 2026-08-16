# Technology baseline — 2026-08-08

> Snapshot temporal. Revalidar antes de instalar.

## Backend

### Python
Objetivo: Python 3.14, sujeto a soporte oficial de las dependencias elegidas.

### Django
- La verificación del 2026-08-15 encontró Django 6.1 publicado en el índice de paquetes y documentación versionada.
- `django-ninja==1.6.2` declara `django>=3.1,<6.1`; `uv lock` rechazó la combinación Django 6.1 + Django Ninja.
- Resolución fijada: **Django 6.0.8** con Django Ninja 1.6.2, documentada en ADR-0011.
- Django 6.0 declara soporte para Python 3.14 en sus notas oficiales.

### API
Resolución fijada: Django Ninja 1.6.2. La prueba de compatibilidad con la versión final de Django resuelta pasó el solver y queda cubierta por los checks del backend.

## Frontend

### Next.js
La consulta del registro NPM del 2026-08-15 resolvió `next@latest` a **16.3.1**, con `dist-tags.latest=16.3.1` y una etiqueta canary separada; no se instala preview/canary. La documentación oficial disponible describe 16.3 como preview en publicaciones anteriores, por lo que el lockfile y el tag `latest` son la fuente operativa actual y se volverán a validar en upgrades.

### React Flow
Usar `@xyflow/react` estable resuelto por el lockfile de pnpm y comprobar su compatibilidad con Next/React durante cada build.

## gpt

gpt:
- model id: `gpt`;
- 1M de contexto;
- thinking/non-thinking;
- tool calls;
- JSON output;
- máximo documentado de salida 384K.

Aun con 1M, no usar el contexto como almacenamiento permanente. El repositorio es la memoria.

## codex

gpt recomienda codex >= 1.14.24 para integración. Mantener codex actualizado y revisar si la sintaxis de `codex.json` cambia entre generaciones.

Este kit incluye configuración V1 actual en `codex.json` y una guía de migración preventiva en `docs/research/codex_CONFIG_COMPATIBILITY.md`.

## Resolución local de bootstrap

- Python 3.14.7
- Node.js 24.19.0
- pnpm 11.21.0
- uv 0.11.19
- Django 6.0.8
- Django Ninja 1.6.2
- psycopg 3.3.4
- Pydantic 2.13.4
- Hypothesis 6.165.9
- OR-Tools 9.15.6755
- Ruff 0.16.3
- mypy 2.3.1
- Next.js 16.3.1
- React/React DOM 19.2.8

## PostgreSQL / OR-Tools

- PostgreSQL es la base transaccional elegida.
- OR-Tools CP-SAT resuelve planificación discreta; opera sobre enteros, lo cual coincide bien con créditos/semestres.

## Regla de oro

`latest stable verified > version guessed from model memory`.
