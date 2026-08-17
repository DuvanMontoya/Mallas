# ADR-0028: mantenimiento continuo sin publicación automática

## Estado

Accepted — 2026-08-17

## Contexto

Dependencias, fuentes normativas, reglas desconocidas, estadísticas de base y
estado operativo cambian después de una release. Confiar en memoria humana o
en una extracción LLM puede convertir una alerta en una regla publicada sin
evidencia. El producto necesita reportes repetibles y gates que recuperen el
estado del repositorio desde un checkout limpio.

## Decisión

- Renovate abre PRs con versiones y digest pins exactos; no hace automerge ni
  publica cambios normativos.
- Workflows separados ejecutan advisories/dependency checks, source freshness y
  auditorías periódicas de seguridad/accesibilidad.
- `scripts/source_freshness.py` sólo observa URLs HTTPS allowlisted y produce
  un artifact; el workflow nunca crea snapshots ni cambia una revisión.
- `unknown_rule_queue` exporta requisitos `UNKNOWN`,
  `INFERRED_PENDING_REVIEW` y `DISPUTED` con `HUMAN_REVIEW_REQUIRED` y
  `publish_blocker`, sin escritura académica.
- `update_technology_baseline.py` extrae pins de manifests/lockfiles y exige
  una revisión oficial separada para actualizar la baseline narrativa.
- `db_maintenance` limita el mantenimiento a migración preflight y
  `VACUUM (ANALYZE)`/`ANALYZE` explícito; no acepta SQL o tablas de entrada.
- `verify_state_recovery.py` comprueba la memoria durable del agente y no
  modifica estados.

## Consecuencias

Los cambios de dependencias y fuentes son visibles y bloqueables, pero un
operador debe revisar y promoverlos. Un job sin red produce `UNKNOWN`/`ERROR`,
no una falsa confirmación. La operación requiere conservar artifacts de
freshness, advisories, restore drills y state-recovery como evidencia.
