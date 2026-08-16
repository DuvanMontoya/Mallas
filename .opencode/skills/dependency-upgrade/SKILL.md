---
name: dependency-upgrade
description: Actualiza frameworks/librerías sin adivinar versiones: documentación oficial, compatibilidad, codemods, tests, lockfiles y rollback.
---

# Dependency upgrade

1. Inspecciona versión instalada y lockfile.
2. Consulta registry oficial + documentación oficial.
3. Confirma stable vs preview/rc/canary.
4. Lee breaking changes y advisories.
5. Verifica compatibilidad peers/runtime.
6. Crea plan de migración.
7. Usa codemod dry-run si existe.
8. Actualiza versión exacta/lockfile.
9. Corrige deprecations sin silenciarlas.
10. Ejecuta unit/integration/e2e.
11. Smoke performance.
12. reviewer.
13. Actualiza TECH baseline/ADR si cambia arquitectura.
14. Nunca saltar a prerelease de producción por «ser más nuevo».
