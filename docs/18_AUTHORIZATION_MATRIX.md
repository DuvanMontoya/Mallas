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
