# Cadencia de release y mantenimiento

## Cadencia de referencia

| Periodicidad | Actividad | Gate |
| --- | --- | --- |
| Cada PR | tests, OpenAPI, migraciones, lint/typecheck, secret/SAST y dependency review | checks obligatorios en branch protection |
| Semanal | dependency check, source freshness, security advisories, smoke y revisión de estado | fallos bloquean promoción |
| Mensual | restore drill, backup más antiguo en retención, axe/Playwright y revisión de threat model | evidencia de recuperación y accesibilidad |
| Trimestral | revisión de ADRs, tecnología, permisos mínimos, RPO/RTO y fuentes normativas | aprobación de arquitectura/seguridad/gobierno |
| Antes de release | baseline oficial, impacto curricular, migración, backup, image scan, smoke y rollback rehearsal | release manifest con digests |

## Dependencias

Renovate abre PRs con versiones exactas y digest pins. No hace merge ni
publica automáticamente: patch/minor agrupables siguen necesitando todos los
checks verdes y aprobación humana; majors, Django/Next/React, imágenes base y
lockfiles críticos requieren PR separado y revisión de release notes.

## Cambios normativos

Los jobs de vigilancia sólo producen reportes. Un cambio de una fuente crea un
snapshot, diff y propuesta nueva. Nunca se ejecuta un auto-publish por un
workflow de dependencia, watcher, extracción LLM o merge de código.
La política de los jobs es `no auto-publish`.

## Recuperación

La secuencia de una release es:

`build → tests → dependency/security scan → migration check → backup →
restore-drill gate → promote digest → migrate → deploy → smoke → monitor →
rollback si hace falta`.

El detalle operativo está en `DEPLOYMENT_RUNBOOK.md`,
`BACKUP_RESTORE_RUNBOOK.md`, `DATABASE_MAINTENANCE_RUNBOOK.md` y
`ROLLBACK_RUNBOOK.md`.
