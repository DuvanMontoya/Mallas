# Requisitos canónicos del producto

Este archivo consolida los requisitos verificables para la revisión final y
apunta a sus especificaciones detalladas. No sustituye los documentos de cada
bounded context ni convierte una inferencia curricular en requisito publicado.

## Funcionales

- [Alcance funcional completo y módulos obligatorios](00_PRODUCT_SCOPE.md)
- [Catálogo completo de funcionalidades](33_FULL_FEATURE_CATALOG.md)
- [Requisitos de aceptación del dominio](acceptance/DOMAIN_ACCEPTANCE.md)
- [Matriz de trazabilidad integral](audit/P25_TRACEABILITY_MATRIX.md)

## No funcionales

- [Requisitos no funcionales](34_NON_FUNCTIONAL_REQUIREMENTS.md)
- [Seguridad y privacidad](17_SECURITY_PRIVACY.md)
- [Matriz de autorización](18_AUTHORIZATION_MATRIX.md)
- [Accesibilidad](26_ACCESSIBILITY.md)
- [Rendimiento](25_PERFORMANCE.md)
- [Observabilidad y operación](20_OBSERVABILITY_OPERATIONS.md)
- [Modelo de eventos y auditabilidad](36_EVENT_MODEL.md)

## Operación y mantenimiento

- [Despliegue, backup y disaster recovery](21_DEPLOYMENT_BACKUP_DR.md)
- [Runbook de despliegue](ops/DEPLOYMENT_RUNBOOK.md)
- [Runbook de backup/restore](ops/BACKUP_RESTORE_RUNBOOK.md)
- [Runbook de mantenimiento de base de datos](ops/DATABASE_MAINTENANCE_RUNBOOK.md)
- [Cadencia de releases](ops/RELEASE_CADENCE.md)
- [Mantenimiento de estado](ops/STATE_MAINTENANCE.md)
- [Respuesta a incidentes](ops/INCIDENT_RESPONSE_RUNBOOK.md)

## Procedencia

Toda afirmación académica debe poder recorrer `Requirement → Evidence →
SourceSnapshot → fuente archivada`, con `UNKNOWN`, `DISPUTED` o
`INFERRED_PENDING_REVIEW` cuando la evidencia sea insuficiente. La fuente y el
baseline actual se registran en [SOURCE_REGISTER.md](research/SOURCE_REGISTER.md)
y la reauditoría más reciente está en
[P90 plan 2514](research/reaudits/2026-08-17-plan-2514.md).

