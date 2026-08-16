# P08 — Foundation frontend y design system

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/12_UX_INFORMATION_ARCHITECTURE.md`.
4. Lee `docs/13_DESIGN_SYSTEM.md`.
4. Lee `docs/15_FRONTEND_ARCHITECTURE.md`.
4. Lee `docs/26_ACCESSIBILITY.md`.

## Skills obligatorias
- carga `feature-delivery`

## Objetivo

Construir shell de producto y design system de alta calidad, responsive y accesible, conectado al cliente API real.

## Entregables obligatorios

1. Configurar routing y layouts por roles.
2. Implementar navegación principal, error boundaries, loading states, auth shell.
3. Crear tokens de diseño semánticos y temas accesibles.
4. Implementar primitives y componentes base descritos en design system.
5. Configurar i18n preparada.
6. Configurar Testing Library/Vitest/axe.
7. Configurar Playwright.
8. Conectar generated API client, no fetches dispersos.
9. Crear mocks sólo en tests/Storybook, nunca como datos productivos.
10. Responsive mobile/desktop.
11. Establecer patrón de URL state.

## Gates de aceptación

- [ ] teclado completo en shell
- [ ] axe sin violaciones serias en componentes base
- [ ] no hardcoded domain eligibility
- [ ] loading/error/empty consistentes
- [ ] mobile usable
- [ ] tests verdes

## Revisión

- Ejecuta subagente `ux-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
