# 17 — Seguridad y privacidad

## Threat model mínimo

Activos:
- cuentas;
- historia académica;
- archivos importados;
- reglas publicadas;
- privilegios editoriales;
- secretos;
- backups.

Amenazas:
- account takeover;
- IDOR/BOLA;
- CSRF;
- XSS;
- SSRF en ingestión de fuentes;
- upload malicioso;
- privilege escalation;
- supply-chain;
- publicación curricular no autorizada;
- leakage en logs;
- mass assignment.

## Controles

- auth robusta;
- RBAC + checks de ownership;
- sesiones seguras;
- 2FA opcional/obligatoria para roles editoriales si se implementa;
- CSRF;
- CSP;
- CORS mínimo;
- rate limit;
- file type + size + malware scanning;
- sandbox/parsing seguro;
- no permitir URL fetch a redes privadas;
- audit log append-oriented;
- secret manager en producción;
- dependency scanning;
- SAST;
- backups cifrados;
- least privilege DB.

## Privacidad

- minimizar PII;
- separar perfil de historia;
- export/delete flows según política legal aplicable;
- definir retención;
- nunca enviar historia completa a un LLM externo por defecto;
- si se usa LLM para parsing, aplicar consentimiento/política y redacción cuando sea viable.

## Roles

Ver `docs/18_AUTHORIZATION_MATRIX.md`.
