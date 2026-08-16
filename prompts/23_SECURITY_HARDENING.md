# P23 — Security hardening

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/17_SECURITY_PRIVACY.md`.
4. Lee `docs/18_AUTHORIZATION_MATRIX.md`.

## Skills obligatorias
- carga `security-change`
- carga `feature-delivery`

## Objetivo

Ejecutar threat model de sistema completo y remediar superficies antes de producción.

## Entregables obligatorios

1. Threat model actualizado con trust boundaries.
2. IDOR/BOLA test matrix.
3. CSRF/CORS/CSP/headers review.
4. Session fixation/cookie review.
5. Rate limiting.
6. SSRF hardening source fetch.
7. Upload hardening.
8. Secrets scanning.
9. Dependency audit.
10. SAST.
11. DB privilege review.
12. Audit-log integrity.
13. Admin publication abuse cases.
14. Privacy/logging review.
15. Security runbook.

## Gates de aceptación

- [ ] no Critical/High known
- [ ] negative auth tests
- [ ] SSRF private ranges/redirect bypass tested
- [ ] uploads non-executable and bounded
- [ ] secret scan green
- [ ] reviewer signoff

## Revisión

- Ejecuta subagente `security-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
