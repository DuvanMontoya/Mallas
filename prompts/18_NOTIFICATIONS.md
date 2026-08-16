# P17 — Notificaciones

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/28_NOTIFICATION_SYSTEM.md`.
4. Lee `docs/17_SECURITY_PRIVACY.md`.

## Skills obligatorias
- carga `feature-delivery`

## Objetivo

Implementar notificaciones in-app y arquitectura de canales opcionales con deduplicación, preferencias y eventos confiables.

## Entregables obligatorios

1. NotificationEvent/Delivery/Preference.
2. Outbox or transactional event pattern apropiado al monolito.
3. In-app center.
4. Email adapter opcional.
5. Dedup/idempotency.
6. Read/unread.
7. User preferences.
8. No enviar draft changes.
9. Templates localizables.
10. Privacy-safe content.

## Gates de aceptación

- [ ] no duplicate notifications on retry
- [ ] publication event after commit
- [ ] preferences respected
- [ ] no sensitive detail in insecure channel
- [ ] tests green

## Revisión

- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `security-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `ux-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
