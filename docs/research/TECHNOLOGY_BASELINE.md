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

### Observabilidad

- `opentelemetry-sdk==1.44.0`;
- `opentelemetry-exporter-otlp-proto-http==1.44.0`.

La documentación oficial de OpenTelemetry Python consultada el 2026-08-16
describe `TracerProvider`/`MeterProvider` manuales y exportación OTLP hacia un
collector. La aplicación fija ambas versiones, usa exportación opt-in por
entorno y cubre la integración con checks de arranque, pruebas de redacción y
smoke; no instala instrumentación automática que pudiera capturar cuerpos o
atributos no aprobados.

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
- pypdf 6.16.1 (PDF text extraction adapter; OCR remains outside the authority boundary)
- Ruff 0.16.3
- mypy 2.3.1
- Next.js 16.3.1
- React/React DOM 19.2.8

### Imágenes de producción P24

Verificadas con `docker buildx imagetools inspect` el 2026-08-17 y fijadas en
los Dockerfiles/Compose:

- `python:3.14-slim@sha256:ce40764625a4ff50df3548277632e7f96c4e77fe75fa848aae9885476e7df5a4`;
- `node:24.19.0-alpine@sha256:d32cdf619f63fe0471182d08996dd516c6275bb5fd31ae06e55a570bd9e1ad43`;
- `ghcr.io/astral-sh/uv:0.11.19@sha256:b46b03ddfcfbf8f547af7e9eaefdf8a39c8cebcba7c98858d3162bd28cf536f6`;
- `postgres:18.0-alpine@sha256:48c8ad3a7284b82be4482a52076d47d879fd6fb084a1cbfccbd551f9331b0e40`;
- `caddy:2.10.2-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d`.

Los digests son índices multi-arquitectura; la release registra además el
digest final de cada imagen de aplicación publicado por el registry. No se
considera suficiente un tag mutable.

## PostgreSQL / OR-Tools

- PostgreSQL es la base transaccional elegida.
- OR-Tools CP-SAT resuelve planificación discreta; opera sobre enteros, lo cual coincide bien con créditos/semestres.

## Regla de oro

`latest stable verified > version guessed from model memory`.

## PDF candidate extraction

P06 fijó inicialmente `pypdf==6.10.0`. La auditoría de dependencias P23
identificó avisos de seguridad con correcciones publicadas en versiones
posteriores, por lo que la resolución se actualizó a **6.16.1** el
2026-08-17. La versión está publicada como estable en PyPI, declara soporte
para Python 3.14 y su wheel es `py3-none-any`; el lockfile contiene los hashes
resueltos por `uv`. Se usa únicamente para abrir PDFs y extraer texto
candidato; el resultado conserva página/lineage y requiere
preview/confirmación humana. La documentación oficial de pypdf advierte que la
extracción no es OCR y puede fallar en PDFs escaneados, por lo que una
extracción vacía o de baja confianza queda sin resolver en vez de convertirse
en historia académica.
