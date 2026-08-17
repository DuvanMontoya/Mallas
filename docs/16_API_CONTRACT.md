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
- `Curriculum`: `/curriculum-map`, a provenance-aware public read model for a
  curriculum revision and its non-normative visual layouts.
- `Offerings`: `/academic-terms`, `/offerings` and `/offerings/schedule`, with
  temporal source freshness and exact schedule conflict read models.
- `Planning`: `/scenarios`, `/scenarios/{id}`, planned-course mutations,
  duplication, archive, compare and the redacted public
  `/shared/scenarios/{share_token}` view.

The broader product resources (curriculum, offerings, planning, optimization,
governance, and analytics) keep their domain ownership and are added as separate
routers when their application service and evidence contract are published. A
frontend feature must not invent an endpoint or duplicate a domain rule locally.

The authoritative machine-readable contract is
[`artifacts/openapi.json`](../artifacts/openapi.json). It is exported from the
running Django API and the TypeScript client in `packages/api-client` is generated
from that artifact. Hand-authored frontend API DTOs are prohibited when the type
is part of this contract.

## Editorial publication impact

The scoped editorial read endpoint
`GET /api/v1/governance/publications/{publication_id}/impact` returns the
immutable publication event and its downstream impact. It is authorized using
the same institution/program scope as the governance backoffice and never
changes a revision, enrollment or audit.

The response has this shape:

```json
{
  "publication_id": "uuid",
  "event": {
    "id": "uuid",
    "event_key": "curriculum.revision.published:<publication-id>",
    "event_type": "curriculum.revision.published",
    "schema_version": 1,
    "publication_id": "uuid",
    "revision_id": "uuid",
    "superseded_revision_id": "uuid|null",
    "changed_courses": [],
    "changed_groups": [],
    "changed_requirements": [],
    "impact_summary": {},
    "recompute_plan": {},
    "notification_plan": {},
    "enrollment_impacts": []
  }
}
```

Each enrollment impact contains the previous revision, optional previous audit
run and result hash, stable recomputation key, explicit status and
`requires_revision_decision`. The endpoint reports queued notification work;
it does not claim delivery. Stable errors include
`publication_not_found`, `governance_forbidden` and
`publication_event_missing`. The generated TypeScript client exposes
`getGovernancePublicationImpact`.

## Notification center contract

The authenticated notification center is a private user projection. Its
endpoints are:

- `GET /api/v1/notifications?unread_only=false&limit=50&before=<cursor>`;
- `POST /api/v1/notifications/read-all`;
- `POST /api/v1/notifications/{delivery_id}/read`;
- `GET /api/v1/notifications/preferences`;
- `PUT /api/v1/notifications/preferences/{event_type}`.

The feed returns `items`, `unread_count`, and an opaque `next_cursor`. A cursor
is derived from delivery creation time and UUID and must be sent back as
`before`; invalid cursors are rejected. Every item is a server-rendered,
localized safe template with `event_type`, `channel`, `status`, `title`,
`body`, `locale`, `link_path`, `read_at`, `created_at`, and `delivered_at`.
The response never contains the source revision payload or another student's
academic data.

Preferences are keyed by supported event type and contain
`in_app_enabled`, `email_enabled`, and `locale`. The backend validates the
event type, normalizes locales to `es-CO` or `en`, and applies the preference
when materializing future channel deliveries. Email delivery is optional and
does not change the contract of the in-app feed. All endpoints use the common
`ProblemDetails` envelope for authentication, ownership, validation, and rate
limit failures. The generated TypeScript client exposes
`getNotifications`, `markNotificationRead`, `markAllNotificationsRead`,
`getNotificationPreferences`, and `updateNotificationPreference`.

## Planning contract

`ScenarioView.version` is the optimistic-concurrency version. `PATCH` and
course movement/removal require `If-Match`; missing preconditions return
`428 PRECONDITION_REQUIRED` and a stale version returns `409 STALE_RESOURCE`.
The response includes incremental validation and a
`ScenarioAuditProjectionView`; the latter is explicitly a projection and is
never an official audit run.

