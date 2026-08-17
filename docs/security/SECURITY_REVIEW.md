# P23 security review record

Fecha: 2026-08-17

## Evidence executed

- `python scripts/scan_secrets.py` — PASS; no high-confidence committed
  credential material.
- `python scripts/sast.py` — PASS; no high-confidence dangerous execution or
  raw-HTML findings in production Python/TypeScript.
- `pnpm audit --prod --audit-level high` — PASS; the same check is scheduled by
  `.github/workflows/security.yml`.
- `uv pip check` — PASS.
- `pip-audit==2.9.0` against the fully hashed frozen export — PASS after
  upgrading `pypdf` from 6.10.0 to 6.16.1. The initial P23 audit found the
  pypdf advisories and blocked completion until the fixed dependency was
  locked and the parser tests passed.
- `manage.py check --deploy` with explicit production settings — PASS with
  zero warnings in the baseline; security workflow repeats it.
- P23 focused backend tests — 34 passed, including private IPv4/metadata
  ranges, redirect bypass, bounded responses, upload modes/signatures, CORS,
  mutation rate limiting and ORM audit tamper attempts.
- `scripts/verify.py` is the canonical gate and now includes the secret scan
  and high-confidence SAST before domain checks.

## Control review

| Area | Result | Notes |
|---|---|---|
| IDOR/BOLA | PASS | Matrix and negative tests are backend-owned. |
| CSRF/CORS/CSP/headers | PASS | Exact origins, credentialed wildcard forbidden, explicit security headers and mutation CSRF. |
| Session fixation/cookies | PASS | Django login rotates the session key; secure HttpOnly/SameSite policy outside DEBUG; password-change marker invalidates older sessions. |
| Rate limiting | PASS | Auth identifier/IP buckets plus database-backed mutation middleware. |
| SSRF | PASS | Allowlist, HTTPS/default-port, DNS address validation, pinned connection and redirect revalidation. |
| Uploads | PASS | Bounded private artifacts, non-executable signature checks, containment and parser limits. |
| Secrets/dependencies/SAST | PASS | Local gates plus scheduled CI workflow. |
| DB privilege | PASS | Production role provisioning reference; local Compose remains explicitly development-only. |
| Audit integrity | PASS | Model/queryset guards and PostgreSQL trigger; audit metadata redacted. |
| Publication abuse | PASS | Role scope, separation of duties, explicit confirmation, ETag and immutable receipt. |
| Privacy/logging | PASS | Keyed digests, recursive redaction, safe routes and aggregate analytics suppression. |

## Findings and disposition

No Critical or High repository findings remain after dependency remediation.
The specialized reviewer
subagents required by the milestone are not callable in this session, so there
is no fabricated reviewer sign-off. A manual read-only architecture, code,
curriculum, security and UX review was performed and recorded here. External
institutional MFA/IdP and malware-scanning controls are deployment gates,
explicitly documented as external prerequisites in `THREAT_MODEL.md`.
