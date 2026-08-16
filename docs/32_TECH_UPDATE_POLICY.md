# 32 — Política de actualización tecnológica

## Dependency resolution

No guardar «latest» como versión de producción. El agente resuelve latest estable durante la tarea y luego fija versión exacta/lockfile.

## Renovate

Configurar:
- patch/minor agrupables cuando riesgo bajo;
- major en PR separado;
- automerge sólo para cambios de riesgo bajo con suite verde y política explícita;
- frameworks core nunca se auto-publican a producción sin verificación.

## Framework upgrades

Checklist:
1. official release notes;
2. security advisories;
3. compatibility matrix;
4. codemod dry run;
5. upgrade branch;
6. unit/integration/e2e;
7. performance smoke;
8. reviewer;
9. ADR si cambia arquitectura.

## Canary/RC

No producción por defecto. Se pueden ejecutar en CI experimental para anticipar migraciones.
