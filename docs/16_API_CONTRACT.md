# 16 — API

## Principios

- REST pragmático;
- OpenAPI generado;
- schemas versionados;
- errores consistentes;
- pagination;
- idempotency keys en operaciones apropiadas;
- ETags/version fields para edición concurrente.

## Recursos base

`/api/v1/programs`
`/api/v1/curriculum-plans`
`/api/v1/curriculum-revisions`
`/api/v1/courses`
`/api/v1/requirements`
`/api/v1/audits`
`/api/v1/student-records`
`/api/v1/offerings`
`/api/v1/scenarios`
`/api/v1/optimization-runs`
`/api/v1/sources`
`/api/v1/change-proposals`
`/api/v1/reviews`

## Endpoint compuesto útil

`GET /me/academic-overview`
puede devolver un read model optimizado, pero no duplicar lógica.

## Error envelope

```json
{
  "type": "https://...",
  "code": "CURRICULUM_RULE_UNKNOWN",
  "title": "...",
  "detail": "...",
  "status": 409,
  "correlation_id": "...",
  "fields": {}
}
```

Inspirarse en Problem Details sin acoplarse mal.

## Concurrencia

Edición de revisión/propuesta usa optimistic concurrency. Nunca last-write-wins silencioso.
