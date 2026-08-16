# 18 — Roles y autorización

| Acción | Student | Advisor | Editor | Reviewer | Analyst | Admin |
|---|---:|---:|---:|---:|---:|---:|
| Ver currículo público | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Ver propia historia | ✓ | | | | | ✓* |
| Editar propia historia manual | ✓ | | | | | ✓* |
| Ver estudiante asignado | | ✓ | | | | ✓ |
| Crear draft curricular | | | ✓ | ✓ | | ✓ |
| Editar draft | | | ✓ | ✓ | | ✓ |
| Aprobar/publicar | | | | ✓ | | ✓ |
| Editar revisión publicada | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Analítica agregada | | limitada | | | ✓ | ✓ |
| Ver PII analítica | | según rol | | | sólo si necesario | ✓ |

`✓*` no significa acceso arbitrario; debe auditarse y justificarse.

## Separación de funciones

En producción institucional, editor y reviewer deben ser personas distintas para publicación ordinaria.

## Enforcement P05

Las decisiones anteriores se ejecutan en
`modules.identity.application.authorization`. La propiedad directa se
comprueba por `StudentProfile.user_id`; el acceso de asesor requiere tanto rol
`ADVISOR` como `StudentAdvisorAssignment` vigente. Los roles institucionales y
de programa se filtran por alcance y vigencia, y `ADMIN` sólo aparece de forma
implícita para superusuarios o mediante una asignación explícita.

`can_publish_revision` nunca acepta sólo `EDITOR`, mientras que
`can_edit_revision` devuelve falso para `PUBLISHED`, `SUPERSEDED` y `RETIRED`.
Los servicios de ciclo de vida aceptan el actor y generan `AuditEvent` cuando
se invocan desde un flujo autorizado; las rutas de acceso sensibles no
reciben decisiones de ownership desde el cliente.
