# ADR-0005 — OpenAPI como contrato y cliente TypeScript generado

**Estado:** ACCEPTED

## Decisión

El backend genera el contrato versionado localmente y lo archiva en
`artifacts/openapi.json`; no expone el documento por HTTP.
`packages/api-client/src/generated.ts` se genera con `openapi-typescript` desde ese artefacto y se consume mediante
`openapi-fetch`; no se editan manualmente los tipos de transporte.

La frescura es una comparación byte a byte de la salida generada en memoria. La
compatibilidad hacia atrás se revisa con `scripts/check_openapi_breaking.py`
contra el `artifacts/openapi.json` de la base del pull request. El checker cubre
los cambios estructurales de mayor riesgo, mientras que la revisión humana
continúa siendo obligatoria para semántica, autorización, privacidad y cambios
de significado.

## Flujo requerido

```text
API schema → export_openapi.py → artifacts/openapi.json
          → openapi-typescript → packages/api-client/src/generated.ts
          → check-generated.mjs + breaking diff in CI
```

Una modificación de endpoint debe actualizar contrato, cliente, pruebas de
contrato y documentación en el mismo cambio. CI falla si el artefacto OpenAPI o
el cliente están obsoletos; los cambios breaking requieren `/api/v2` o una
estrategia de compatibilidad explícita y revisada.
