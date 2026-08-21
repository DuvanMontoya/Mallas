# 18 — Roles y autorización

| Acción | Student | Advisor | Editor | Reviewer | Analyst | Admin |
|---|---:|---:|---:|---:|---:|---:|
| Ver currículo autenticado | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Ver propia historia | ✓ | | | | | ✓* |
| Editar propia historia manual | ✓ | | | | | ✓* |
| Ver estudiante asignado | | ✓ | | | | ✓ |
| Crear draft curricular | | | ✓ | ✓ | | ✓ |
| Editar draft | | | ✓ | ✓ | | ✓ |
| Aprobar/publicar | | | | ✓ | | ✓ |
| Editar revisión publicada | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Analítica agregada institucional | | | | | ✓ | ✓ |
| Analítica estudiantil propia/asignada | ✓ | ✓* | | | | ✓* |
| Ver PII analítica | | | | | ✗ | ✗ |
| Ver/rectificar identidad propia | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Exportar identidad propia | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Ver/rectificar identidad estudiantil | | | | | | ✓* |
| Enviar política de asignación a revisión | | | ✓* | | | ✓* |
| Publicar política de asignación | | | | ✓* | | ✓* |
| Preparar excepción de asignación | | | | | | ✓* |
| Aprobar/aplicar excepción de asignación | | | | | | ✓* |
| Alta, reingreso o transición de matrícula | | | | | | ✓* |

`✓*` no significa acceso arbitrario; debe auditarse y justificarse.

La rectificación propia se limita siempre al `User` de la sesión. La
rectificación administrativa requiere alcance institucional y de programa
vigente; un UUID de matrícula nunca concede acceso por sí mismo. Asesores no
reciben fecha de nacimiento en P101: cualquier necesidad posterior exige
propósito, delegación y una nueva revisión de privacidad.

## Separación de funciones

En producción institucional, editor y reviewer deben ser personas distintas para publicación ordinaria.
La política de asignación sólo puede ser enviada por su preparador y publicada
por otra persona. Una excepción curricular exige también preparador y aprobador
distintos; publicación, aprobación y aplicación requieren MFA privilegiado y
alcance vigente sobre la matrícula/programa.

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

`ANALYST` y `ADMIN` son los únicos roles que habilitan la vista institucional
de P18/P19. El acceso de `ADVISOR` queda limitado a la analítica privada de un
estudiante con asignación vigente, nunca al agregado institucional. La
implementación institucional no devuelve PII a ningún rol y aplica supresión
de celdas pequeñas; una necesidad futura de PII analítica requiere una nueva
decisión de gobernanza.

## Hardening P23

Las operaciones mutables quedan además cubiertas por un límite compartido en
base de datos, y los UUID nunca sustituyen las comprobaciones de ownership,
institución, programa y vigencia. La publicación requiere una sesión
first-party protegida, rol `REVIEWER`/`ADMIN`, estado `APPROVED`, versión ETag,
confirmación explícita y una persona distinta de quien creó la propuesta.

En producción institucional, la asignación de `REVIEWER` o `ADMIN` debe estar
condicionada al MFA/IdP institucional. El backend no acepta un header de MFA
del navegador como prueba de identidad; si el despliegue no puede imponer la
política del IdP, esos roles permanecen deshabilitados.
