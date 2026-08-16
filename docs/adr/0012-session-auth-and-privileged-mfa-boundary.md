# ADR-0012 — Sesión first-party, boundary de MFA privilegiado y controles temporales

**Estado:** ACCEPTED  
**Fecha:** 2026-08-16

## Contexto

La aplicación web es first-party y comparte el navegador con la API. La
historia académica y los cambios curriculares son datos sensibles. El stack
fijado ya incluye el backend Django y su middleware de sesión, pero no incluye
un proveedor de identidad externo ni una dependencia de TOTP/WebAuthn con
política de enrolamiento, recuperación y rotación de dispositivos definida.

## Decisión

Usar sesiones Django server-side para la web first-party. La cookie de sesión
es `HttpOnly`, `SameSite=Lax` y `Secure` fuera de DEBUG; las operaciones que
usan cookies pasan por CSRF de Ninja y el endpoint `/api/v1/auth/csrf`. Login,
logout, reset de contraseña y verificación de correo están implementados con
tokens Django, rate limiting compartido en base de datos y eventos de
auditoría sin PII directa.

No se finge una implementación de 2FA en P05. El enrolamiento TOTP/WebAuthn,
recuperación y requisito obligatorio para roles privilegiados quedan como
frontera explícita para el hardening de seguridad (P23). Mientras tanto,
publicar una revisión requiere el rol `REVIEWER` o `ADMIN`, un editor no puede
publicar, las revisiones publicadas son inmutables, los roles tienen alcance
institucional/programa, cada transición sensible genera `AuditEvent` y los
intentos de autenticación tienen límites transaccionales.

## Alternativas descartadas

- JWT almacenado en `localStorage`: aumenta el impacto de XSS y no es necesario
  para una aplicación first-party.
- Permitir que `EDITOR` publique: rompe separación de funciones.
- Añadir una librería 2FA sin versión/política de recuperación verificada:
  produciría una falsa sensación de seguridad y una migración incompleta.

## Consecuencias y riesgos

- La sesión es adecuada para el frontend first-party y mantiene CSRF explícito.
- Un despliegue institucional con riesgo elevado no debe tratar los controles
  temporales como sustituto permanente de MFA; P23 debe cerrar esta frontera
  antes de habilitar publicación privilegiada sin una política adicional.
- Los eventos de auditoría son append-only a nivel de modelo y trigger
  PostgreSQL; la retención y exportación se mantienen sujetas a la política de
  privacidad del producto.

## Condición de revisión

Revisar este ADR cuando exista un proveedor de identidad institucional o una
dependencia estable de TOTP/WebAuthn con pruebas de enrolamiento, recuperación,
revocación, auditoría y migración de sesiones.
