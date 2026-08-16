# Infraestructura

Este directorio contiene una base reproducible, no una decisión irrevocable sobre proveedor cloud.

## Local
`docker-compose.bootstrap.yml` levanta PostgreSQL para el bootstrap. codex debe convertirlo en el Compose real una vez haya resuelto las versiones y nombres de servicios.

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

No desplegar automáticamente desde este kit sin completar P24.
