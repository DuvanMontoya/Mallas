# Mantenimiento de estado y memoria operativa

El repositorio es la memoria durable del proyecto. Ningún agente debe
depender de una conversación anterior para reanudar trabajo.

## Archivos de recuperación

- `AGENTS.md`: constitución, invariantes y Definition of Done;
- `.codex/STATUS.md`: cierre por milestone, pruebas y problemas;
- `docs/state/CURRENT_STATE.md`: snapshot operativo, siguiente acción y
  comandos de reanudación;
- `docs/state/ROADMAP_STATUS.json`: estados, dependencias, prompts y evidencia;
- `docs/state/OPEN_DECISIONS.md`: decisiones que requieren dirección humana;
- `docs/state/SESSION_LOG.md`: historial de verificaciones y riesgos.

## Check automatizable

```powershell
python scripts/verify_state_recovery.py
python scripts/verify_state_recovery.py --output var/reports/state-recovery.json
```

El check valida que los archivos existan, que el roadmap sea JSON válido, que
cada prompt referenciado exista, que no haya IDs duplicados, que los estados
sean conocidos y que el snapshot actual exponga problemas pendientes, acción
siguiente y comandos. No modifica el roadmap ni marca fases como terminadas.

## Regla de cierre

Al cerrar una sesión se actualizan `CURRENT_STATE.md`, `ROADMAP_STATUS.json`,
`SESSION_LOG.md` y `.codex/STATUS.md`. Una fase sólo puede ser `done` cuando
su evidencia ejecutable está registrada y no tiene un TODO de alcance. Las
decisiones normativas siguen requiriendo revisión humana y evidencia oficial.
