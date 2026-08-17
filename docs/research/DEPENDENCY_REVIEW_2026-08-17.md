# P91 — Revisión segura de dependencias

**Fecha:** 2026-08-17  
**Resultado:** `BLOCKED_EXTERNAL` para completar el cierre del upgrade frontend; no se ejecutó una actualización ciega ni se dejó un lockfile inconsistente.

## Inventario resuelto

El inventario se obtuvo de los manifiestos y lockfiles locales mediante
`scripts/update_technology_baseline.py --check`.

| Área | Versión actualmente fijada | Evidencia local | Decisión |
|---|---:|---|---|
| Python | 3.14 (`>=3.14,<3.15`) | `apps/api/pyproject.toml`, `apps/api/uv.lock`, `.python-version`/CI | Mantener; resolver/verificar con Python 3.14 accesible |
| Django | 6.0.8 | `apps/api/pyproject.toml`, `apps/api/uv.lock` | Mantener; es la línea estable fijada y tiene release notes oficiales de 2026-08-04 |
| Django Ninja | 1.6.2 | manifiesto + lockfile | Mantener; no hay motivo comprobado para un cambio mayor |
| Pydantic | 2.13.4 | manifiesto + lockfile | Mantener |
| psycopg | 3.3.4 | manifiesto + lockfile | Mantener |
| OR-Tools | 9.15.6755 | manifiesto + lockfile | Mantener; requiere suite del motor después de cualquier cambio |
| pypdf | 6.16.1 | manifiesto + lockfile | Ya actualizado y verificado en P23 contra PyPI/changelog oficial |
| React / React DOM | 19.2.8 | `apps/web/package.json`, `pnpm-lock.yaml` | Mantener; la documentación oficial identifica 19.2 como línea actual |
| Next.js | 16.3.1 | `apps/web/package.json`, `pnpm-lock.yaml` | **Hallazgo:** la versión fijada no es la línea estable observada; requiere downgrade controlado |
| `eslint-config-next` | 16.3.1 | manifiesto + lockfile | Debe acompañar exactamente a Next.js en el downgrade |
| Node.js | 24.19.0 | `.nvmrc`, `package.json`, CI, Dockerfile | Mantener; no actualizar sin compatibilidad de Next/Playwright |
| pnpm | 11.21.0 | `package.json`, CI | Mantener; lockfile v9 se genera con esa versión |
| TypeScript | 6.0.3 | `apps/web/package.json`, lockfile | Mantener |

## Evidencia oficial consultada

- Las [notas oficiales de Django 6.0.8](https://docs.djangoproject.com/en/6.0/releases/6.0.8/) indican la publicación del 4 de agosto de 2026 con correcciones de seguridad y bugs; no hay una razón para salir de 6.0.8 durante este milestone.
- La [documentación oficial de Django 6.0](https://docs.djangoproject.com/en/6.0/releases/6.0/) confirma compatibilidad con Python 3.14 y enumera cambios incompatibles; el repositorio ya fija esa combinación.
- La [documentación de versiones de React](https://react.dev/versions) identifica React 19.2 como versión documentada actual; las [notas de React 19.2](https://react.dev/blog/2025/10/01/react-19-2) fueron revisadas.
- El anuncio oficial de [Next.js 16.2](https://nextjs.org/blog/next-16-2) describe la línea estable de producción revisada. El [blog oficial de Next.js](https://nextjs.org/blog) describe 16.3 como preview en las publicaciones consultadas, y el [registro de versiones de npm](https://www.npmjs.com/package/next?activeTab=versions) muestra `16.2.12` con tag `latest` y `16.3.0-preview`/`canary` en tags separados.
- El [aviso oficial de seguridad de Next.js](https://github.com/vercel/next.js/security/advisories/GHSA-89xv-2m56-2m9x) fija como parche mínimo de la rama 16 `16.2.11`; la versión estable disponible observada es `16.2.12`.
- La ficha oficial de [pypdf 6.16.1 en PyPI](https://pypi.org/project/pypdf/6.16.1/) y su [changelog oficial](https://pypdf.readthedocs.io/en/latest/meta/CHANGELOG.html) respaldan la actualización ya aplicada en P23.

## Hallazgo y decisión sobre Next.js

El repositorio declara `next==16.3.1` y `eslint-config-next==16.3.1`, pero las fuentes oficiales consultadas durante este milestone muestran `16.2.12` como `latest` estable y `16.3.0-preview`/`canary` como canales previos. Para el producto de producción, la decisión correcta es migrar ambas dependencias a `16.2.12` y regenerar el lockfile con pnpm 11.21.0. No se cambia sólo `package.json`: el lockfile debe ser generado por pnpm para obtener las integridades y los binarios opcionales `@next/swc-*` correctos.

No se ejecutó esa mutación porque el entorno no puede resolver el registro npm: `pnpm view next@16.2.12 version --json` terminó con `ERR_PNPM_META_FETCH_FAIL` después de no poder conectar a `registry.npmjs.org`; además, los comandos de frontend fallan con `EPERM` al abrir entradas existentes de `node_modules`. Editar manualmente `pnpm-lock.yaml` sin los metadatos oficiales y sin reinstalar sería una falsificación de reproducibilidad y dejaría la instalación congelada sin verificación.

## Pruebas y gates ejecutados

- Inventario y consistencia narrativa: **PASS** (`scripts/update_technology_baseline.py --check`).
- Validación de JSON de `package.json`: **PASS** mediante el parser del gestor/inspección local.
- `pnpm install --lockfile-only --ignore-scripts` con el estado actual: **BLOQUEADO** por red (`ERR_PNPM_META_FETCH_FAIL`); no cambió el lockfile.
- `pnpm audit --prod --audit-level high`: resultado histórico de P23 **PASS**; no se pudo repetir en esta ejecución por la misma restricción de red.
- Lint, typecheck, Vitest y build frontend: resultados históricos de P22/P23 **PASS**; en esta ejecución el acceso a `node_modules` da **EPERM**, por lo que no se sobredeclaran como actuales.
- Codemod dry-run: **NO APLICA** a un downgrade patch de Next sin APIs 16.3 específicas; se inspeccionó el código y no hay uso de APIs preview de 16.3. El codemod de upgrade no se ejecuta a ciegas.
- OpenAPI backend: no cambia; el comparador de contrato local pasa.

## Cierre requerido para P91

En un runner con salida al registro npm y filesystem de dependencias accesible:

```powershell
pnpm add --filter @curriculum-navigator/web next@16.2.12
pnpm add --filter @curriculum-navigator/web --save-dev eslint-config-next@16.2.12
pnpm install --frozen-lockfile --ignore-scripts
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web build
pnpm --dir apps/web e2e
```

Después se debe actualizar `docs/research/TECHNOLOGY_BASELINE.md`, ejecutar el
comparador OpenAPI y la suite canónica, y sólo entonces cerrar el hallazgo.
Mientras esto no ocurra, el estado es `BLOCKED_EXTERNAL`, no `done`.
