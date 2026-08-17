# Security runbook

This runbook is for the on-call owner and the institutional platform team.
Never paste secrets, raw student history, tokens or uploaded documents into an
incident ticket.

## Triage and containment

1. Record the UTC time window, deployment version, safe route and
   `X-Request-ID`/`X-Trace-ID`. Do not record query strings or request bodies.
2. If account takeover or publication abuse is suspected, disable the affected
   role assignment, rotate the user's password through the identity process,
   and invalidate the session store. Preserve the corresponding `AuditEvent`
   and publication receipt.
3. If a source-fetch or upload incident is suspected, disable
   `SOURCE_FETCH_ALLOWED_HOSTS` or the upload route at the reverse proxy,
   quarantine the private storage root, and preserve SHA-256 metadata. Do not
   execute or open an untrusted artifact outside the parser sandbox.
4. If a secret is exposed, revoke it in the secret manager first, then rotate
   `DJANGO_SECRET_KEY`, pseudonymization keys, database credentials and OTLP
   credentials as applicable. A Django secret rotation invalidates signed
   tokens; coordinate the user-facing reset flow.

## Verification after containment

```powershell
python scripts/scan_secrets.py
python scripts/sast.py
pnpm audit --prod --audit-level high
$env:DATABASE_URL='postgresql://runtime-user@db/curriculum'
uv run --frozen python scripts/verify.py
uv run --frozen python scripts/smoke.py --base-url https://api.example.edu --web-url https://app.example.edu
```

Check that `live` is reachable, `ready` reflects database health, metrics are
not public without `OBSERVABILITY_METRICS_TOKEN`, and all mutation responses
retain correlation/security headers.

## Audit integrity

Audit events are append-only. If an update/delete is reported, stop any
operator using a superuser database session, preserve the database WAL/audit
logs, and compare the event table with the last encrypted backup. The
production role must not own or have `UPDATE/DELETE` privileges on the audit
table; apply `infra/postgres/provision-least-privilege.sql` and run a restore
drill before re-enabling traffic.

## Dependency and source freshness incidents

- A high dependency advisory blocks release until the lockfile is upgraded,
  the compatibility suite passes and the advisory is documented.
- A stale or conflicting normative source never auto-publishes. Keep the
  proposal in `DRAFT`/`IN_REVIEW`, preserve the archived snapshot and create a
  new evidence-backed review decision.
- A source-fetch failure is fail-closed. Do not broaden the host allowlist or
  allow HTTP/private ranges as an emergency workaround.

## Contacts and evidence

The deployment must fill in institutional contacts, IdP/MFA owner, database
owner, backup operator and data-protection officer. The repository provides the
safe technical controls and evidence locations but does not invent people or
retention periods.
