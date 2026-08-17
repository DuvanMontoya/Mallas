# P25 — Auditoría integral del sistema

Fecha: 2026-08-17  
Estado: `IN_PROGRESS` — falta evidencia de runtime Docker en este sandbox

## Resultado ejecutivo

La implementación cubre los bounded contexts y los flujos de estudiante,
editor, revisor, analista y operación definidos en el alcance. La
trazabilidad detallada está en
[`P25_TRACEABILITY_MATRIX.md`](P25_TRACEABILITY_MATRIX.md). El código no
contiene TODO/FIXME/HACK/XXX funcionales detectados por el guard de release y
no se encontraron rutas de producción que conviertan el fixture E2E, el mock de
cliente o un valor hardcoded de prueba en fuente de verdad académica.

La auditoría no marca el producto como completamente conforme todavía porque
el entorno administrado niega el ejecutable de Docker y el pipe
`docker_engine`. Esto impide verificar localmente el build final, el scan
Docker Scout, el restore drill contra PostgreSQL y el smoke del Compose. La CI
contiene jobs reproducibles para esos gates; la falta de acceso local no se
presenta como PASS.

## Matriz de gates P25

| Gate | Evidencia | Resultado |
| --- | --- | --- |
| 100% del alcance trazado | `P25_TRACEABILITY_MATRIX.md`, código, tests y ADRs | PASS, salvo filas marcadas `UNKNOWN`/`BLOCKED_EXTERNAL` |
| Sin Critical/High conocidos | threat model, security review, secret scan, pip-audit 2.9.0, `pnpm audit` | PASS; prerrequisitos institucionales externos siguen documentados |
| Sin TODO de alcance | `scripts/check_no_todos.py`; búsqueda productiva manual | PASS |
| Verificación canónica | `scripts/verify.py` pasó con Python 3.14 antes de P24; cambios P24/P25 pasan guards estáticos | PASS histórico + reejecución completa pendiente por sandbox |
| Suite backend | Django/PostgreSQL: 131 passed, 1 skipped en última verificación canónica | PASS histórico; reejecución actual bloqueada por Python/venv |
| Suite frontend | Vitest 33 passed, ESLint y TypeScript PASS en última verificación canónica | PASS histórico; reejecución actual bloqueada por ACL de `node_modules` |
| E2E y accesibilidad | Playwright 50/50 desktop/mobile; axe 20/20 sin violaciones | PASS histórico; reejecución actual bloqueada por ACL de `node_modules` |
| Property/golden tests | `tests/test_rule_engine.py`, golden plan 2514 y Hypothesis en suite canónica | PASS histórico |
| Performance smoke/load | `docs/ops/PERFORMANCE_BASELINE.md`, benchmark y load test de P21 | PASS histórico con límites documentados; nueva medición requiere API/DB |
| OpenAPI freshness | `scripts/check_openapi.py`, generated client, breaking diff self-check | PASS histórico; `check_openapi_breaking.py` reejecutado PASS |
| Migración desde vacío | `migrate`, `migrate --check`, `makemigrations --check --dry-run` en CI/suite PostgreSQL | PASS histórico; gate CI conservado |
| Migración desde estado previo | migraciones versionadas y suite PostgreSQL existente | PASS histórico; no hay migración pendiente registrada |
| Backup/restore | scripts atómicos y job `restore-drill` en `.github/workflows/production-gates.yml` | BLOCKED_EXTERNAL para ejecución local; no se marca verde |
| Production smoke | `scripts/smoke.py`, P22 smoke real 200/ETag/OpenAPI/Web | PASS histórico; smoke Compose nuevo requiere Docker |
| Docs clone-clean | `scripts/verify_docs_clone_clean.py` | PASS reejecutado 2026-08-17 |
| Evidencia curricular | fuente/evidence lineage y estados epistemológicos | `UNKNOWN`/`INFERRED_PENDING_REVIEW` donde falta snapshot normativo oficial |

## Búsqueda de implementación incompleta

- `scripts/check_no_todos.py`: sin hits funcionales.
- `scripts/scan_secrets.py`: sin secretos de alta confianza.
- Los `vi.mock`, `Mock` y fixtures están confinados a tests; no se importan
  desde el runtime de producción.
- Los `return None`, `return []` y `pass` revisados son ramas de ausencia,
  manejo tolerante de telemetría opcional o valores epistemológicos; no son
  endpoints placeholder. Los módulos tienen tests de sus ramas relevantes.
- No hay `NotImplementedError` en el código de producto auditado.

## Revisiones

Los reviewers especializados solicitados por el prompt no están expuestos en
esta sesión. Se hizo una revisión read-only equivalente por dominios:

- arquitectura: bounded contexts, separación domain/application/infrastructure,
  OpenAPI y no autoridad del frontend/LLM;
- código: errores, idempotencia, concurrencia, tipos, migraciones y tests;
- seguridad: SSRF, IDOR/BOLA, sesiones, uploads, rate limits, audit log,
  secrets, SAST y supply chain;
- currículo: estados epistemológicos, evidencia, no doble conteo, revisión
  publicada inmutable y ausencia de reglas inventadas;
- UX: flujos críticos, teclado, foco, responsive, reduced motion, axe y
  alternativas textuales del grafo.

No se inventa un sign-off de subagente; la limitación está en el estado del
proyecto.

## Correcciones P25

- Añadida la matriz de trazabilidad completa del alcance.
- Añadido `scripts/verify_docs_clone_clean.py` y conectado a la verificación
  canónica para comprobar que un checkout limpio conserva los entry points y
  no contiene enlaces relativos rotos o rutas de máquina.
- Añadida esta auditoría con clasificación explícita de evidencia histórica,
  reejecutada y bloqueada.

## Cierre requerido

Para pasar a `done` faltan únicamente verificaciones ejecutables que no pueden
simularse en este sandbox:

1. construir API/web con Docker y comprobar usuarios no root/healthchecks;
2. ejecutar Docker Scout y obtener cero vulnerabilidades `Critical`;
3. ejecutar migración y smoke dentro del stack Compose;
4. crear un backup PostgreSQL y completar `restore_drill.py`, verificando que
   la base temporal se elimina;
5. repetir la suite canónica, lint, typecheck, build y E2E después de esos
   cambios y registrar el resultado.

El siguiente intento debe comenzar habilitando acceso al Docker Engine o
ejecutando la misma evidencia en la CI de `production-gates.yml`; luego se
actualizan esta matriz, `.codex/STATUS.md`, `CURRENT_STATE.md` y el roadmap.
