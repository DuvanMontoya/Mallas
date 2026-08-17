# Riesgos vivos

| Riesgo | Severidad | Mitigación |
|---|---|---|
| Interpretar una celda ambigua como requisito oficial | Critical | estado UNKNOWN + revisión humana |
| Mezclar malla sugerida con norma | High | `CurriculumLayout` separado |
| Doble conteo de créditos | High | CreditAllocation explícito + property tests |
| LLM publica cambios incorrectos | Critical | workflow sin auto-publish |
| Dependencias framework cambian | Medium | version policy + official docs |
| Oferta académica desactualizada | High | source timestamp + freshness |
| Historia PDF extraída mal | High | preview/confirmation/idempotencia |
| Sobrearquitectura | Medium | monolito modular, ADR gates |
| Regla duplicada en frontend | High | backend authority + contract tests |

## Riesgos operativos añadidos — 2026-08-17

| Riesgo | Severidad | Mitigación / evidencia |
|---|---|---|
| Docker CLI/socket no accesible en la estación de ejecución | Critical para release | P24 documenta el bloqueo; repetir build, scan, backup, restore y smoke en runner autorizado; no marcar P24 `done` antes del resultado |
| Python 3.14/venv/uv inaccesibles y runtime bundled sin Django | Critical para gates backend | Ejecutar `scripts/verify.py`, migraciones y tests en runner Python 3.14 real; no confundir `py_compile` 3.12 con validación Django |
| Archivos existentes de `node_modules` bloqueados con `EPERM` | High para release frontend | Reparar instalación/ACL o reinstalar con pnpm en runner autorizado; repetir lint, typecheck, Vitest, build, E2E y axe |
| Registry npm/red no disponible | High para mantenimiento | Resolver versión Next y lockfile con acceso al registry; no editar lockfile a mano ni aplicar downgrade ciego |
| Source watch remoto no puede confirmar fuentes | High para procedencia | Mantener `UNKNOWN`/`ERROR`, archivar snapshots oficiales y ejecutar watcher en red autorizada; nunca autopublicar |
| Fuentes normativas remotas sin archivo íntegro | Critical para publicación curricular | Revisión humana y archivo/evidencia verificable; no mutar `PUBLISHED` ni convertir observaciones en reglas |
| Reviewers especializados, screen reader y dispositivo físico no expuestos | Medium/High para sign-off | Completar revisión independiente y checklist manual antes de release; conservar auditoría manual como evidencia parcial |
| Estado `.codex/STATUS.md` no editable por ACL de la sesión | Medium para continuidad | Usar `docs/state/CURRENT_STATE.md`, `SESSION_LOG.md`, `ROADMAP_STATUS.json` e informes auditables; actualizar `.codex/STATUS.md` en una sesión con permiso |
