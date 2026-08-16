# 30 — API and data versioning

- The public API starts at `/api/v1`; the namespace is owned by the API contract,
  not by a Django app or a frontend release.
- Do not create a new API version for an internal refactor that preserves the
  generated OpenAPI contract.
- A breaking contract requires a new API version or a documented, reviewed
  compatibility strategy. The PR workflow compares the current
  `artifacts/openapi.json` with the base revision using
  `scripts/check_openapi_breaking.py`.
- The checker is intentionally conservative and detects removed operations,
  removed required parameters/fields, incompatible request field types, removed
  success responses, and incompatible required response fields/types. It does
  not replace human review of semantics, authorization, privacy, or data meaning.
- `packages/api-client/src/generated.ts` is a reproducible generated artifact.
  `pnpm --dir packages/api-client verify` regenerates it in memory and fails on
  byte-level drift. It must be regenerated in the same change as the OpenAPI
  artifact; no manually duplicated API DTOs are accepted.
- Curriculum plans and revisions have versioning independent from API versions.
  A published curriculum revision is immutable; a new rule creates a new
  revision and preserves the prior evidence.
- Import schemas have `schema_version` and source/parser versions. Import
  batches retain provenance and do not inherit a new API version merely because
  the transport endpoint gains a compatible field.
- The rule AST has `rule_schema_version`; serialized AST compatibility is tested
  independently from HTTP contract compatibility.
