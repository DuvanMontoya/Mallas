# P98 — Auditoría anti-MVP y completitud

**Fecha:** 2026-08-17  
**Alcance:** `docs/00_PRODUCT_SCOPE.md`, `docs/33_FULL_FEATURE_CATALOG.md`,
`docs/41_ACCEPTANCE_GATES_MATRIX.md`, `docs/SPEC.md`,
`docs/REQUIREMENTS.md`, `docs/ACCEPTANCE.md` y el checkout completo.  
**Veredicto:** no se encontraron capacidades funcionales `MISSING` ni una
reducción MVP oculta en el código de producto. Sí quedan gates
`BLOCKED_EXTERNAL` de ejecución y un upgrade de dependencias que no puede
regenerarse con el registro inaccesible; el producto no se declara `READY`.

## Matriz de módulos obligatorios

| Módulo de `PRODUCT_SCOPE` | Implementación | Pruebas/documentación | Estado anti-MVP |
|---|---|---|---|
| Catálogo y currículo versionado | `modules.institutions`, `curriculum`, revisiones y migraciones | dominio, ingestión, invariantes, ADR-0004 | COMPLETE |
| Motor de requisitos | AST/evaluator/graph Python puro | unit, golden, Hypothesis, round-trip, ciclos | COMPLETE |
| Auditoría de grado | ledger, allocation, snapshot, explanations | audit service, golden 2514, API/UI/E2E | COMPLETE |
| Historia académica | import privado, reconciliación, reconocimientos/excepciones | history/security/API tests | COMPLETE |
| Malla interactiva | map read model, filtros, ficha, print | backend/frontend/E2E/axe | COMPLETE |
| Grafo | proyección semántica, foco, paths, textual alternative | graph tests, E2E keyboard/axe | COMPLETE |
| Oferta/secciones/horarios | términos, snapshots, importer, conflicts | offerings/planning/E2E | COMPLETE; fuente externa real permanece UNKNOWN cuando no hay snapshot |
| Planner | escenarios privados, drag/drop y alternativa keyboard | planning/frontend/E2E | COMPLETE |
| Optimizer | CP-SAT, estados, límites, explicación y persistencia | solver/API/property/performance/E2E | COMPLETE |
| Requisitos no crediticios | external requirement, B1 separado de créditos | audit/golden/UI | COMPLETE; evidencia individual puede ser UNKNOWN |
| Equivalencias/homologaciones/excepciones | recognition ledger y excepciones auditables | history/audit tests | COMPLETE |
| Importadores | baseline/source/history, preview, idempotencia, quarantine | imports/security tests | COMPLETE |
| Backoffice editorial | snapshots, candidates, AST, diff, evidence, validation | governance tests/UI/E2E | COMPLETE |
| Revisión/publicación/impacto | state machine, immutable revision, impact/outbox | publication/notification tests/E2E | COMPLETE |
| Notificaciones/alertas | event/delivery/preferences/outbox/in-app | notification tests/UI/E2E | COMPLETE |
| Analítica estudiante | read-only persisted audit analytics | analytics tests/UI/E2E | COMPLETE |
| Analítica institucional | aggregate privacy threshold, HMAC/export | analytics role/suppression tests | COMPLETE |
| Authz/auditoría | sessions, CSRF, RBAC, audit event and trigger | identity/security tests | COMPLETE; MFA/IdP remain external prerequisite |
| Observabilidad | logs, traces, metrics, health, frontend adapter | observability/health/smoke/runbooks | COMPLETE |
| Backups/DR | atomic backup, isolated restore drill, Compose/runbooks | static/CI jobs | BLOCKED_EXTERNAL: Docker Engine local inaccessible |
| CI/CD/dependencies | workflows, immutable images, Renovate, audits | static deployment checks/CI definitions | BLOCKED_EXTERNAL: CI not executable here; Next stable downgrade lock resolution pending |
| Documentación | specs, requirements, acceptance, ADRs, runbooks | docs clone-clean/state recovery/OpenAPI | COMPLETE |
| Multi-programa/multi-sede | FK-scoped schema and generic AST | P94 synthetic isolation/round-trip test | BLOCKED_EXTERNAL: new test not runnable with Python runtime |
| i18n preparada | catalogs, locale preferences, locale-aware text | frontend tests/typecheck/E2E histórico | COMPLETE; screen-reader manual run external |

## Señales MVP buscadas y resultado

