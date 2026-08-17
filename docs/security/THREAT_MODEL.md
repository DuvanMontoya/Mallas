# Threat model — P23 security hardening

Fecha de revisión: 2026-08-17 -05:00

## Sistema y trust boundaries

```text
┌──────────────────────┐      TLS / CSRF / CORS       ┌─────────────────────┐
│ Navegador first-party│ ───────────────────────────▶ │ Next.js web         │
│ estudiante/editor   │                               │ BFF sin autoridad   │
└──────────────────────┘                               └─────────┬───────────┘
                                                                  │ server-side API
                                                                  ▼
┌──────────────────────┐      private network / TLS    ┌─────────────────────┐
│ Reverse proxy / IdP  │ ───────────────────────────▶ │ Django API          │
│ headers confiables   │                               │ dominio + RBAC      │
└──────────────────────┘                               └──────┬──────┬───────┘
                                                               │      │
                                         least privilege       │      │ egress allowlist
                                                               ▼      ▼
                                                     ┌────────────┐ ┌──────────────┐
                                                     │ PostgreSQL │ │ fuente HTTP  │
                                                     │ audit/data  │ │ no confiable  │
                                                     └─────┬──────┘ └──────┬───────┘
                                                           │               │
                                                           ▼               ▼
                                                     ┌────────────┐ ┌──────────────┐
                                                     │ backups    │ │ source bytes │
                                                     │ encrypted  │ │ private store│
                                                     └────────────┘ └──────────────┘
```

The browser, uploaded bytes, normative URLs, email provider, reverse-proxy
headers and backup destination are untrusted inputs or external boundaries.
The Next.js layer is presentation/BFF only: it cannot decide eligibility,
publication or graduation. The Django domain engine and PostgreSQL are the
authoritative boundaries for those decisions.

## Assets

| Asset | Impact | Required control |
|---|---|---|
| Accounts and sessions | account takeover, publication abuse | Django session rotation, HttpOnly/Secure/SameSite cookies, CSRF, bounded auth attempts, email verification, external institutional MFA/IdP gate for privileged production roles |
| Student history and imports | privacy, academic harm | ownership/RBAC on every enrollment, private storage, bounded parser, no-overwrite reconciliation, redacted audit/logging |
| Published revisions and evidence | incorrect graduation decisions | immutable revisions, evidence/provenance, editor/reviewer separation, explicit publication confirmation, append-only events |
| Secrets and keys | total compromise | environment/secret manager, repository scanner, no secrets in images, rotation runbook |
| Database and backups | bulk disclosure/tampering | separate owner/migrator/runtime roles, encrypted backups, restore drill, protected audit tables |

## Abuse cases and controls

| Threat | Attack path | Control and evidence |
|---|---|---|
| IDOR/BOLA | change another enrollment, batch, attempt or scenario UUID | centralized ownership/RBAC; negative matrix in `IDOR_BOLA_TEST_MATRIX.md`; identity, history and planning tests |
| CSRF/session fixation | cross-site mutation or reuse of pre-login session | Ninja cookie CSRF, first-party Origin policy, Django `login()` session rotation, password-change marker middleware |
| CORS abuse | attacker origin with credentialed API request | exact origin allowlist, no wildcard credentials, explicit headers/methods; security tests |
| SSRF and redirect bypass | source URL points to loopback/private/metadata or redirects there | exact host allowlist, HTTPS/default-port policy, IDNA normalization, DNS resolution of every address, pinned socket, manual redirect validation, size/timeout bounds |
| Malicious upload | executable, archive, traversal, symlink, oversized or malformed PDF | extension/signature/MIME/UTF-8/NUL/size checks, private containment, 0700 directories/0600 files, text-only PDF parser with page/record limits |
| Publication abuse | editor publishes or reviewer self-approves | centralized `can_publish_revision`, editor cannot publish, submitter cannot approve/publish, approved state and explicit confirmation, immutable receipt/event |
| Audit tampering | ORM bulk update/delete or direct DB mutation | model guards, non-PostgreSQL QuerySet guards, PostgreSQL trigger, PROTECT foreign keys, admin read-only |
| Rate-limit bypass | rotate API paths/workers or upload repeatedly | database-backed fixed-window auth limits plus mutation middleware by user/IP and sensitive route class |
| Log/analytics leakage | PII, tokens or academic payload in telemetry | recursive metadata redaction, keyed digests, normalized routes, aggregate analytics/suppression |
| Supply chain | vulnerable dependency or committed credential | frozen lockfiles, weekly security workflow, `pnpm audit`, `pip-audit`, custom secret scan and SAST |

## Residual external prerequisites

- Institutional deployment must place reviewer/admin accounts behind the
  institution's MFA/IdP policy before granting privileged roles. This
  repository does not invent a local recovery-sensitive TOTP store; the
  boundary is explicit in ADR-0012. A production deployment that cannot
  provide that IdP control must keep publication roles disabled.
- Malware scanning of uploaded files remains an infrastructure control. The
  application parser is bounded, text-only for PDF and never executes an
  upload; an institutional deployment should add an isolated scanner before
  accepting high-risk files.
- Egress filtering at the network layer remains defense in depth. The fetcher
  itself rejects private/reserved resolutions and pins the resolved address,
  while production firewalls should deny metadata and private destinations.

## Review result

No Critical or High findings were reproducible in the repository after the P23
changes. The unavailable reviewer subagents (`security-reviewer`,
`architecture-reviewer`, `code-reviewer`) were replaced by a documented
manual read-only review; this is a tooling limitation, not a claim that an
external reviewer signed off.
