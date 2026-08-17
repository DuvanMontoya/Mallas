# 21 — Despliegue, backups y recuperación

## Topología inicial de producción

Puede desplegarse en un VPS robusto con:
- reverse proxy;
- Next Node process;
- Django ASGI/WSGI según necesidades verificadas;
- PostgreSQL;
- object storage externo o compatible S3;
- worker sólo cuando el job backend sea elegido;
- observabilidad.

Monolito modular no significa un solo proceso.

## Docker

Imágenes reproducibles, non-root, healthchecks, multi-stage.

## DB

- migraciones forward;
- backup antes de cambios riesgosos;
- PITR si la criticidad lo justifica;
- restore drill periódico.

## Backups

Una copia no es backup hasta que se restaura.

Definir:
- RPO;
- RTO;
- frecuencia;
- retención;
- cifrado;
- ubicación separada;
- prueba de restauración.

## Deploy

`build → tests → image scan → migrate check → backup gate → deploy → smoke → monitor → rollback`.

No auto-deploy de cambios normativos sólo por merge de código.

## Implementación P24

La ruta reproducible está en `infra/docker/api.Dockerfile`,
`infra/docker/web.Dockerfile` y `infra/docker-compose.production.yml`. Las
imágenes base están fijadas por digest; API y web ejecutan como usuarios no
root, usan healthchecks, stages separados y no reciben secretos en build.
`infra/docker/Caddyfile` es la referencia de reverse proxy/TLS.

La CI completa y los gates operativos están descritos en
`docs/ops/DEPLOYMENT_RUNBOOK.md`. `scripts/backup_postgres.py` genera dumps
custom-format con metadata y permisos 0600; `scripts/restore_drill.py` restaura
en una base temporal generada, valida migraciones/tablas y limpia el destino.
La política, el object storage separado y el rollback están en los runbooks de
`docs/ops/`. Los defaults locales no son una configuración de producción.
