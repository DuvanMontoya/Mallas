# 30 — Versionado de API y datos

- API pública comienza `/api/v1`.
- No versionar sólo por cada cambio interno.
- Breaking contract → nueva versión o estrategia compatible.
- Currículos tienen versionado independiente de API.
- Import schemas tienen `schema_version`.
- AST tiene `rule_schema_version`.
- OpenAPI se versiona y se compara en CI.
