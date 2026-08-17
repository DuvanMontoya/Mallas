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

## Notificaciones y canales

El centro de notificaciones se autoriza con la sesión Django y filtra cada
lectura por `recipient=request.auth`; un identificador de entrega ajeno
responde como no encontrado. El frontend no decide ownership, elegibilidad ni
contenido académico.

La frontera de contenido es deliberadamente restrictiva: el evento persistido
sólo conserva identificadores operacionales no sensibles y las plantillas
publicadas no interpolan revision codes, cursos, calificaciones, auditorías,
correos ni impacto individual. La respuesta HTTP entrega título, cuerpo,
locale y un `link_path` interno controlado; la UI rechaza rutas externas o
protocolos alternativos antes de crear un enlace.

Email permanece deshabilitado por defecto. Cuando se habilita mediante
configuración explícita, el adaptador recibe el correo sólo en la frontera de
entrega y un texto estático localizado; no se envían payloads JSON ni datos de
historia. Los errores del proveedor se registran con el UUID de delivery y un
código estable, nunca con el mensaje de excepción o el contenido del correo.
Los estados, claves de deduplicación y reintentos permiten inspección
operativa sin convertir datos personales en logs.

## Analítica estudiantil e institucional

La analítica institucional está separada de la consulta privada de matrícula:
requiere `ANALYST` o `ADMIN` y una institución explícita; una asignación de
programa no puede ampliar su alcance omitiendo `program_id`. El resultado
institucional no incluye nombre, correo, número de estudiante, UUID de
matrícula ni filas individuales. Los conteos de estudiantes distintos se
suprimen por debajo de `ANALYTICS_MIN_CELL_SIZE` (5 por defecto) y una
población completa inferior al umbral no recibe desgloses.

Las exportaciones sólo replican esos agregados, se marcan como `no-store`, se
entregan con MIME/descarga segura y crean un `AuditEvent`. Los identificadores
de rutas frecuentes son HMAC con `ANALYTICS_PSEUDONYMIZATION_KEY`; nunca se
usa un identificador de estudiante como clave visible. No hay perfil de
riesgo, clasificación sensible ni predicción individual. La UI muestra la
fuente, el estado epistemológico, la fecha de corte y la advertencia de que
elegibilidad no confirma oferta o matrícula.

## Hardening P23 — 2026-08-17

La frontera de fuentes ahora tiene un fetcher ejecutable y fail-closed en
`modules.governance.application.source_fetch`: allowlist exacta de hosts,
HTTPS/default-port por defecto, normalización IDNA, rechazo de credenciales,
fragmentos, loopback, rangos privados/reservados/link-local/multicast y
metadata, resolución de todas las direcciones, conexión con IP resuelta,
redirects revalidados uno a uno, timeout y límite de bytes. No se permite
descargar una fuente si `SOURCE_FETCH_ALLOWED_HOSTS` está vacío. El fetcher
devuelve bytes/hash para un snapshot; nunca publica una regla.

Las mutaciones API tienen un límite transaccional compartido por workers:
autenticación mantiene buckets por IP/identificador; uploads y gobierno tienen
presupuestos específicos; el resto de escrituras usa el límite general.
Los artefactos privados se crean en directorios 0700 y archivos 0600 cuando la
plataforma lo permite, con hash/contención/symlink checks y firmas de
ejecutables ampliadas. `AuditEvent` bloquea también `QuerySet.update/delete`
fuera de PostgreSQL y conserva el trigger de producción.

Los gates `scripts/scan_secrets.py` y `scripts/sast.py` forman parte de
`scripts/verify.py`; CI ejecuta además `pip-audit` contra el export frozen,
`pnpm audit`, check de despliegue y el escaneo de secretos. La revisión
completa, la matriz IDOR/BOLA, el runbook y la referencia de privilegios están
en `docs/security/`, `docs/ops/SECURITY_RUNBOOK.md` e
`infra/postgres/provision-least-privilege.sql`.

La MFA de roles privilegiados sigue siendo una condición del IdP institucional
externo: el repositorio no finge un almacén TOTP local ni habilita publicación
si el despliegue no puede imponer esa política. La separación editor/reviewer,
la confirmación explícita, el ETag, la inmutabilidad y el audit log son los
controles de aplicación verificables.
