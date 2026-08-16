# Actualización segura de dependencias

Carga `dependency-upgrade`.

No ejecutes un update global ciego.

1. Inventaría versiones y lockfiles.
2. Consulta documentación/release notes oficiales de cada core dependency.
3. Prioriza security patches.
4. Separa major/core framework upgrades.
5. Confirma stable tags.
6. Ejecuta codemods dry run.
7. Actualiza.
8. Corrige deprecations.
9. Unit + integration + E2E + accessibility + performance smoke.
10. Revisa OpenAPI.
11. architecture/code/security reviewer según alcance.
12. Actualiza Technology Baseline y ADR si aplica.
13. No push.
