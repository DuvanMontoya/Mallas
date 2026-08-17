# Runbook de rollback

## Rollback de aplicación sin restaurar datos

1. Pausar la promoción y conservar logs/trace IDs de la release fallida.
2. Confirmar el digest conocido-bueno anterior y que sus migraciones son
   compatibles con el esquema actual.
3. Cambiar `API_IMAGE` y `WEB_IMAGE` al digest anterior en el secret manager o
   release manifest; nunca usar sólo un tag mutable.
4. Ejecutar `docker compose ... pull` y `up -d api web reverse-proxy`.
5. Ejecutar `scripts/smoke.py` y los journeys críticos.
6. Registrar causa, versión, ventana, métricas y decisión en el incidente.

## Rollback con migración incompatible

No intentar `downgrade` automático de Django. Aislar el tráfico, preservar la
base actual, recuperar el backup pre-deploy en una instancia temporal y
ejecutar el restore drill ampliado. La recuperación productiva requiere una
orden aprobada, validación de integridad y una ventana comunicada; `docker
compose down -v` está prohibido en producción.

## Criterio de cierre

El rollback sólo se cierra cuando live/ready, OpenAPI, login, dashboard,
planner, importación privada y flujo editorial responden de acuerdo con los
gates, sin reintroducir una revisión curricular anterior ni perder audit events.
