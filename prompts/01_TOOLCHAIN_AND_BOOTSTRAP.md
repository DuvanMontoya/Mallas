# P00 — Toolchain y bootstrap

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/03_REPOSITORY_STRUCTURE.md`.
4. Lee `docs/research/TECHNOLOGY_BASELINE.md`.
4. Lee `docs/19_TEST_STRATEGY.md`.
4. Lee `docs/21_DEPLOYMENT_BACKUP_DR.md`.

## Skills obligatorias
- carga `dependency-upgrade`
- carga `feature-delivery`

## Objetivo

Convertir este kit de especificación en un repositorio ejecutable, reproducible y versionado sin adivinar versiones ni usar prereleases como producción.

## Entregables obligatorios

1. Verificar versiones oficiales actuales de codex, gpt integration, Python, Django, Next, Node, pnpm, uv, PostgreSQL y librerías núcleo.
2. Resolver Django: 6.1 final sólo si existe oficialmente; de lo contrario última 6.0.x estable. Registrar evidencia de la decisión.
3. Resolver Next con `next@latest` estable y documentación version-matched; no preview/canary.
4. Crear `apps/api` Django y `apps/web` Next con configuración estricta.
5. Crear PostgreSQL local en Compose con healthcheck y volumen de desarrollo.
6. Configurar Python tooling, TypeScript strict, lint, format, tests y comandos consistentes.
7. Crear/ajustar `package.json`, workspace pnpm, `pyproject.toml`, lockfiles y version files.
8. Configurar CI inicial que ejecute curriculum validation, backend y frontend checks.
9. Configurar Renovate con política prudente.
10. Expandir `scripts/verify.py` como comando canónico.
11. Actualizar README con setup desde clone limpio y comandos exactos.
12. No implementar aún lógica académica improvisada durante el scaffold.

## Gates de aceptación

- [ ] clone/checkout limpio puede instalar dependencias siguiendo README
- [ ] DB local arranca y Django conecta
- [ ] Next arranca
- [ ] health endpoints mínimos funcionan
- [ ] lint/typecheck/tests verdes
- [ ] lockfiles presentes
- [ ] no prereleases core salvo CI experimental explícita
- [ ] verify pasa

## Notas específicas

Si codex actual usa sintaxis V2, migra `codex.json` preservando seguridad. No debilites `git push: deny`.

## Revisión

- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
