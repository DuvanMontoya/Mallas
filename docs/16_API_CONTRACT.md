# 16 — API contract

## Public namespace and ownership

The public HTTP namespace is `/api/v1`. The version is an API contract version; it
is independent from curriculum revision versions, import `schema_version` values,
and the rule-engine AST version.

The current bounded-context routers are:

- `Operations`: `/health/live`, `/health/ready`, and the generated `/openapi.json`;
- `Identity`: `/auth/csrf`, `/auth/login`, `/auth/logout`, `/auth/me`, password reset,
  and email verification;
- `Student history`: `/history/imports`, `/history/attempts`, and their preview,
  reconciliation, confirmation, and mutation operations.

The broader product resources (curriculum, offerings, planning, optimization,
governance, and analytics) keep their domain ownership and are added as separate
routers when their application service and evidence contract are published. A
frontend feature must not invent an endpoint or duplicate a domain rule locally.

The authoritative machine-readable contract is
[`artifacts/openapi.json`](../artifacts/openapi.json). It is exported from the
running Django API and the TypeScript client in `packages/api-client` is generated
from that artifact. Hand-authored frontend API DTOs are prohibited when the type
is part of this contract.

## Success and error responses

Every v1 operation declares the same `ProblemDetails` schema for the standard
failure statuses: `400`, `401`, `403`, `404`, `409`, `422`, `428`, `429`, and
`500`. Successful responses are operation-specific and are also represented in
OpenAPI. The error body uses `application/json` and follows the Problem Details
shape without making clients depend on a media-type-specific implementation.

```json
{
  "type": "https://api.curriculum-navigator.local/problems/VALIDATION_ERROR",
  "code": "VALIDATION_ERROR",
  "title": "Request validation failed",
  "detail": "One or more request fields are invalid.",
  "status": 422,
  "correlation_id": "request-id-or-generated-uuid",
  "fields": {"body.email": "Input should be a valid email address"}
}
```

`code` is the stable machine-facing discriminator. `detail` is safe for the
caller and must not contain stack traces, secrets, or untrusted SQL/HTML. The
server accepts a safe `X-Request-ID` value (`A-Za-z0-9._-`, at most 80
characters), otherwise generates a UUID. The same value is returned in the
`correlation_id` field and the `X-Request-ID` response header. Support and audit
records use this identifier to connect an API failure with server logs.

Domain services raise typed errors; the API adapter maps them to stable codes.
The frontend must branch on `code`/`status`, not on localized `detail` text.

## Session authentication and CSRF

Authentication uses the secure Django session cookie. The cookie is HttpOnly and
SameSite-aware; production settings also enable `Secure`. Before a state-changing
request made with the session cookie, the client obtains a token from
`GET /api/v1/auth/csrf` and sends it as `X-CSRFToken`. The allowed origin policy
is enforced by the backend. A missing or invalid token returns the same error
shape with `403` and `code: CSRF_FAILED`.

Unauthenticated protected operations return `401` with
`code: AUTHENTICATION_REQUIRED`. Authorization failures return `403`; the API
does not leak whether an inaccessible student record exists.

## Pagination, filtering, and sorting

`GET /api/v1/history/attempts` accepts:

- `enrollment_id` (required UUID);
- `limit` (default `50`, inclusive range `1..100`);
- `offset` (default `0`, non-negative);
- `status` (optional academic attempt status, normalized to uppercase);
- `sort` (`term`, `course`, or `status`; default `term`).

The response is an `AttemptPage` object rather than a bare array:

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0,
  "next_offset": null,
  "previous_offset": null
}
```

Ordering is deterministic: every supported sort includes stable tie-breakers so
two reads of unchanged data have the same order. Invalid pagination, filters,
or sort values return a `ProblemDetails` response with a field-level explanation.

## Optimistic concurrency

Mutable history resources expose a `version` token derived from their persisted
`updated_at` value and return the same token as a quoted `ETag` header. Clients
must send that value in `If-Match` for edits and annulments:

```http
If-Match: "2026-08-16T03:00:00.123456+00:00"
```

Candidate reconciliation and attempt `PATCH`/`DELETE` require this precondition.
Missing `If-Match` returns `428 PRECONDITION_REQUIRED`. If another transaction
has changed the resource, the service locks the base row, detects the stale
token, and returns `409 STALE_RESOURCE`; it never silently applies last-write-wins.
The client must refetch the resource, present the new state, and ask the user to
retry the edit.

## Idempotency

`POST /api/v1/history/imports` accepts an optional `Idempotency-Key` header. The
key is 1–128 safe ASCII characters (`A-Z`, `a-z`, digits, `.`, `_`, `:`, `-`) and
is scoped to the enrollment. The backend serializes preview creation for an
enrollment and persists the key:

- retrying the same key with the same content returns the original batch with
  `created: false`;
- reusing the key for different content returns `409 IDEMPOTENCY_KEY_REUSED`;
- even without a key, the enrollment/content SHA-256 prevents duplicate import
  batches;
- confirmation is also domain-idempotent and reports `idempotent: true` on a
  replay of an already applied batch.

The frontend should generate one stable key per user-intended upload and reuse
it only for retries of that upload.

## Generation, freshness, and breaking changes

Run the following from the repository root after an API change:

```bash
uv run --project apps/api python scripts/export_openapi.py
pnpm --dir packages/api-client generate
pnpm --dir packages/api-client verify
python scripts/check_openapi.py
python scripts/check_openapi_breaking.py \
  --base-revision <git-base-sha>
```

`check-generated.mjs` regenerates the client in memory and compares it byte for
byte with `packages/api-client/src/generated.ts`; it fails on stale output.
The breaking-change checker detects removed operations, removed required request
fields/parameters, incompatible request types, removed success responses, and
incompatible required response fields/types. A deliberate breaking change must
be introduced under a new API version or an explicitly reviewed compatibility
strategy; the pull-request workflow runs the checker against the PR base.
