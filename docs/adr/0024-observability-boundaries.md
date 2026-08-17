# ADR-0024 — Observabilidad acotada y exportación OTel opt-in

## Estado

Aceptado — 2026-08-16.

## Contexto

La plataforma necesita diagnosticar requests, jobs, auditorías, readiness y
errores frontend sin convertir logs en un almacén de expedientes académicos ni
acoplar el dominio a un proveedor de telemetría.

## Decisión

- El backend instrumenta mediante middleware/decoradores pequeños y un registro
  de métricas acotado.
- OpenTelemetry SDK 1.44.0 es la API de tracing/metrics; el exportador OTLP
  HTTP 1.44.0 sólo se activa mediante configuración de entorno.
- Logs se emiten como JSON, con ids de correlación y campos de allowlist; no se
  serializan traceback ni mensajes de excepción.
- Liveness y readiness son endpoints distintos; readiness devuelve 503 seguro
  cuando falla la base.
- El endpoint de métricas expone sólo agregados y requiere token en producción.
- El frontend reporta errores/Web Vitals únicamente si se configura un endpoint
  explícito y usa `credentials: omit`.
- No se añade una plataforma de dashboard ni un SLO inventado al repositorio;
  su contrato operativo está en `docs/ops/`.

## Consecuencias

La solución funciona localmente sin collector y permite exportar a diferentes
backends sin tocar el dominio. Las métricas en memoria se pierden al reiniciar,
por lo que el despliegue que requiera continuidad debe configurar OTLP y una
política de retención. La redacción defensiva limita el diagnóstico de errores,
pero protege la frontera de privacidad; el detalle se consulta por los modelos
auditables y roles autorizados.

