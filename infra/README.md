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

## Producción objetivo
- TLS/reverse proxy;
- web Next.js;
- API Django;
- workers si el job adapter de producción los requiere;
- PostgreSQL con backups;
- object storage para fuentes/artefactos si se necesita;
- OpenTelemetry;
- health/readiness;
- secretos fuera de Git.

Antes de un despliegue, ejecute las migraciones, health checks, pruebas de restore y el checklist de `docs/24_DEPLOYMENT_AND_DR.md`.

No desplegar automáticamente desde este kit sin completar P24.
