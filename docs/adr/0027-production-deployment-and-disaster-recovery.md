# ADR-0027 — Reproducible production containers and recovery drills

**Estado:** ACCEPTED  
**Fecha:** 2026-08-17

## Contexto

El producto necesita una ruta operativa que pueda reconstruirse desde un
servidor limpio, con migraciones explícitas, imágenes reproducibles, backup
fuera del host y evidencia de restore. El repositorio no debe contener
credenciales ni elegir un proveedor cloud por accidente.

## Decisión

- API y web se construyen con Dockerfiles multi-stage, usuarios no root,
  lockfiles congelados, healthchecks y referencias base por digest.
- La imagen de API es el único proceso que ejecuta migraciones, mediante el
  servicio Compose de perfil `migration`; el proceso web nunca migra la base.
- PostgreSQL no se publica en producción. El reverse proxy Caddy es la única
  superficie HTTP(S) pública y termina TLS.
- Las imágenes de aplicación se promueven como referencias inmutables
  `registry/repository:release@sha256:digest`. Los tags son sólo alias de
  lectura humana y no son una entrada válida para el Compose de producción.
- Los backups custom-format se crean con `scripts/backup_postgres.py`, se
  cifran y se replican a object storage con retención/versionado gestionados
  fuera del host. `scripts/restore_drill.py` sólo restaura a una base temporal
  generada y la elimina al finalizar.
- La CI ejecuta verificaciones de código, contrato, migraciones, build de
  imágenes, scan de Critical, smoke y restore drill antes de promover una
  versión. Un cambio curricular requiere el flujo editorial y no se publica
  automáticamente por un merge de código.

## Consecuencias

- Se puede probar un rollback de imágenes sin alterar la revisión curricular
  publicada; las migraciones son forward-only y cualquier migración riesgosa
  requiere backup y plan de reversión compatible.
- El almacenamiento local privado sigue siendo el adaptador de desarrollo.
  En producción, los artefactos importados deben usar el bucket privado
  separado o un volumen cifrado respaldado por él; la política y el contrato
  están en `docs/ops/OBJECT_STORAGE_STRATEGY.md`.
- Un VPS sin secret manager, cifrado, backup off-site, TLS y restore drill no
  satisface la definición de producción aunque las imágenes compilen.
