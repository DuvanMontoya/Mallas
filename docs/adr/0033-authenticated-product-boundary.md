# ADR-0033 — Superficie de producto autenticada por defecto

## Estado

Aceptada — 2026-08-21

## Contexto

La aplicación exponía pantallas de malla, dependencias, oferta y evidencia sin
una sesión validada. Varias lecturas de API y los capability links de
planificación también podían responder de forma anónima. Esto contradice la
expectativa de una plataforma académica completamente privada y aumenta la
superficie de enumeración de datos institucionales.

## Decisión

1. Todas las páginas de producto pasan por un guard servidor que valida la
   sesión Django y falla cerrado; `proxy.ts` redirige de forma temprana cuando
   ni siquiera existe la cookie de sesión.
2. Todas las lecturas de currículo, grafo, oferta, secciones, reuniones y
   definiciones analíticas exigen `django_auth`; las respuestas autenticadas se
   marcan `Cache-Control: private, no-store`.
3. La vista de escenario por token conserva su contrato redacted únicamente
   como compatibilidad, pero exige sesión y autorización owner/advisor. La UI
   deja de crear enlaces externos.
4. La especificación OpenAPI y la UI de documentación no se publican por HTTP;
   el contrato se genera localmente desde la instancia Ninja y se archiva.
5. Login, recuperación/verificación de cuenta y health operativo son las
   únicas superficies sin sesión, cada una con controles específicos.

## Consecuencias

- Una cookie falsa, vencida o una identidad no verificable nunca habilitan el
  render de una pantalla de producto.
- La autenticación es necesaria pero no suficiente para datos de otra persona:
  se conservan ownership, advisor assignment y RBAC del backend.
- Los clientes que dependían de OpenAPI HTTP o de enlaces públicos deben usar
  el artefacto versionado o iniciar sesión, respectivamente.
