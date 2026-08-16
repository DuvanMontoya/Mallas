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