| Señal | Comprobación | Resultado |
|---|---|---|
| `TODO/FIXME/HACK/XXX` funcional | `scripts/check_no_todos.py` (`files_scanned=508`, `functional_hits=0`, `TODO_RELEASE_GATE=PASS`) + clasificación de hits | No hay hit funcional; todas las referencias no funcionales quedan clasificadas como guard, docs, prompts o metadata |
| `pass`/stub/NotImplemented | `scripts/anti_mvp_audit.py`, revisión de excepciones | 196 archivos de producto escaneados; 0 issues; sólo no-op explícito de telemetry allowlisted |
| reglas hardcoded por curso | regex anti-literal + revisión de `domain/rules`, audit, optimizer, graph | 0 comparación literal de curso en producto; los códigos en tests/fixtures son datos |
| mocks/fake API en producción | separación `tests/`, fixture E2E y rutas reales | mocks confinados a tests; producción usa APIs/BFF y estados honestos |
| botones/rutas placeholder | suites de interacción y rutas de app | acciones tienen handler/API/error state; no se detectó endpoint placeholder |
| auth bypass | ownership/RBAC/CSRF/security gates | no se detectó bypass; integración MFA/IdP se declara externa |
| reglas en frontend | inspección de componentes y contrato | frontend proyecta estados/backend; no evalúa elegibilidad/graduación |
| estado sólo por color | axe, badges, microcopy | estados tienen texto, iconos o explicación |
| mobile/reduced motion/zoom | accessibility E2E histórica + CSS | cubierta; ejecución nueva bloqueada por dependencias |
| evidencia ausente/UNKNOWN silenciado | provenance, governance, audit, source watcher | `UNKNOWN`/`DISPUTED`/pending visibles y bloquean publicación |

## Correcciones realizadas durante P98

- Creé los índices canónicos `docs/SPEC.md`, `docs/REQUIREMENTS.md` y
  `docs/ACCEPTANCE.md` para que la revisión solicitada no dependa de archivos
  inexistentes; sólo enlazan especificaciones existentes.
- Añadí `scripts/anti_mvp_audit.py` y lo integré a `scripts/verify.py`.
- Hice que `scripts/check_no_todos.py` pode artefactos de dependencias y
  caches, clasifique explícitamente referencias no funcionales y falle sólo
  ante un marcador dentro de código de producto; quedó integrado al
  verificador canónico.
- Añadí la prueba multiprograma sintética de P94 y su reporte epistemológico.
- Añadí el runbook de incidentes P95 y documenté que no hay incidente activo.

No se relajaron aserciones, no se introdujeron datos curriculares inventados,
no se modificó `2514-AC496-2023`, y no se eliminó funcionalidad para hacer pasar
un gate.

## Bloqueos que no son MVP oculto

1. Docker Engine/Named Pipe no es accesible desde este sandbox: no puede
   ejecutarse aquí el build final de imágenes, Docker Scout, Compose smoke ni
   backup/restore drill. La interfaz, scripts, CI y runbooks existen.
2. El entorno no permite usar el Python 3.14 del proyecto/Django; el intérprete
   bundled 3.12 sólo sirve para sintaxis/JSON y reporta correctamente que no
   puede ejecutar producción 3.14. La suite backend nueva de P26/P94 queda sin
   ejecutar localmente.
3. El registro npm no responde desde shell y `node_modules` falla con `EPERM`.
   P91 identifica que Next 16.3.1 no es el canal estable observado y deja el
   downgrade exacto a 16.2.12 pendiente de regeneración oficial del lockfile.
4. Las fuentes normativas corrientes de P90 sólo están como referencias remotas,
   no bytes archivados; no pueden promover una revisión publicada.
5. NVDA/VoiceOver/TalkBack y reviewers especializados no están expuestos.

Cada bloqueo tiene adapter, UX/estado honesto, tests o checks, observabilidad y
documentación cuando aplica; ninguno se presenta como PASS ejecutado.

## Estado de los gates

- Static secret scan, deployment assets, docs clone-clean, state recovery,
  source-watch offline, baseline check, OpenAPI self-diff y anti-MVP: **PASS**.
- Histórico ya ejecutado: backend 131 passed + 1 skip esperado, frontend 33,
  E2E 50/50 y axe 20/20, migraciones PostgreSQL, build/lint/typecheck,
  performance smoke y security/dependency checks: **PASS histórico**.
- Repetición completa actual, Docker build/scan/restore/smoke, downgrade Next
  con lockfile, fuente remota byte-level y screen-reader manual: **BLOCKED_EXTERNAL**.

## Criterio de no declaración

Esta auditoría no marca el producto como completo porque existen gates externos
sin ejecución actual. El siguiente estado sólo puede cambiar a `READY` después
de ejecutar los comandos de `docs/ACCEPTANCE.md` en un runner con Python 3.14,
registro npm, Docker Engine, PostgreSQL y Chromium accesibles, corregir cualquier
regresión, y repetir el cierre contra las fuentes oficiales archivadas.
