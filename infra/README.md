# Infraestructura

Este directorio contiene una base reproducible, no una decisión irrevocable sobre proveedor cloud.

## Local

`docker-compose.yml` es el Compose canónico de desarrollo. Levanta PostgreSQL 18 con volumen persistente y health check:

```bash
docker compose -f infra/docker-compose.yml up -d postgres
docker compose -f infra/docker-compose.yml ps
```

`docker-compose.bootstrap.yml` se conserva como compatibilidad histórica del kit; no es el archivo de referencia para la aplicación.

El stack completo se construye con:

```bash
docker compose -f infra/docker-compose.yml up --build
```

La configuración usa variables `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_PORT`; los valores incluidos son sólo para desarrollo local.

## Referencia de producción

`docker-compose.production.yml` contiene API Django, web Next.js, PostgreSQL
no publicado y Caddy como reverse proxy/TLS. Las imágenes de API/web y las
imágenes base están fijadas por digest; los contenedores de aplicación son no
root, read-only salvo el volumen privado explícito y tienen healthchecks.

```bash
cp infra/production.env.example infra/production.env
# sustituir cada placeholder desde el secret manager; no guardar el archivo
python3 scripts/production_preflight.py --env-file infra/production.env
docker compose --env-file infra/production.env -f infra/docker-compose.production.yml config
docker compose --env-file infra/production.env -f infra/docker-compose.production.yml --profile migration run --rm migrate
docker compose --env-file infra/production.env -f infra/docker-compose.production.yml up -d
```

La guía completa es `docs/ops/DEPLOYMENT_RUNBOOK.md`. Backups y restore drills
están en `docs/ops/BACKUP_RESTORE_RUNBOOK.md`; el object storage separado en
`docs/ops/OBJECT_STORAGE_STRATEGY.md`; rollback en
`docs/ops/ROLLBACK_RUNBOOK.md`. El archivo local de desarrollo sigue usando
credenciales de ejemplo y nunca es una configuración institucional.
