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

## Implementación P05

La aplicación usa sesión first-party de Django con cookie `HttpOnly`,
`SameSite=Lax` y `Secure` fuera de DEBUG. Las operaciones mutables de
identidad usan la comprobación CSRF de Ninja; el frontend obtiene el token en
`GET /api/v1/auth/csrf`. `OriginAndSecurityMiddleware` permite sólo los
orígenes configurados, responde preflight explícito y emite CSP, Permissions
Policy, COOP y CORP.

`identity.User` conserva la cuenta separada de `StudentProfile` y expone
login/logout, `/me`, reset de contraseña y verificación de correo. Los enlaces
usan tokens Django con expiración; el reset marca el cambio de contraseña y
`PasswordChangeSessionMiddleware` invalida sesiones anteriores. Las respuestas
de reset no enumeran cuentas.

`RoleAssignment` permite roles con alcance global, institucional o de programa;
`StudentAdvisorAssignment` es la delegación explícita para consultar historia
ajena. Las políticas de autorización están centralizadas en
`modules.identity.application.authorization`; no se decide ownership en el
frontend. Editor puede trabajar drafts, Reviewer/Admin pueden publicar y una
revisión publicada no puede editarse.

`AuditEvent` es append-only en modelo, admin y trigger de PostgreSQL. En SQLite, usado
para desarrollo/tests, la protección de modelo/admin cubre las rutas de aplicación; la
integridad de producción se asegura con el trigger PostgreSQL. Los eventos
no guardan email, contraseña, token ni IP en claro; los identificadores y la IP
se almacenan como digest con la clave de configuración. `RateLimitBucket` usa
ventanas transaccionales en la base para compartir límites entre workers.

Los archivos de historia se validan antes de persistir, se almacenan fuera de media
pública bajo `PRIVATE_IMPORT_STORAGE_ROOT`, no se ejecutan y sólo se exponen después de
comprobar ownership/RBAC del enrollment. Se rechazan extensiones no permitidas,
excesos de tamaño, firmas de ejecutables/archivos comprimidos, firmas PDF incoherentes,
NUL y texto no UTF-8. La extracción PDF es text-only y sus resultados siempre requieren
confirmación humana.

La frontera de MFA está documentada en ADR-0012: P05 no incorpora una
dependencia de TOTP/WebAuthn sin política de enrolamiento/recuperación
verificada; los controles temporales de separación de funciones, CSRF,
cookies, rate limiting, ownership y auditoría protegen la publicación hasta el
hardening dedicado.
