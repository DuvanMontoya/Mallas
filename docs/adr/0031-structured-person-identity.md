# ADR 0031 — Identidad personal estructurada separada del perfil estudiantil

## Estado

Aceptada — 2026-08-19

## Contexto

`StudentProfile.display_name` mezclaba identidad civil, presentación y datos
académicos en una cadena opaca. No permitía búsquedas controladas por nombres y
apellidos ni registrar fecha de nacimiento sin guardar también una edad que se
volvería obsoleta. Separar cadenas históricas por espacios sería una inferencia
destructiva e incorrecta para nombres compuestos.

## Decisión

1. `identity.PersonProfile` es 1:1 con `identity.User` y posee primer nombre,
   otros nombres, primer apellido, segundo apellido, nombre preferido y fecha
   de nacimiento. `User` conserva autenticación; `StudentProfile` conserva
   institución, número estudiantil y metadata académica.
2. La edad nunca se persiste. `age_on(fecha)` la deriva de `birth_date` con
   aritmética calendaria y puede devolver `None`.
3. La fecha de nacimiento exige propósito explícito
   `ACADEMIC_ADMINISTRATION`. Es privada, no entra en telemetría, eventos de
   auditoría ni vistas públicas. Una fecha de retención concreta puede quedar
   nula mientras la persona tenga relación académica activa; el proceso de
   retención institucional debe fijarla al cerrar esa relación antes del gate
   de release.
4. Un perfil `CONFIRMED` requiere primer nombre y primer apellido. Los campos
   se normalizan eliminando espacios redundantes, pero nunca se transliteran ni
   se recomponen heurísticamente. `verification_method` distingue declaración
   propia, verificación institucional, origen preexistente no clasificable y
   origen legacy desconocido; constraints de base preservan los invariantes
   representables fuera de `save()`. La migración deriva el método sólo desde
   eventos de rectificación inequívocos y conserva lo demás como no clasificado.
5. La migración renombra el valor histórico a
   `StudentProfile.legacy_display_name` y crea `PersonProfile` vacío con estado
   `LEGACY_UNSTRUCTURED`. El nombre histórico sólo sirve como fallback visible
   hasta que una persona autorizada confirme los campos. La migración inversa
   elimina únicamente placeholders del backfill que permanezcan intactos;
   conserva cualquier perfil rectificado para no destruir identidad adquirida.
6. El alta administrativa recibe campos estructurados, crea el perfil
   `CONFIRMED` en la misma transacción y deriva `display_name` para respuesta.
   Búsqueda y orden usan columnas estructuradas, con fallback legacy.
7. La persona puede leer, rectificar y exportar su identidad mediante una
   superficie self-service con sesión, CSRF e `If-Match`. Administradores
   institucionales con alcance pueden rectificarla en el flujo académico. Los
   asesores no reciben fecha de nacimiento en P101. La política de retención y
   supresión está definida en `docs/17_SECURITY_PRIVACY.md`; los plazos legales
   concretos y el proceso operativo de vencimiento son un gate de release
   institucional, no una fecha inventada por P101.
8. Las colecciones administrativas son proyecciones minimizadas. La fecha de
   nacimiento sólo se obtiene al abrir el detalle privado de una persona; ese
   acceso es auditado y no cacheable. La edición bloquea `User` y
   `PersonProfile` explícitamente para serializar self-service y administración.
   El detalle requiere MFA privilegiado en producción y rate limit de lectura;
   self-service no puede degradar ni sustituir una identidad institucional.

## Consecuencias

- Se pueden distinguir nombres y apellidos sin perder variantes culturales.
- No existe una columna de edad que requiera sincronización.
- Los datos legacy no aparentan precisión que no tienen.
- Cambios de nombres y fecha de nacimiento requieren eventos auditables y una
  política de rectificación; no se habilita edición directa en Django admin.
- Las consultas que muestran nombres deben cargar `user__person_profile` para
  evitar N+1 y mantener el fallback histórico.

## Rechazado

- Dividir `display_name` automáticamente por el último espacio.
- Reusar `User.first_name`/`last_name`, que no modelan nombres múltiples ni la
  política privada requerida.
- Persistir edad.
- Copiar fecha de nacimiento en `StudentProfile`, auditoría, analytics o
  eventos de observabilidad.