`POST /scenarios` creates a private scenario by default. `sharing_enabled` is
an explicit opt-in. The public share response contains only scenario name,
status, target term, planned course code/name/credits/term and a privacy
statement. It never returns `enrollment_id`, student identity, attempts,
preferences or audit projection.

Error responses use the common `ProblemDetails` envelope. The frontend must
keep backend warning codes and correlation IDs available to the user/support
workflow; it must not replace `UNKNOWN` with a guessed boolean.

## Optimization contract

Optimization belongs to the scenario bounded context but has its own
execution resource. The authenticated owner or an authorized advisor may
create and read runs for a scenario:

- `POST /scenarios/{scenario_id}/optimization-runs` accepts
  `time_limit_seconds`, `unknown_offering_policy` (`ALLOW_UNKNOWN` or
  `REQUIRE_OFFERED`), optional `credit_target`, optional
  `preferred_credits_per_term` and `random_seed`; it returns `202` with a
  queued `OptimizationRun`.
- `GET /scenarios/{scenario_id}/optimization-runs` lists the runs for that
  scenario.
- `GET /optimization-runs/{run_id}` returns the current state and an ETag based
  on the output hash, or the input hash while no output exists.
- `POST /optimization-runs/{run_id}/cancel` requests cooperative cancellation
  and returns the updated run.

`QUEUED` and `RUNNING` are operational states. A completed run has one of
`OPTIMAL`, `FEASIBLE`, `INFEASIBLE` or `UNKNOWN`. The response includes the
immutable `input_hash`, `output_hash` when available, `solver_version`, ordered
objective values, selected courses, explanations, assumptions, conflicts and
execution timestamps. `INFEASIBLE` and `UNKNOWN` are valid domain results, not
HTTP failures; malformed requests, ownership failures and missing runs use
the common `ProblemDetails` envelope.

The request is evaluated from a canonical backend snapshot. The browser never
evaluates the rule AST, changes a solution into a scenario, or turns an
unknown offering into an offered fact. A result is only a proposal until the
user applies individual scenario edits through the planning endpoints.

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

## Academic overview read model

`GET /api/v1/academic-overview` is the authenticated student/advisor read model
for the dashboard and audit workspace. `enrollment_id` is optional for a
student with one or more enrollments; when omitted, the API selects that
student's most recent enrollment with an active or reviewable status. An
explicit enrollment is always checked with the same ownership/advisor rules as
history reads and never permits cross-student access.

The response is assembled by `modules.audit.application.overview` from the
latest persisted `DegreeAuditResult` and its reproducibility metadata. A newly
created enrollment with no audit run receives a read-only preview and does not
create a database row during `GET`. History imports and manual history
mutations persist the authoritative run inside their existing transaction.

The contract includes:

- `audit.overall`: required, earned, applied, unapplied and a backend-owned
  credit progress percentage;
- `components` and `groups`: labelled progress, remaining credits, mandatory
  missing courses and available options;
- `eligible_courses`, `blocked_courses` and `unknown_courses`: eligibility
  resolved by the backend, with requirement reasons and deep links;
- `graduation_requirements` and `external_graduation_requirements`: separate
  non-credit requirements with status, epistemic status, source references and
  accessible evidence details;
- `unknowns`, `warnings`, `next_unlocks`, `history` and `links` for the empty,
  incomplete and explainable states.

`audit.overall.credit_progress_percent` is a credit-progress measure only. A
value of `100` never means graduation when a group, mandatory course, external
requirement or `UNKNOWN` fact remains unresolved. The endpoint returns an ETag
based on the persisted result hash (or the deterministic read-only preview
hash), allowing clients to cache a read without weakening the provenance
contract.

## Curriculum map read model

`GET /api/v1/curriculum-map` is the read model for the interactive curriculum
map. It accepts `plan_code` (default `2514`), an optional `revision_id`, an
optional `enrollment_id`, and an optional `term_code`. The request is public
when no enrollment is requested: it exposes curriculum facts, source evidence,
the dependency projection, and the explicitly non-normative layout policy.
When `enrollment_id` is supplied, the backend applies the same ownership and
advisor authorization boundary as the audit read model; a caller cannot use an
IDOR to obtain another student's personal statuses.

