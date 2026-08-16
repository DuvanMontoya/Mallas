# P05 — Identidad, auth, RBAC y audit log

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/17_SECURITY_PRIVACY.md`.
4. Lee `docs/18_AUTHORIZATION_MATRIX.md`.

## Skills obligatorias
- carga `feature-delivery`
- carga `security-change`
- carga `db-migration`

## Objetivo

Implementar autenticación y autorización de producción con ownership, roles, sesiones seguras y auditoría administrativa.

## Entregables obligatorios

1. Definir user model si aún es seguro hacerlo al inicio.
2. Implementar StudentProfile y roles/assignments sin mezclar identidad con programa.
3. Elegir estrategia de sesión para web first-party y documentarla.
4. Implementar login/logout/password reset/verification según alcance real.
5. RBAC + object ownership.
6. Separación Editor/Reviewer.
7. AuditEvent append-oriented para cambios sensibles.
8. Protecciones CSRF/CORS/CSP/secure cookies en settings por entorno.
9. Rate limits en auth/sensitive endpoints mediante solución compatible.
10. Tests negativos IDOR/privilege escalation.
11. Política de secrets y configuración.
12. Preparar 2FA para roles privilegiados si dependencia estable/arquitectura lo permite; si no, dejar una decisión explícita no fingida y proteger publicación por controles equivalentes temporales.

## Gates de aceptación

- [ ] estudiante no accede historia ajena
- [ ] editor no puede publicar si rol no lo permite
- [ ] reviewer no edita published revision
- [ ] sesiones seguras en producción
- [ ] security tests negativos
- [ ] audit events creados
- [ ] no secrets en repo

## Revisión

- Ejecuta subagente `security-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
