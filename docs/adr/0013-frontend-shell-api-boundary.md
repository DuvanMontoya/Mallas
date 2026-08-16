# ADR-0013 — Frontend shell and typed API boundary

**Estado:** ACCEPTED

## Decisión

El App Router usa un shell de producto común para las vistas de workspace y un
auth shell para `/login`. El layout raíz obtiene la sesión con
`getSessionSnapshot`, reenvía la cookie sólo al backend configurado y pasa al
shell un snapshot serializable. Los Client Components se limitan a navegación,
tema, login, popovers y estado efímero.

Toda comunicación HTTP vive en `apps/web/lib/api.ts` y consume el paquete
`@curriculum-navigator/api-client`, generado desde OpenAPI. Los componentes no
construyen URLs ni llaman `fetch` directamente. CSRF se obtiene por el endpoint
oficial y se envía como `X-CSRFToken`; los errores conservan el `code` y el
`correlation_id` del contrato.

## Consecuencias

- El build puede ejecutarse sin backend: la capa de sesión degrada a estado
  `unavailable` sin inventar datos académicos.
- El shell es responsive y comparte navegación, loading, error, empty state,
  tema e internacionalización preparada.
- Los componentes del design system son presentacionales: reciben hechos y
  estados, pero no deciden elegibilidad ni graduación.
- La cookie y cualquier dato de sesión no se refleja en URL; sólo filtros y
  selección no sensibles usan el patrón `useWorkspaceUrlState`.
