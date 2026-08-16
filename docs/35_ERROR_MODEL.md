# 35 — Modelo de errores

El API no devuelve strings arbitrarios como contrato.

## Envelope conceptual

```json
{
  "error": {
    "code": "CURRICULUM_RULE_UNKNOWN",
    "message": "No se puede determinar el requisito con las fuentes publicadas.",
    "details": {},
    "trace_id": "..."
  }
}
```

## Familias
- `AUTH_*`
- `PERMISSION_*`
- `VALIDATION_*`
- `NOT_FOUND_*`
- `CONFLICT_*`
- `CURRICULUM_*`
- `AUDIT_*`
- `IMPORT_*`
- `OFFERING_*`
- `OPTIMIZATION_*`
- `EXTERNAL_SOURCE_*`
- `RATE_LIMIT_*`
- `INTERNAL_*`

Los mensajes para usuario y los detalles técnicos/logs están separados. Nunca filtrar secretos/stack traces.
