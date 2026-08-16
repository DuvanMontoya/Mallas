# P24 — CI/CD, despliegue, backup y DR

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/21_DEPLOYMENT_BACKUP_DR.md`.
4. Lee `docs/20_OBSERVABILITY_OPERATIONS.md`.

## Skills obligatorias
- carga `release`
- carga `db-migration`
- carga `security-change`

## Objetivo

Crear ruta de producción reproducible con containers, CI gates, migrations, backups y restore drills.

## Entregables obligatorios

1. Production Dockerfiles non-root/multi-stage.
2. Compose dev y production reference sin secretos.
3. Reverse proxy config reference.
4. CI full pipeline.
5. Build artifacts/images pinned.
6. Migration gate.
7. Backup script/runbook.
8. Restore drill automatizable.
9. Smoke tests.
10. Rollback runbook.
11. Environment config matrix.
12. Deployment docs desde servidor limpio.
13. Separate object storage strategy.

## Gates de aceptación

- [ ] restore drill exitoso
- [ ] image scan sin critical
- [ ] migration dry-run
- [ ] smoke green
- [ ] no secret baked in images
- [ ] rollback documented

## Revisión

- Ejecuta subagente `security-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