The response contains `revision`, `layout_policy`, `components`, `groups`,
`courses`, `offering_context`, `personal`, `warnings`, and `links`. Courses
include requirement ASTs, evidence references, direct dependency/unlock lists,
and epistemic/personal statuses. The revision includes its publication state,
content hash, required credits, institution/campus/program labels, and a
`normative` flag. The policy marks layouts as `official: false` until an
official source explicitly supplies a visual placement rule; a dependency
level is never a semester.

`personal_status` is backend-owned. Without an authorized enrollment the map
uses `NOT_ASSESSED`; an unresolved academic fact remains `UNKNOWN` rather than
becoming eligible. `offering_state` is `UNKNOWN`/`NOT_REPORTED` until a
`term_code` is selected and the offering source says otherwise. Requirement
ASTs and evidence are returned for explanation, not for client-side
eligibility calculations.

The endpoint returns the revision content hash as a quoted `ETag`. Clients may
cache that representation, but must not cache private enrollment data across
users or reinterpret a visual layout as an official semester placement. The
generated TypeScript client exposes `getCurriculumMap`; the map component may
filter and persist view preferences in URL/local storage, but it cannot alter
the read model or resolve domain rules.

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

## Dependency graph read model

`GET /api/v1/dependency-graph` accepts `plan_code`, `revision_id`,
`enrollment_id`, `term_code` and `selected`. It applies the same enrollment
ownership/advisor boundary as the curriculum map and returns `NOT_ASSESSED`
when no authorized personal context is available. The response is an ETagged,
deterministic read model with `revision`, semantic `nodes`, typed `edges`,
`direct_relations`, optional `focus`, `cycles`, `warnings` and `links`.

`COURSE` nodes represent courses. `CONDITION` nodes represent AST logic and
retain their requirement code and path; thresholds are never fabricated as
course prerequisites. Edges carry a stable ID, source/target, semantic kind,
human label, requirement code and directness. `direct_relations` is the
course-only relation projection used for direct prerequisite/corequisite and
unlock lists. `focus` additionally contains deterministic ancestor/descendant
closures and shortest paths whose node IDs retain intermediate conditions.
Cycle detection is deterministic and returned as a governance signal; it does
not silently change eligibility. The generated client exposes
`getDependencyGraph`, and consumers must not recompute the rule graph in the
browser.

## Academic terms, offerings and schedules

The temporal offering contract is independent of curriculum revisions. Public
read endpoints are:

- `GET /api/v1/academic-terms` and `GET /api/v1/academic-terms/{id}` for term
  metadata, status, campus dates and source freshness;
- `GET /api/v1/offerings` for the term offering read model, optionally filtered
  by `term_code`, `course_code`, `status` and authorized `enrollment_id`;
- `GET /api/v1/offerings/{id}`, `GET /api/v1/sections/{id}` and
  `GET /api/v1/meetings/{id}` for focused temporal records;
- `GET /api/v1/offerings/schedule?term_code=...&section_ids=...` for exact
  conflict evaluation of the selected sections.

The offering response keeps three backend-owned dimensions separate:
`offered_state`, `eligibility_state` and `schedulable_state`. A group can be
offered and blocked, or a course can be eligible while not offered. Missing or
ambiguous facts remain `UNKNOWN` and include an explanation.

Every source projection includes `source_key`, `source_name`, URL, retrieval
timestamp, SHA-256 when available and `freshness` (`FRESH`, `STALE` or
`UNKNOWN`). Capacity is explicitly described by `capacity_status`; without a
source declaration that the value is real time, clients must show the value as
reported/non-real-time or unknown and must not promise a reservable seat.

Term administration uses `POST`, `PATCH` and `DELETE` on
`/api/v1/academic-terms` and is restricted to the existing scoped governance
roles. These mutations affect temporal data only and never publish or mutate a
curriculum revision. Offering ingestion is an application service behind the
`OfferingSourceAdapter`; the public API does not scrape an authenticated SIA
session or perform enrollment.
