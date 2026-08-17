# ADR-0026 — Egress policy and shared mutation limits

**Estado:** ACCEPTED  
**Fecha:** 2026-08-17

## Contexto

Normative sources and user uploads are untrusted boundaries. The existing
application already had ownership, CSRF, secure first-party sessions and
append-only audit controls, but source retrieval was not an executable
security boundary and mutation limits were not shared across all workers.

## Decisión

- Source retrieval uses `SafeSourceFetcher`: explicit host allowlist, HTTPS by
  default, default ports only, no credentials/fragments, IDNA normalization,
  rejection of private/reserved/loopback/link-local/multicast/unspecified
  resolutions, pinned socket connections, bounded bytes/time and manual
  redirect validation. An empty allowlist fails closed.
- State-changing API requests use database-backed fixed-window limits keyed by
  authenticated user or client IP. Authentication keeps stricter identifier/IP
  limits; uploads and governance mutations receive lower route-specific
  budgets.
- Private imports use containment plus 0700 directories and 0600 files. The
  ORM cannot bulk-update/delete audit events on non-PostgreSQL test backends;
  PostgreSQL remains protected by its trigger.
- Production database role separation is documented in
  `infra/postgres/provision-least-privilege.sql`; local Compose is not a
  production privilege model.

## Consequences

The controls add small synchronous checks and database counters to mutation
requests. This is intentional: correctness and abuse resistance outweigh the
cost for sensitive writes, while read paths remain unaffected. The fetcher is
not an authority for curriculum content; downloaded bytes still require
evidence and governance review. Institutional MFA remains an external IdP
deployment gate for privileged roles rather than an invented local TOTP store.
