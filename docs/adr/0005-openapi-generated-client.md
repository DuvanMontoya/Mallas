# ADR-0005 — OpenAPI como contrato y cliente TypeScript generado

**Estado:** ACCEPTED

El backend publica OpenAPI versionado. `packages/api-client` se genera y no se edita manualmente. CI falla si el contrato cambió y el cliente generado está desactualizado.
