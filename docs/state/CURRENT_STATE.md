# Current State

## Snapshot

P00–P10 están terminados y verificados. El repositorio tiene backend Django modular, frontend Next.js con shell responsive/role-aware, design system accesible y malla curricular interactiva, cliente TypeScript generado con frescura comprobable, Compose PostgreSQL, ingestión normativa idempotente, AST/evaluador académico puro, auditoría de grado determinista con ledger de créditos, identidad con ownership/RBAC, sesiones first-party seguras, rate limiting, audit log append-only, historia académica con importación privada, reconciliación y evidencia, contrato API v1 con errores correlacionables, paginación, concurrencia optimista e idempotencia, read models `academic-overview` y `curriculum-map`, dashboard auditado y E2E de estudiante/malla; todo sobre un núcleo persistente multiinstitución separado del dominio puro. Las capacidades de producto restantes se construirán en P11–P26.

## Terminado en P00

- Toolchain fijado: Python 3.14.7, Node 24.19.0, pnpm 11.21.0, uv 0.11.19.
- Stack fijado: Django 6.0.8 + Django Ninja 1.6.2, Next 16.3.1 + React 19.2.8, PostgreSQL 18.0-alpine.
- ADR-0011 registra la decisión Django 6.0 por incompatibilidad declarada de Django Ninja 1.6.2 con Django 6.1.
- `apps/api` ejecuta checks, health live/readiness, OpenAPI, migraciones y tests; `identity.User` tiene migración inicial.
- `apps/web` compila a standalone, arranca y tiene rutas de base para curriculum, audit, graph, planner, offerings, history, sources.
- `packages/api-client` se genera desde `artifacts/openapi.json` y tiene verificación de frescura.
- `infra/docker-compose.yml` fue validado, PostgreSQL arrancó healthy y Django conectó y migró contra esa instancia.
- `scripts/verify.py` ejecuta invariantes, API, Ruff, mypy, lint, typecheck y Vitest.
- Playwright Chromium fue instalado en el entorno y el smoke E2E pasó en desktop y mobile.

## Terminado en P01

- Modelos, migraciones y admin de inspección para institutions, curriculum, rules, governance, offerings, student_records, imports, planning, audit y optimization.
- `apps/api/domain` puro con enums epistemológicos/operativos, hashing canónico y errores de inmutabilidad.
- `CurriculumRevisionService` y trigger PostgreSQL para publicación inmutable.
- `UserManager` por email y `StudentProfile` separado de la cuenta.
- Factories/tests de constraints y `docs/ERD.md` con correspondencia al esquema real.
- SQLite y PostgreSQL migrados desde cero; trigger de mutación bulk probado en PostgreSQL.

## Terminado en P02

- Baseline 2514 validado: schema `1.0.0`, fingerprint `78546fdf2e87b8aa8d0bce3afc6a4d685cb8ec9312d90d49453465f4d4ec11d4`, 141 créditos (52/61/28), 102 cursos, 97 membresías y 73 reglas de matrícula.
- `modules.imports.application.baseline` valida estructura, totales, referencias AST, ciclos, evidencia requerida y ambigüedades sin resolverlas.
- `import_curriculum_baseline` crea `DRAFT`, fuente PDF con SHA-256 verificado, grupos jerárquicos, versiones, requisitos, evidencia, batch, propuesta y reporte Markdown de forma idempotente.
- `ChangeProposal`, `ImportBatch` enriquecido y `Requirement.revision` permiten trazabilidad por revisión y diff semántico estable.
- Comandos `validate_curriculum`, `import_curriculum` y `diff_curriculum` disponibles.
- La ingestión rechaza estados `IN_REVIEW`, `APPROVED` y `PUBLISHED`; migración PostgreSQL protege también `CurriculumRevision.metadata`.

## Terminado en P03

- `apps/api/domain/rules/` contiene el AST `1.0.0`, parser estricto, serializer/hash canónico, evaluator trivalente ampliado y análisis de ciclos, sin imports de Django.
- `AuditContext` es un contrato de hechos inmutable; `EvaluationResult` conserva estado, progreso, árbol de hijos, claves, hechos y evidencias.
- Se cubren todos los nodos de `docs/05_RULE_ENGINE_SPEC.md`, ALL/ANY/UNKNOWN, aritmética exacta y equivalencias/externos/correquisitos.
- `Requirement.ast_schema_version` se persiste y el importador valida/hash cada AST.
- Golden/Hypothesis/round-trip/ciclo/benchmark ejecutados; `scripts/verify.py` pasa con 24 tests y 1 skip SQLite.

## Terminado en P04

- `apps/api/domain/audit/engine.py` implementa `AuditInput`, `AuditContext`, `AuditResult`, snapshots, `CreditLedger`, allocations, componentes, agrupaciones, requisitos externos, `remaining_requirements` y `next_unlocks` como dominio Python puro.
- La asignación es determinista y auditable: cada curso aprobado/reconocido cuenta una vez; earned/applied/unapplied están separados; un curso 4cr cierra un bucket 3cr y conserva 1cr como excedente; `FREE_ELECTIVE` sólo opera como bucket abierto explícito.
- El motor cubre repetición de intentos, homologación con créditos reconocidos, excepciones aprobadas, obligatorias, requisitos externos, UNKNOWN material y hashes reproducibles.
- `modules.audit.application.services` construye hechos desde ORM y persiste transaccionalmente `DegreeAuditRun`, `DegreeAuditResult` y `CreditAllocation` con fingerprints, snapshot, versión y hash de resultado.
- Fixture golden completo del plan 2514 y tests de dominio/servicio en `tests/test_degree_audit.py` y `tests/test_degree_audit_service.py`; especificación actualizada en `docs/06_DEGREE_AUDIT_SPEC.md`.

## Terminado en P05

- `identity.User` conserva verificación de correo y marca de cambio de contraseña; `RoleAssignment` separa rol, alcance y vigencia de la identidad y `StudentAdvisorAssignment` representa la delegación explícita de ownership.
- Sesión first-party Django implementada con cookies seguras de producción, CSRF, CORS mínimo, CSP, Permissions-Policy, COOP/CORP, rate limits compartidos y invalidación de sesiones tras cambio de contraseña.
- Endpoints de CSRF, login/logout, `/me`, reset de contraseña y verificación de correo; tokens separados por propósito, expiración Django y respuestas de reset no enumerables.
- Autorización centralizada y negativa: ownership directo, asesor con asignación vigente, editor sin publish, reviewer/admin publish, revisión publicada sin edición.
- `AuditEvent` append-only en modelo/admin/trigger PostgreSQL; metadata sensible anidada redacted, identificadores/IP como digest y actor `PROTECT` para preservar evidencia. `RateLimitBucket` soporta concurrencia de primer insert.
- ADR-0012 deja la frontera MFA explícita y no finge 2FA; el hardening de P23 debe cerrar la política de roles privilegiados.
- Migraciones `identity.0003`–`identity.0006` y `student_records.0003`–`student_records.0004` aplicadas y verificadas en SQLite/PostgreSQL.

## Terminado en P06

- Parser puro versionado `student-history/1.0.0` para CSV/JSON y parser PDF text-only con `pypdf` 6.10.0; conserva errores/warnings, estado explícito, fingerprints, confidence y locators; PDF siempre queda pendiente de confirmación.
- `RawArtifact`, `CandidateRecord`, `Reconciliation` e `ImportEvidence` preservan archivo privado, candidatos no autoritativos, decisiones explícitas y lineage al intento/reconocimiento confirmado.
- Preview/import idempotente por enrollment + SHA-256, detección de duplicados/conflictos, resolución `ACCEPT`/`EXTERNAL`/`SKIP`, códigos externos y no-overwrite; confirmación transaccional recalcula el audit de grado.
- CRUD manual de `CourseAttempt` con ownership/RBAC backend, origen/usuario, validación de institución y anulado auditable; endpoints `/api/v1/history/imports` y `/api/v1/history/attempts` documentados en OpenAPI y cliente regenerado.
- Almacenamiento privado con límite 10 MiB, validación de extensión/MIME/firma/UTF-8/NUL, rechazo de ejecutables/archives, containment path y política `never-executed`.

## Verificaciones que pasaron

```text
  python scripts/verify.py                         PASS (66 passed, 1 SQLite skip)
pnpm --dir apps/web build                        PASS (Next 16.3.1 standalone)
pnpm --dir apps/web e2e                          PASS (8/8 desktop/mobile)
manage.py check                                  PASS
makemigrations --check --dry-run                 PASS
migrate --check                                  PASS
PostgreSQL Compose + migrate + full tests         PASS (67)
curriculum validation/import/diff                 PASS
rule engine/golden/Hypothesis/benchmark           PASS
degree audit golden/service                       PASS (7 focused; included in 42 PostgreSQL tests)
identity security focused                          PASS (10 SQLite)
student history/API contract focused               PASS (19 SQLite; included in 61 PostgreSQL tests)
SQLite full suite                                  PASS (66 passed, 1 expected skip)
PostgreSQL full suite                              PASS (67)
production `manage.py check --deploy`             PASS (0 warnings)
OpenAPI export/check + generated client freshness   PASS
OpenAPI breaking-diff self-check                    PASS
```

## Problemas y riesgos conocidos

- No se creó un commit nuevo: AGENTS.md exige autorización explícita para commits automáticos. El repositorio ya contiene un commit inicial.
- Los reviewers `architecture-reviewer` y `code-reviewer` exigidos por los prompts no están expuestos como herramientas instaladas en esta sesión; la revisión de P00 fue manual y de solo lectura.
- El backend usa SQLite por defecto sólo como fallback de desarrollo/tests; el objetivo transaccional sigue siendo PostgreSQL y ya fue probado.
- El trigger de inmutabilidad es específico de PostgreSQL; en SQLite la protección de modelo/servicio evita las rutas normales y el test se marca explícitamente como skip.
- No hay `docs/SPEC.md` ni `docs/REQUIREMENTS.md` en el kit original; la revisión final deberá usar los documentos normativos existentes y registrar explícitamente esta ausencia.
- El requisito B1 externo se conserva como pendiente porque el repositorio no contiene snapshot archivado del contenido de la URL oficial.
- Los subagentes reviewer obligatorios no están expuestos en la sesión; se efectuó revisión manual y se registró la limitación.
- `NOT_APPLICABLE` no se infiere; requiere un hecho explícito en `AuditContext`.
- P04 no deja fallos funcionales pendientes. El contenido externo B1 sigue siendo un riesgo de gobernanza heredado: el motor conserva `UNKNOWN` si la capa de aplicación no aporta el hecho.
- P05 no deja fallos funcionales pendientes dentro de su alcance. MFA para roles privilegiados queda deliberadamente como frontera explícita en ADR-0012 y debe resolverse en P23 antes de producción institucional.
- P06 no deja fallos funcionales pendientes dentro de su alcance. El scanning antimalware externo depende de infraestructura institucional y el parser PDF sigue deliberadamente limitado a texto con confirmación humana; no se otorga autoridad a OCR/LLM.
- P07 no deja fallos funcionales pendientes dentro de su alcance. El breaking diff contra una rama base real se ejecutará cuando CI reciba el SHA del pull request; el detector y el self-check local ya pasan.
- P08 no deja fallos funcionales pendientes dentro de su alcance. La revisión manual NVDA/VoiceOver queda para releases institucionales.
- P09 no deja fallos funcionales pendientes dentro de su alcance. B1 permanece `UNKNOWN` por falta de snapshot normativo local; el dashboard muestra el estado, evidencia y disclaimer sin inventar graduación. La revisión manual NVDA/VoiceOver y los reviewers especializados no disponibles quedan documentados como limitaciones de la sesión.
- P10 no deja fallos funcionales pendientes dentro de su alcance. La malla pública real fue cargada como revisión DRAFT en la base local y conserva 12 ambigüedades/UNKNOWN; no se publica como normativa. Los layouts `suggested-path` y `user-scenario` requieren planificación/escenarios posteriores y la UI lo declara explícitamente.
- La comprobación de despliegue local con `DEBUG=true` emite advertencias HTTPS esperadas; con configuración de producción efímera (DEBUG=false, secreto largo, redirect SSL y HSTS) queda en cero warnings. No se incorporan secretos.

## P07 — OpenAPI & generated TypeScript client

- Routers separados por bounded context: `modules/identity/api.py`, `modules/imports/api.py` y `modules/student_records/api.py`, montados en `/api/v1` junto con Operations.
- `ProblemDetails` uniforme para errores 400/401/403/404/409/422/428/429/500, con `X-Request-ID`, `correlation_id`, validación de campos y sanitización de errores inesperados.
- CSRF de sesión documentado/probado; paginación/filter/sort deterministas para historia; ETag/If-Match para ediciones; `Idempotency-Key` para uploads con replay seguro y detección de reutilización incompatible.
- OpenAPI exportable de forma determinista; cliente `openapi-typescript` + `openapi-fetch` reproducible; stale check byte-level y detector de breaking changes en CI.
- Documentación actualizada en `docs/16_API_CONTRACT.md`, `docs/30_API_AND_DATA_VERSIONING.md` y ADR-0005.

## P08 — Frontend foundation & design system

- App Router shell común con sidebar desktop, navegación móvil, skip link, `aria-current`, role-aware editorial nav, auth shell `/login`, theme toggle claro/oscuro y conexión de sesión al API generado.
- Tokens semánticos y componentes presentacionales neutral al dominio en `apps/web/components/ui`; ningún componente decide elegibilidad o graduación.
- i18n `es-CO`/`en`, URL state (`q`, `view`, `selected`, `next` seguro), boundaries loading/error/not-found y API boundary único sin fetches dispersos.
- `axe-core` y Testing Library/Vitest pasan; Playwright desktop/mobile pasa foco del skip link y formulario de autenticación; build Next standalone PASS.
- ADR-0013 documenta el límite shell/API y la degradación explícita a `unavailable` sin datos académicos inventados.

## P09 — Student dashboard & audit UX

- `apps/api/modules/audit/application/overview.py` construye el read model determinista `academic-overview` a partir de auditoría persistida o preview de solo lectura, con ownership/RBAC, hashes, ledger, componentes, grupos, requisitos externos, `UNKNOWN`, warnings, elegibilidad y próximos desbloqueos.
- `apps/api/modules/audit/api.py` expone `GET /api/v1/academic-overview` con schemas tipados, ProblemDetails y ETag; OpenAPI y `packages/api-client` fueron regenerados y verificados.
- `apps/web/components/academic-dashboard.tsx`, `/` y `/audit` presentan únicamente hechos del backend: requerido/ganado/aplicado/no aplicado, porcentaje crediticio con disclaimer, componentes/grupos, faltantes, opciones, cursos elegibles/bloqueados/desconocidos, evidencia y deep links.
- Se añadieron estados honestos `NO_HISTORY`/`INCOMPLETE`, evidencia accesible y fixture de estudiante E2E; la UI conserva visible B1 `UNKNOWN` y no transforma 100% crediticio en graduación.
- ADR-0014, `docs/16_API_CONTRACT.md`, `docs/12_UX_INFORMATION_ARCHITECTURE.md` y `docs/15_FRONTEND_ARCHITECTURE.md` documentan la frontera read model/backend-UI y la procedencia.

### Verificaciones P09

- `python scripts/verify.py` → PASS: 63 passed + 1 skip esperado; OpenAPI/cliente, checks, migraciones, Ruff, formato, mypy, ESLint, TypeScript y Vitest 5/8 PASS.
- PostgreSQL 18.0 Compose healthy y suite completa serializada → 64 passed; `migrate --check` y migraciones PASS.
- Frontend typecheck/lint/unit/axe/build → PASS; Playwright E2E aislado en puertos 3100/8010 → 6/6 desktop/mobile PASS.

### Problemas y riesgos P09

- B1 externo permanece `UNKNOWN` hasta archivar y validar su snapshot oficial; no se publica inferencia.
- No existen `docs/SPEC.md` ni `docs/REQUIREMENTS.md` en el kit original; la auditoría final debe referenciar la documentación normativa disponible y declarar esta ausencia.
- Reviewers especializados no están expuestos como herramientas en esta sesión; se realizó revisión manual read-only sin Critical/High reproducibles.

## P10 — Interactive curriculum map

- `apps/api/modules/curriculum/application/map.py` proyecta revisión, layouts no normativos, componentes, grupos, cursos, AST/evidencia, profundidad de dependencias, desbloqueos, oferta explícita y estado personal protegido.
- `apps/api/modules/curriculum/api.py` publica `/api/v1/curriculum-map`; `artifacts/openapi.json` y `packages/api-client/src/generated.ts` están regenerados y frescos.
- `apps/web/components/curriculum-map.tsx` implementa filtros, selección contextual, ficha completa, leyenda accesible, layouts de profundidad/componente, mobile roadmap, print y persistencia de preferencias. `/curriculum` y `/curriculum/print` son rutas reales.
- `apps/web/scripts/prepare-standalone.mjs` corrige el empaquetado local de assets del runtime standalone de Next.
- `docs/adr/0015-curriculum-map-read-model.md` y las docs UX/diseño/frontend/API documentan la frontera: el backend resuelve hechos; la UI sólo presenta y filtra.

### Verificaciones P10

- `python scripts/verify.py` → PASS: 66 passed + 1 skip esperado; OpenAPI, breaking diff, migraciones, Ruff, formato, mypy, cliente, ESLint, TypeScript y Vitest incluidos.
- PostgreSQL 18.0 Compose healthy; full suite serializada → 67 passed; baseline importado de forma auditable como DRAFT: 102 cursos, 3 componentes, 12 grupos, 97 membresías y 12 ambigüedades conservadas.
- Frontend unit/axe → 6 archivos, 12 tests; build standalone → PASS; Playwright fixture E2E → 8/8 desktop/mobile; Chromium contra Django/PostgreSQL reales → 102 tarjetas, selección/ficha y print route.
- `pnpm audit --prod --audit-level high`, `uv pip check`, production `manage.py check --deploy` y `git diff --check` → PASS.

### Problemas conocidos P10

- B1 continúa `UNKNOWN` por falta de snapshot normativo archivado; no se infiere.
- `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/07_CURRICULUM_MAP_SPEC.md` no existen en el kit original; la auditoría final debe registrar esta ausencia y usar las especificaciones existentes.
- Reviewers especializados y la skill `feature-delivery` no están expuestos en esta sesión; se realizó revisión manual read-only sin Critical/High reproducibles. NVDA/VoiceOver, MFA privilegiado y antimalware externo permanecen en sus alcances posteriores.

## P11 — Dependency graph & unlock analysis

- `apps/api/domain/rules/graph.py` proyecta el AST de reglas como grafo semántico de cursos y condiciones, con operadores, umbrales, correquisitos, equivalencias, `UNKNOWN`, relaciones directas/transitivas, rutas cortas y ciclos; no fabrica relaciones curso→curso para condiciones no basadas en cursos ni duplica reglas.
- `apps/api/modules/curriculum/application/graph.py` y `apps/api/modules/curriculum/api.py` publican el read model `GET /api/v1/dependency-graph` con foco, ancestros/descendientes, desbloqueos, rutas explicativas, evidencia, estados epistemológicos, ETag, ProblemDetails y autorización coherente con el mapa.
- `apps/web/app/graph/page.tsx`, `dependency-graph-shell.tsx`, `dependency-graph.tsx` y `dependency-graph-canvas.tsx` entregan `/graph` con React Flow/ELK lazy, canvas no editable, filtros, focus mode, ciclos, leyenda, deep links y alternativa textual accesible. `apps/web/lib/api.ts` usa correctamente `params.query` de `openapi-fetch`; `apps/web/tests/api.test.ts` evita la regresión de serialización.
- OpenAPI y cliente generados están frescos; docs de UX, diseño, frontend y API actualizadas; ADR-0016 registra la proyección semántica y sus límites.

### Verificaciones P11

- `uv run --frozen pytest tests/test_dependency_graph.py tests/test_dependency_graph_api.py -q` → 6 passed.
- `python scripts/verify.py` → PASS: 72 passed + 1 skip esperado; PostgreSQL 18.0 full suite → 73 passed; migraciones/check PASS.
- Frontend → 8 archivos/15 tests, axe, lint y typecheck PASS; build standalone PASS; E2E fixture 10/10 desktop/mobile PASS.
- Flujo real Django/PostgreSQL/Next/Chromium → backend 200/ETag con 126 nodos, 87 relaciones y foco `2016379`; Next server propagó `selected`; Chromium verificó encabezado, panel de foco, textual alternative, condición y canvas.
- Seguridad y consistencia → `pnpm audit --prod --audit-level high`, `uv pip check`, `git diff --check` y guard TODO PASS.

### Problemas conocidos P11

- B1 continúa `UNKNOWN` por falta de snapshot normativo archivado; no se infiere.
- `docs/SPEC.md` y `docs/REQUIREMENTS.md` no existen en el kit original; la auditoría final debe declararlo y usar los documentos disponibles.
- Reviewers especializados y la skill `feature-delivery` no están expuestos; se efectuó revisión manual read-only sin Critical/High reproducibles. NVDA/VoiceOver queda para release institucional.

## Siguiente acción exacta

Leer y ejecutar completamente `prompts/13_OFFERINGS_SCHEDULES.md` (P12): períodos académicos, oferta, secciones y horarios.

## Comandos para reanudar

```bash
docker compose -f infra/docker-compose.yml up -d postgres
DATABASE_URL=postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum uv run --project apps/api python apps/api/manage.py migrate --check
DATABASE_URL=postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum uv run --project apps/api python apps/api/manage.py import_curriculum --json
python scripts/verify.py
pnpm --dir apps/web build
pnpm --dir apps/web e2e
DATABASE_URL=postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum uv run --project apps/api pytest
DATABASE_URL=postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum uv run --project apps/api python manage.py migrate --check
pnpm --dir packages/api-client verify
python scripts/check_openapi_breaking.py --base-revision <git-base-sha>
pnpm --dir apps/web test -- --run
pnpm --dir apps/web e2e
```

## Current snapshot after autonomous execution P24–P99 — 2026-08-17

### Qué quedó terminado

- P24–P26 fueron implementados con infraestructura, auditoría, source watch,
  mantenimiento, workflows y documentación; permanecen `IN_PROGRESS` porque
  sus gates de ejecución real no son demostrables desde este entorno.
- P90–P92 y P94 fueron ejecutados en el alcance posible: reauditoría normativa,
  revisión de dependencias, auditoría cognitiva y prueba multi-programa. Los
  artefactos están escritos y distinguen evidencia observada de evidencia
  publicable.
- P93 y P95 quedaron cerrados para sus alcances documentales/revisión estática.
- P98 creó los índices canónicos `docs/SPEC.md`, `docs/REQUIREMENTS.md` y
  `docs/ACCEPTANCE.md`, además del gate anti-MVP; P99 dejó el procedimiento de
  recovery verificable.
- El verificador estático informa: state recovery PASS (`27 done`,
  `8 in_progress`), deployment assets PASS, docs clone-clean PASS, anti-MVP
  PASS (`196` archivos, `14` bounded contexts, `0` señales), invariantes
  curriculares PASS y OpenAPI breaking diff PASS.

### Verificaciones ejecutadas en esta fase

- `python scripts/verify_deployment.py`: PASS.
- `python scripts/verify_state_recovery.py`: PASS, JSON válido y sin errores
  estructurales.
- `python scripts/anti_mvp_audit.py`: PASS.
- `python scripts/verify_docs_clone_clean.py`: PASS.
- `python scripts/update_technology_baseline.py --check`: PASS.
- Source watch offline: PASS con cuatro fuentes `UNKNOWN` explícitas.
- Revisión normativa P90, snapshot JSON, hash del PDF local y compilación
  estática de los nuevos scripts/tests: PASS.
- `scripts/verify.py`: ejecutado hasta el final con salida no cero honesta.
  Los gates estáticos pasaron; SAST completo, backend Django/uv, frontend
  pnpm, DB/PostgreSQL y algunos gates de generación no pudieron correr por
  las restricciones del entorno.
- Historial verificable previo: backend 131 passed/1 skip, frontend Vitest
  33/33, Playwright 50/50 desktop/mobile y axe 20/20 sin violaciones; estos
  resultados no sustituyen un rerun posterior a los cambios P24–P99.

### No quedó terminado / riesgos

- No se pudo ejecutar el build/scan de imágenes, backup/restore drill,
  migraciones contra PostgreSQL, smoke de Compose ni el inicio real completo:
  Docker CLI/socket está bloqueado por ACL.
- No se pudo ejecutar el backend actual con Python 3.14/Django: el venv y los
  ejecutables externos son inaccesibles y el Python bundled 3.12 no contiene
  Django. El SAST bundled también rechaza sintaxis válida sólo para 3.14.
- No se pudo repetir pnpm lint/typecheck/test/build/E2E: `node_modules` tiene
  archivos legibles por el proyecto pero bloqueados con `EPERM`; el standalone
  no arranca por el mismo problema (`Cannot find module 'next'`).
- Source watch remoto y consulta de registry fallaron por restricciones de red;
  P91 no modificó el lockfile ni hizo un downgrade ciego.
- B1 y cualquier cambio normativo siguen `UNKNOWN`/pendientes de revisión; no
  se publicó ninguna inferencia. Reviewer especializado, lector de pantalla
  y dispositivo físico tampoco están disponibles.
- `.codex/STATUS.md` no pudo actualizarse en esta fase porque la política de
  filesystem expone `.codex` como sólo lectura para el proceso; este snapshot,
  el roadmap y los informes de auditoría son la trazabilidad alternativa.

### Siguiente acción exacta

Reanudar en un runner/estación que tenga Python 3.14 + Django, `uv`, pnpm con
`node_modules` reparable, registry, Docker CLI/socket y PostgreSQL accesibles:

1. Ejecutar `uv run --frozen python scripts/verify.py` con
   `DATABASE_URL` apuntando a PostgreSQL real.
2. Ejecutar `pnpm --dir apps/web install --frozen-lockfile`, regenerar cliente,
   lint, typecheck, Vitest, build, Playwright E2E y axe.
3. Ejecutar build/scan de imágenes, migraciones, backup, restore drill y smoke
   de Compose; iniciar API/web y probar dashboard, malla, grafo, auditoría,
   oferta, planner, optimizer y backoffice.
4. Repetir source watch remoto, prueba multi-programa y sign-off de reviewers;
   archivar fuentes normativas P90 y resolver los `UNKNOWN` sin inferencias.
5. Actualizar `ROADMAP_STATUS.json`, los informes P25/P90/P92/P98 y la
   auditoría final sólo con resultados ejecutados; entonces reevaluar el Goal.

### Decisiones abiertas

- Resolver Next estable/lockfile en P91 con documentación oficial y pruebas de
  compatibilidad; no editar manualmente `pnpm-lock.yaml`.
- Resolver si existe y puede archivarse una fuente normativa íntegra posterior
  o complementaria a Acuerdo 496 de 2023 antes de mutar la revisión publicada.
- Obtener aprobación operativa de Docker/backup/restore, reviewers y pruebas
  manuales de accesibilidad.

### Comandos para reanudar

```powershell
$env:DATABASE_URL='postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum'
uv run --frozen python scripts/verify.py
python scripts/verify_deployment.py
python scripts/verify_state_recovery.py
python scripts/anti_mvp_audit.py
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test -- --run
pnpm --dir apps/web build
pnpm --dir apps/web e2e
docker compose -f infra/docker-compose.production.yml --profile migrate run --rm migrate
python scripts/backup_postgres.py --help
python scripts/restore_drill.py --help
python scripts/smoke.py --help
```

## P20 — Observabilidad y operación — 2026-08-16 22:25 -05:00

### Qué quedó terminado

- El backend ahora emite logs JSON estructurados y seguros, conserva
  correlación `X-Request-ID`, propaga `traceparent`, devuelve `X-Trace-ID` y
  crea spans OTel configurables por OTLP. La redacción cubre secretos, tokens,
  cookies, emails, ids, archivos, bodies y mensajes de excepción.
- Se instrumentaron métricas RED HTTP, health DB, jobs de optimizer/import/
  notificaciones y operaciones de auditoría/grafo/publicación, con cardinalidad
  controlada, snapshot agregado y exportadores OTel opt-in. La instrumentación
  no modifica reglas, transacciones ni payloads académicos.
- `/api/v1/health/live` es liveness sin DB; `/api/v1/health/ready` ejecuta
  `SELECT 1` y responde `503 NOT_READY` seguro si falla; `/api/v1/health/metrics`
  está protegido en producción por token y es `no-store`.
- Frontend: adaptador opt-in de errores/Web Vitals y observador LCP/CLS/FID
  montado en el layout; no envía cookies, auth, query strings ni mensajes de
  error. Error boundary y tests de redacción incluidos.
- Smoke sintético, dashboard operativo, runbooks y ADR-0024 documentados;
  OpenAPI y cliente TS regenerados; `uv.lock` actualizado con el exportador
  OTel 1.44.0.

### Verificaciones que pasaron

- `scripts/verify.py`: PASS — 117 backend tests + 1 skip esperado, 33 tests
  frontend, OpenAPI/client, migraciones, Ruff/formato/mypy, ESLint y TS.
- PostgreSQL real: `migrate --check`, `makemigrations --check --dry-run`,
  migration plan 0 y suite completa `118 passed`; server version 18.0.
- `pnpm build` y Playwright `20/20` desktop/mobile PASS; API y Next standalone
  reales en puertos 8020/3020; smoke live/ready/OpenAPI/Web PASS; headers de
  request/trace y `Cache-Control: no-store` observados.
- `pnpm audit --prod --audit-level high`, `uv pip check`, OTel exporter import,
  `manage.py check --deploy` sin warnings y `git diff --check` PASS.

### No quedó terminado / riesgos

- No quedan fallos resolubles de P20. Sin collector OTLP las métricas del
  registro en memoria no sobreviven reinicios; el despliegue debe configurar
  endpoint y retención antes de depender de continuidad histórica.
- SLO numéricos siguen pendientes de baseline real; no se inventan objetivos.
- B1 externo continúa `UNKNOWN`; no hay snapshot normativo archivado ni reglas
  inventadas. Email está deshabilitado localmente.
- Revisores especializados, NVDA/VoiceOver y skills `feature-delivery`/
  `security-change` no están expuestos; se dejó revisión manual read-only.
  `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md` siguen ausentes
  y deben declararse en la auditoría final.
- No commit automático.

### Siguiente acción exacta

Leer completamente `prompts/21_PERFORMANCE.md` y las referencias de
performance antes de modificar código.

### Comandos para reanudar

```powershell
$env:DATABASE_URL='postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum'
uv run --frozen python scripts/verify.py
uv run --frozen python -m pytest -q tests/test_observability.py
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web build
pnpm --dir apps/web e2e
python scripts/smoke.py --base-url http://127.0.0.1:8020 --web-url http://127.0.0.1:3020
```

## P14 — Constraint optimizer (2026-08-16)

### Qué quedó terminado

- Motor puro CP-SAT en `apps/api/domain/optimization/` con input/output
  canónicos, snapshot serializable, hashes estables y versión del solver.
- Variables `x(course, term)` y asignaciones de grupo con restricciones duras
  de cursos obligatorios, grupos, créditos, límites por término,
  prerrequisitos, correquisitos, oferta, locks y conflictos de secciones.
  Cursos ya aprobados quedan fuera de la selección.
- Políticas explícitas `ALLOW_UNKNOWN`/`REQUIRE_OFFERED`, estados
  `OPTIMAL`/`FEASIBLE`/`INFEASIBLE`/`UNKNOWN`, límites de tiempo, semilla,
  cancelación cooperativa y explicaciones estructuradas.
- Objetivos lexicográficos por pasadas, sin pesos mágicos, y `OptimizationRun`
  persistido con snapshot, input/output hash, versión, solución, objetivos,
  supuestos, conflictos y marcas de ejecución.
- API OpenAPI/cliente, BFF y panel `/planner` con polling, cancelación y
  comparación de solución contra escenario. No se mutan intentos ni se aplica
  automáticamente una propuesta.
- ADR-0019 y actualizaciones de optimización/API/UX/frontend/ERD.

### Verificaciones que pasaron

- Optimización focalizada: 11 passed; incluye Hypothesis, golden cases,
  round-trip, cancelación, regresiones de locks/cursos aprobados y API.
- Backend final: 94 passed + 1 skip esperado por trigger PostgreSQL-only;
  `scripts/verify.py` PASS; OpenAPI/cliente/migraciones/check/Ruff/format/mypy
  PASS.
- `optimization.0004_optimizationrun_execution_metadata` aplicado en SQLite
  y PostgreSQL; `migrate --check` y `makemigrations --check --dry-run` PASS.
- Frontend: lint/typecheck/Vitest 21/21 + axe/build PASS; Playwright E2E
  14/14 desktop/mobile PASS.
- Seguridad: audit de dependencias sin vulnerabilidades high, `uv pip check`,
  secret scan, `git diff --check` y deploy check de Django PASS. El guard TODO
  sólo reporta referencias históricas/documentales y del propio guard; no hay
  TODO/FIXME/HACK/XXX funcional en el código nuevo.
- Integración real Postgres + Django + Next/BFF: login/scenarios 200, creación
  optimizer 202, polling a `INFEASIBLE` con hash/conflicto, y `/planner` 200.

### No quedó terminado / riesgos

- B1 externo permanece `UNKNOWN` sin snapshot normativo archivado; no se
  inventan reglas ni se automatiza SIA autenticado.
- NVDA/VoiceOver y reviewers/subagentes especializados no están disponibles;
  revisión manual read-only, axe, teclado y E2E pasan.
- `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md` no existen en
  el kit original; la auditoría final deberá declararlo y revisar los
  documentos equivalentes existentes.
- No se creó commit automático.

### Siguiente acción exacta

Leer y ejecutar completamente `prompts/16_ADMIN_GOVERNANCE.md` como P15,
empezando por sus documentos normativos y el estado real del backoffice.

## P12 — Academic terms, offerings, sections & schedules (2026-08-16)

### Qué quedó terminado

- Cadena temporal `AcademicTerm → CourseOffering → Section → Meeting` con
  `SourceSnapshot`, fechas parciales, sesiones alternas, capacidad opcional y
  restricciones de integridad; cambiar oferta no crea una revisión curricular.
- Dominio puro de frescura y de conflictos recurrentes exactos: días,
  intervalos, límites, fechas parciales, zonas horarias/DST y `UNKNOWN` si la
  zona es inválida.
- `OfferingSourceAdapter`, importador JSON normalizado/versionado, SHA-256,
  `retrieved_at`, evidencia y selección temporal de `CourseVersion`. El
  adaptador SIA público es una frontera segura y no automatiza sesiones
  autenticadas ni scraping privado.
- API pública de términos/ofertas/secciones/reuniones/evaluación de agenda y
  CRUD administrativo scoped de términos, con ETags, ProblemDetails y estados
  separados de oferta/elegibilidad/agenda.
- `/offerings` responsive, filtros por término/curso, frescura visible,
  capacidad honesta, reuniones, selección optimista de grupos y conflictos
  exactos desde backend.
- OpenAPI/cliente generados, ADR-0017, registro de fuentes oficiales y
  documentación de oferta, UX, diseño y frontend actualizados.

### Verificaciones que pasaron

- `tests/test_offerings.py`: 5 passed.
- `scripts/verify.py`: PASS, 77 passed + 1 skip PostgreSQL-only esperado;
  Django/migraciones/OpenAPI/Ruff/format/mypy/cliente/ESLint/TypeScript/Vitest
  incluidos.
- Frontend: lint, typecheck y 9 archivos/18 tests Vitest + axe PASS.
- Next production build + standalone PASS; Playwright E2E 12/12 desktop/mobile
  PASS.
- PostgreSQL real: migración `offerings.0002...` aplicada, payload archivado
  importado (2 ofertas/2 grupos/2 reuniones), API 200/ETag y 26 conflictos
  recurrentes; Chromium contra Next standalone real verificó `/offerings`,
  selección y panel de solapamientos.

### No quedó terminado / riesgos

- B1 externo permanece `UNKNOWN` por falta de snapshot normativo local.
- La captura actual de ofertas requiere un proceso institucional autorizado;
  el producto no automatiza SIA autenticado ni afirma cupos en tiempo real.
- NVDA/VoiceOver y reviewers especializados no están disponibles en esta
  sesión; se hizo revisión manual read-only y pasan axe/teclado/E2E.
- `docs/SPEC.md` y `docs/REQUIREMENTS.md` no existen; la auditoría final debe
  dejarlo explícito y usar los documentos existentes.
- No se creó commit automático.

### Siguiente acción exacta

Leer y ejecutar completamente `prompts/14_PLANNER.md` (P13), empezando por
`docs/11_PLANNER_OPTIMIZER.md`, `docs/10_OFFERINGS_AND_SCHEDULES.md` y
`docs/12_UX_INFORMATION_ARCHITECTURE.md`.

### Comandos para reanudar

```bash
docker compose -f infra/docker-compose.yml up -d postgres
DATABASE_URL=postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum uv run --project apps/api python apps/api/manage.py migrate --check
python scripts/verify.py
pnpm --dir apps/web build
pnpm --dir apps/web e2e
uv run --project apps/api pytest apps/api/tests/test_offerings.py -q
```

## P13 — Planner scenarios (2026-08-16)

### Qué quedó terminado

- Escenarios persistentes versionados y scoped a la matrícula/usuario, con
  preferencias de créditos, disponibilidad y prioridad, término objetivo,
  duplicación, renombrado, archivo y sharing privado revocable por defecto.
- Cursos planificados por término con sección opcional, bloqueo, invariantes
  de institución/curso/término y optimistic concurrency mediante If-Match/ETag.
- Validador puro de planificación con prerrequisitos por orden temporal,
  correquisitos en el mismo término, composición ALL/ANY/NOT, equivalencias,
  oferta/frescura, disponibilidad, conflictos de agenda y `UNKNOWN` explícito.
- Proyección de auditoría por escenario separada del historial real; las
  proyecciones no crean intentos ni modifican matrícula/revisión. Inputs
  incompletos producen una proyección UNKNOWN trazable.
- API completa de escenarios/cursos/comparación/compartir y frontend `/planner`
  con columnas por término, drag/drop y alternativa de teclado, bloqueo,
  warnings, auditoría proyectada, comparación y privacy panel.
- BFF Next para conservar cookies/CSRF y proxy interno; OpenAPI y cliente
  generado actualizados. ADR-0018, contrato API, UX, design system y
  arquitectura frontend actualizados.

### Verificaciones que pasaron

- `uv run --frozen python -m pytest -q` desde `apps/api`: 83 passed + 1 skip
  esperado por trigger PostgreSQL; P13 focalizado: 6 passed.
- `scripts/verify.py`: PASS completo; incluye invariantes, Django, migraciones,
  OpenAPI freshness/breaking diff, Ruff, formato, mypy, cliente, ESLint,
  TypeScript y 20 tests Vitest + axe.
- Migraciones: `makemigrations --check --dry-run`, `migrate --check` y
  `manage.py check` PASS; PostgreSQL local aplicó planning.0004 y dejó todas
  las migraciones `[X]`.
- `pnpm --dir apps/web build`: PASS con Next 16.3.1/standalone; E2E
  Playwright: 14/14 desktop/mobile; lint y typecheck PASS.
- Seguridad/dependencias: `pnpm audit --prod --audit-level high`, `uv pip
  check`, `git diff --check`, secret scan y guard de TODO/FIXME/XXX PASS.
- Flujo real: backend fresco en 8012 con PostgreSQL pasó health live/ready,
  login CSRF, crear/listar escenario, añadir curso, compartir, vista pública
  redacted, revocar/404 y archivar. Next standalone en 3101 pasó BFF de
  escenarios, health y `/planner` 200 con sesión real.

### No quedó terminado / riesgos

- B1 externo sigue `UNKNOWN` sin snapshot normativo archivado. La captura SIA
  actual requiere una fuente institucional autorizada; no se automatiza acceso
  autenticado ni se inventa capacidad en tiempo real.
- NVDA/VoiceOver y reviewers especializados no están disponibles en esta
  sesión; revisión manual read-only, axe, teclado y E2E desktop/mobile pasan.
- `docs/SPEC.md` y `docs/REQUIREMENTS.md` no existen en el repositorio original;
  la revisión final debe declararlo y usar las especificaciones existentes.
- No se creó commit automático. La orden canónica usa `python -m pytest`
  porque la política de control de aplicaciones de este Windows bloquea el
  ejecutable `pytest` aunque la suite funciona con el módulo de Python.

### Siguiente acción exacta

Leer y ejecutar completamente `prompts/15_OPTIMIZER.md` como P14, comenzando
por `docs/11_PLANNER_OPTIMIZER.md`, `docs/04_RULE_ENGINE_SPEC.md` y las
referencias específicas de optimización indicadas por el prompt.

### Decisiones abiertas

- B1 externo y la fuente institucional autorizada siguen pendientes de
  evidencia; mantener UNKNOWN hasta incorporar snapshot y revisión humana.
- Confirmar en el milestone de optimización los límites de solver, timeouts,
  cancelación y explicación de optimalidad antes de publicar rutas sugeridas.

### Comandos para reanudar

```powershell
$env:DATABASE_URL='postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum'
uv run --frozen python manage.py migrate --check
uv run --frozen python -m pytest -q
uv run --frozen ruff check .
uv run --frozen mypy config modules tests
pnpm --dir packages/api-client verify
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test -- --run
pnpm --dir apps/web build
pnpm --dir apps/web e2e
```

## Authoritative latest snapshot — 2026-08-17 10:46 -05:00

Este bloque es la referencia más reciente del archivo. La auditoría completa
está en `docs/audit/FINAL_AUDIT_2026-08-17.md`; no se declara `READY`.

- Verificado PASS: deployment assets, state recovery (`27 done`, `8
  in_progress`, sin errores), anti-MVP (`196` archivos/14 contextos/0 issues),
  docs clone-clean, baseline check, secret scan, source watch offline,
  curriculum invariants, OpenAPI breaking diff, JSON y `py_compile` del cambio
  de mantenimiento DB.
- Historial PASS conservado: backend 131 passed/1 skip, Vitest 33/33,
  Playwright 50/50 y axe 20/20; no sustituye rerun post-P24–P99.
- Bloqueado: `scripts/verify.py` completo, SAST con Python 3.14, tests Django,
  pnpm lint/typecheck/test/build/E2E, cliente generado, Docker/PostgreSQL,
  migraciones/restore/smoke, source watch remoto, downgrade Next, reviewers y
  pruebas manuales de accesibilidad. Las causas son ACL de runtime/Node/Docker,
  red/registry y ausencia de herramientas humanas, no fallos ocultos.
- P24–P26, P90–P92, P94 y P98 permanecen `IN_PROGRESS` en el roadmap hasta
  ejecutar esos gates; P93/P95/P99 están cerrados en sus alcances.
- Próxima acción exacta: usar un runner con Python 3.14+Django+uv,
  node_modules/pnpm reparable, Docker/PostgreSQL y red; ejecutar los comandos
  canónicos de `docs/ACCEPTANCE.md`, iniciar API/web y repetir la matriz.
- `.codex/STATUS.md` no se pudo escribir porque esa ruta está expuesta como
  sólo lectura por la política de filesystem de esta sesión; el estado se
  dejó en `ROADMAP_STATUS.json`, este archivo, `SESSION_LOG.md`, `RISKS.md`,
  `OPEN_DECISIONS.md` y la auditoría final.

## P15 — Backoffice curricular y diff semántico (2026-08-16 18:51 -05:00)

### Qué quedó terminado

- Source Inbox y visor de documentos/snapshots con SHA-256, procedencia y
  evidencia; propuestas de revisión con diff semántico, validación e impacto.
- Candidatos de extracción revisables individualmente o mediante preview
  masivo sin escrituras; estados epistemológicos explícitos y bloqueo de
  `VERIFIED` sin evidencia del snapshot correcto.
- Inspector AST + explicación humana + evidencia, cola de revisión y workflow
  `DRAFT → IN_REVIEW → APPROVED → APPLIED` con editor/revisor separados,
  confirmación explícita y publicaciones inmutables.
- ETag/`If-Match`, conflictos visibles, `AuditEvent` relacionado para
  propuestas/candidatos/requisitos/revisiones/publicaciones, OpenAPI/cliente,
  `/sources` responsive y ADR-0020.

### Verificaciones que pasaron

- Gobernanza focalizada: 4 SQLite + 4 PostgreSQL.
- Suite backend: 98 passed + 1 skip esperado por trigger PostgreSQL-only.
- `scripts/verify.py`: PASS completo; Django/migraciones/OpenAPI/cliente,
  invariantes, Ruff/formato/mypy, ESLint/TypeScript y Vitest 23/23 + axe.
- `governance.0003...` aplicada en SQLite y PostgreSQL; build de producción
  Next PASS; Playwright 16/16 desktop/mobile PASS.
- PostgreSQL/Django real verificó login-CSRF, inbox/detail, submit,
  request-changes y restauración a DRAFT con ETag; no quedó servidor temporal
  escuchando en 8020.

### No quedó terminado / riesgos

- P16–P26 y los prompts finales de auditoría/operación aún deben ejecutarse.
- B1 externo sigue `UNKNOWN` sin snapshot normativo institucional archivado;
  no se publican inferencias.
- NVDA/VoiceOver, subagentes reviewers y algunas comprobaciones externas no
  están disponibles; axe/teclado/E2E y revisión manual read-only pasan.
- `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md` no existen en
  el repositorio original. La auditoría final revisará los documentos
  equivalentes disponibles y lo dejará explícito.
- No hay commit automático.

### Siguiente acción exacta

Leer completamente `prompts/17_PUBLICATION_IMPACT.md` como P16, inspeccionar la
implementación de gobernanza/publicación y ejecutar sus gates antes de avanzar.

### Decisiones abiertas

- Mantener B1 como `UNKNOWN` hasta incorporar fuente institucional archivada y
  revisión humana.
- Definir en P16 la estrategia final de materialización de impacto y de
  invalidación/re-cálculo al publicar, sin mutar historia individual.

### Comandos para reanudar

```powershell
uv run --frozen python scripts/verify.py
uv run --frozen python -m pytest -q apps/api/tests/test_governance_backoffice.py
pnpm --dir apps/web build
pnpm --dir apps/web e2e
```

## P16 — Publicación e impacto (2026-08-16 19:50 -05:00)

### Qué quedó terminado

- Publicación transaccional con locks, validación de base vigente,
  supersesión (`PUBLISHED → SUPERSEDED`) y contenido/hash inmutable.
- `PublicationEvent`, `PublicationImpact` y `NotificationOutbox` persistidos
  atómicamente. El impacto conserva matrícula, revisión/auditoría previa y
  `result_hash`; el plan de recomputación exige decisión explícita de cohorte y
  la notificación queda encolada para después del commit.
- Endpoint editorial de impacto, OpenAPI/cliente, vista `/sources`, auditoría
  relacionada y ADR-0021. Se actualizaron versionado, procedencia, auditoría,
  backoffice, eventos, notificaciones y contrato API.
- Se corrigió una regresión de conexiones PostgreSQL en el ejecutor síncrono de
  optimización, se hizo UTF-8 el guard de TODO de Windows y se aisló el estado
  mutable del fixture editorial para E2E paralelo.

### Verificaciones que pasaron

- 3 tests de impacto SQLite + 3 PostgreSQL; suite PostgreSQL completa: 102
  passed; suite canónica SQLite: 101 passed + 1 skip esperado por trigger
  PostgreSQL-only.
- Migraciones `governance.0004` y `notifications.0001` aplicadas y sin
  pendientes; `manage.py check`, `makemigrations --check`, `migrate --check`,
  invariantes, OpenAPI freshness/breaking y cliente generado PASS.
- `scripts/verify.py` PASS: backend, Ruff/formato/mypy, ESLint, TypeScript y
  Vitest 23/23 con axe.
- Build Next standalone PASS; Playwright 16/16 desktop/mobile PASS tras
  reparar el aislamiento del fixture; `pnpm audit`, `uv pip check`,
  `git diff --check` y guard TODO UTF-8 PASS.

### No quedó terminado / riesgos

- P17–P26 y los prompts finales de auditoría/operación aún deben ejecutarse.
- El outbox está preparado y verificado como solicitud durable; el dispatcher y
  la entrega efectiva son alcance del P17.
- B1 externo continúa `UNKNOWN` por falta de snapshot normativo institucional;
  no se publican inferencias ni se automatiza SIA autenticado.
- Los archivos referidos por P16 `docs/24_PUBLICATION_AND_IMPACT.md` y
  `docs/05_AUDIT_AND_CREDIT_ALLOCATION.md` no existen; se usaron los
  equivalentes `docs/07_CURRICULUM_VERSIONING.md` y
  `docs/06_DEGREE_AUDIT_SPEC.md`. También siguen ausentes
  `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md`.
- Reviewers/subagentes especializados y NVDA/VoiceOver no están expuestos; se
  hizo revisión manual read-only, axe, teclado y E2E desktop/mobile. No hay
  commit automático.

### Siguiente acción exacta

Leer completamente `prompts/18_NOTIFICATIONS.md` como P17, inspeccionar el
outbox y cerrar el ciclo de entrega/reintento sin notificar publicaciones
fallidas.

### Decisiones abiertas

- Mantener B1 como `UNKNOWN` hasta incorporar evidencia normativa archivada.
- Implementar en P17 el dispatcher reemplazable, deduplicación, reintentos,
  canales y observabilidad de `NotificationOutbox` sin convertir la entrega en
  autoridad académica.

## P17 — Notificaciones (2026-08-16 20:48 -05:00)

### Qué quedó terminado

- `NotificationEvent`, `NotificationDelivery`, `NotificationPreference` y
  outbox transaccional con deduplicación, estados `QUEUED/SENDING/SENT/FAILED/
  SUPPRESSED`, backoff, cursor de feed y comando `process_notifications`.
- Materialización sólo después del commit y sólo desde revisiones `PUBLISHED`;
  drafts/publicaciones fallidas no crean eventos. Preferencias por tipo/canal y
  locale se aplican antes del fan-out; email es un adaptador opcional con clave
  de idempotencia estable y contenido general sin PII ni detalles académicos.
- API autenticada de centro/preferencias/lectura, cliente OpenAPI regenerado y
  centro frontend responsive con contador accesible, lectura individual/global,
  estados de error/carga y preferencias de canal/idioma.
- ADR-0022 y documentación de notificaciones, API, seguridad, eventos y ERD.
  La skill `feature-delivery` y reviewers especializados no están expuestos;
  se hizo revisión manual read-only de arquitectura, código, seguridad,
  currículo y UX.

### Verificaciones que pasaron

- 5 tests de notificaciones SQLite + 5 PostgreSQL; `scripts/verify.py` PASS
  con 106 backend tests + 1 skip esperado por trigger PostgreSQL-only y
  Vitest 26/26 + axe.
- Migración `notifications.0002` aplicada en SQLite/PostgreSQL; `manage.py
  check`, `makemigrations --check`, `migrate --check`, `showmigrations`,
  OpenAPI/client verify, Ruff, formato, mypy, ESLint y TypeScript PASS.
- Next production build PASS; Playwright 18/18 desktop/mobile PASS incluyendo
  flujo real del centro, preferencias y marcar todo como leído.
- `pnpm audit --prod --audit-level high`, `uv pip check`, `git diff --check`,
  guard TODO UTF-8 y `manage.py check --deploy` con parámetros explícitos de
  producción/HSTS/SSL/cookies PASS.

### No quedó terminado / riesgos

- P18–P26 y auditoría final aún deben ejecutarse. B1 externo sigue `UNKNOWN`
  por falta de snapshot normativo archivado; no se inventan reglas ni se
  automatiza SIA autenticado.
- El proveedor email local no está configurado y permanece deshabilitado por
  defecto; el worker debe programarse y observarse en el despliegue.
- NVDA/VoiceOver y reviewers/subagentes no están disponibles. Siguen ausentes
  `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md`; la auditoría
  final debe contrastar los equivalentes existentes y declarar la ausencia.
- No se creó commit automático.

### Siguiente acción exacta

Leer completamente `prompts/19_ANALYTICS.md` como P18 y sus referencias de
analytics antes de inspeccionar/editar la implementación.

### Decisiones abiertas

- Mantener B1 como `UNKNOWN` hasta incorporar evidencia normativa archivada y
  revisión humana.
- Mantener email opcional/deshabilitado hasta configurar proveedor, secreto,
  observabilidad y política de retención en el milestone de despliegue.

### Comandos para reanudar

```powershell
$env:DATABASE_URL='postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum'
uv run --frozen python scripts/verify.py
uv run --frozen python -m pytest -q tests/test_notifications.py
pnpm --dir packages/api-client verify
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web build
pnpm --dir apps/web e2e
```

## Current snapshot after P20 — 2026-08-16 22:25 -05:00

P20 está `done` y es el último milestone ejecutado. La observabilidad,
health/readiness, OTel, métricas, frontend adapter, smoke, dashboard y runbooks
están implementados y verificados; el detalle completo está en la sección
P20 anterior de este archivo. `scripts/verify.py`, suite PostgreSQL, build,
E2E, smoke real, auditoría de dependencias y deploy check pasaron. La siguiente
acción exacta es leer `prompts/21_PERFORMANCE.md`; P21–P26 y la auditoría final
siguen pendientes. B1 continúa `UNKNOWN`, las tres especificaciones globales
ausentes deben declararse, y no se creó commit.

### Comandos para reanudar

```powershell
uv run --frozen python scripts/verify.py
uv run --frozen python -m pytest -q tests/test_publication_impact.py
pnpm --dir apps/web build
pnpm --dir apps/web e2e
```

## P18/P19 — Analítica estudiantil e institucional — 2026-08-16 21:33 -05:00

### Qué quedó terminado

- Backend analytics read-only derivado de snapshots de auditoría persistidos y
  revisiones publicadas: métricas privadas de créditos/requisitos, tendencia,
  cursos críticos y escenarios; agregados institucionales de avance,
  cuellos de botella, requisitos rezagados, demanda potencial, rutas y
  duración observada.
- RBAC con alcance institucional/programa para `ANALYST`/`ADMIN`, validación
  de período, supresión de celdas pequeñas, minimización sin PII, HMAC para
  claves de rutas y exportación agregada JSON/CSV auditada y `no-store`.
- Catálogo de definiciones visible, API versionada, OpenAPI/cliente
  regenerados, página `/analytics` con tablas/progreso accesibles, pruebas
  axe, fixture E2E y ADR-0023/documentación de analítica/seguridad/RBAC.

### Verificaciones que pasaron

- Focalizado analytics: 4 SQLite + 4 PostgreSQL.
- `scripts/verify.py`: 110 passed + 1 skip esperado; invariantes, Django,
  migraciones, OpenAPI, cliente, Ruff/formato/mypy y frontend checks PASS.
- Vitest 30/30 con axe, ESLint, TypeScript, Next build standalone y
  Playwright 20/20 desktop/mobile PASS; `migrate --check` PASS.

### No quedó terminado / riesgos

- P20–P26 y auditoría final aún deben ejecutarse. B1 externo continúa
  `UNKNOWN`; no se publican inferencias.
- La duración oficial a grado queda `UNKNOWN` porque el modelo no contiene
  fecha oficial; la API sólo expone duración observada derivada de términos.
- Reviewers especializados y NVDA/VoiceOver no están disponibles. Siguen
  ausentes `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md`.
- No commit automático.

### Siguiente acción exacta

Leer `prompts/20_OBSERVABILITY.md` completo y contrastar la instrumentación
existente antes de comenzar P20.

### Comandos para reanudar

```powershell
$env:DATABASE_URL='postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum'
uv run --frozen python scripts/verify.py
uv run --frozen python -m pytest -q tests/test_analytics.py
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web build
pnpm --dir apps/web e2e
```

## Current snapshot after P20 (final entry) — 2026-08-16 22:25 -05:00

P20 está `done` y es el último milestone ejecutado. Backend/frontend de
observabilidad, health/readiness, OTel, métricas, adaptador Web Vitals, smoke,
dashboard y runbooks están implementados y verificados. `scripts/verify.py`,
PostgreSQL (118 tests, plan de migraciones 0), build, E2E 20/20, smoke real,
auditoría de dependencias y deploy check pasaron. La siguiente acción exacta
es leer `prompts/21_PERFORMANCE.md`; P21–P26 y la auditoría final siguen
pendientes. B1 es `UNKNOWN`, faltan las tres especificaciones globales, y no
se creó commit.

## Current snapshot after P21 — 2026-08-16 23:07 -05:00

### Qué quedó terminado

P21 está `done`. Se midieron las rutas críticas con PostgreSQL 18.0 y Python
3.14.7, se eliminó el N+1 de evidencias del snapshot de auditoría, la
selección priorizada de matrícula quedó en una sola consulta, y el grafo/mapa
reutilizan índices internos sin cambiar su semántica. El optimizador tiene
límites explícitos de 300 s, 2 workers y 20 jobs en vuelo, con rechazo
auditable de sobrecapacidad. No se añadió caché académica, Redis ni índice sin
evidencia de `EXPLAIN`.

Se añadieron el benchmark de proceso/consultas/planes, el load probe estándar,
la auditoría de bundle y la documentación/ADR de rendimiento. El benchmark
final registró p95 de 16.489 µs por regla, 172.191 ms para malla, 168.314 ms
para grafo con foco y 239.645 ms para auditoría válida, con 16/16/19 queries;
la auditoría bajó de 164 a 19 consultas.

### Verificaciones que pasaron

- 4 tests de rendimiento; regresiones focalizadas 34 passed.
- `scripts/verify.py` con PostgreSQL: 122 backend passed, 33 frontend passed,
  OpenAPI/cliente, Django, migraciones, Ruff, formato, mypy, ESLint y
  TypeScript PASS.
- Next build standalone, `pnpm audit:bundle`, Playwright 20/20,
  `scripts/smoke.py` API/Web real, rutas críticas HTTP 200, health headers de
  correlación/trace/no-store, `pnpm audit`, `uv pip check`, deploy check y
  `git diff --check` PASS.
- PostgreSQL real: `makemigrations --check --dry-run`, `migrate --check`, plan
  de migraciones 0 y `server_version_num=180000`.

### No quedó terminado / riesgos

- No hay trabajo funcional pendiente dentro de P21. El p95 concurrente de
  `runserver` se conserva como señal del entorno de desarrollo, no como SLO;
  el baseline de producción requiere worker/proxy/pool y observación de siete
  días.
- El guard de TODO reportó sólo referencias documentales/históricas,
  metadatos y su propio patrón (35 hits); no hay marcador funcional en el
  código P21. B1 sigue `UNKNOWN` sin snapshot normativo y no se publican
  inferencias.
- P22–P26 y la auditoría final quedan pendientes. Faltan globalmente
  `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md`; reviewers,
  subagentes y `feature-delivery` no están expuestos. No se creó commit.

### Siguiente acción exacta

Leer completamente `prompts/22_ACCESSIBILITY_E2E.md`, sus referencias y el
estado real de accesibilidad antes de comenzar P22.

### Comandos para reanudar

```powershell
$env:DATABASE_URL='postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum'
uv run --frozen python scripts/verify.py
uv run --frozen python ..\..\scripts\benchmark_performance.py --iterations 15 --explain
pnpm --dir apps/web audit:bundle
pnpm --dir apps/web e2e
```

## Current snapshot after P22 — 2026-08-17 00:04 -05:00

### Qué quedó terminado

P22 está `done`. La web tiene una suite axe de páginas críticas, gestión de
foco en menú móvil/ficha curricular/grafo, alternativa textual del grafo,
alternativa no-gestual del planificador, responsive mobile, reduced motion y
verificación de zoom equivalente a 200%. El backoffice conserva un solo
landmark `main` de nivel superior. El contraste claro usa `--text-muted`
`#5a6d61` (5.53:1 sobre blanco), con ratios claros/oscuros y la checklist
manual documentados en `docs/ops/ACCESSIBILITY_MANUAL_CHECKS.md`.

### Verificaciones que pasaron

- `pnpm test` 33/33; `pnpm lint`; `pnpm typecheck`; `pnpm build` standalone.
- Playwright E2E 50/50 desktop/mobile después de la reparación final de
  landmarks; axe 20/20 desktop/mobile sin ninguna violación y los flujos de
  teclado, foco, planner, zoom, reduced motion y journeys incluidos.
- El workflow E2E editorial cubre editor → `IN_REVIEW` → reviewer
  `APPROVED` → `PUBLISHED` y recibo de publicación.

### No quedó terminado / riesgos

- NVDA/VoiceOver y dispositivos físicos requieren una estación de release;
  se dejó la checklist explícita y no se marcó como prueba ejecutada.
- B1 sigue `UNKNOWN` por falta de evidencia normativa. Los reviewers
  especializados y `feature-delivery` no están disponibles. Faltan las tres
  especificaciones globales `docs/SPEC.md`, `docs/REQUIREMENTS.md` y
  `docs/ACCEPTANCE.md`.
- P23–P26 y la auditoría final aún deben ejecutarse. No commit automático.

### Siguiente acción exacta

Leer completamente `prompts/23_SECURITY_HARDENING.md`, inspeccionar el estado
real de seguridad y ejecutar su ciclo de pruebas antes de modificar código.

### Comandos para reanudar

```powershell
$env:DATABASE_URL='postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum'
uv run --frozen python scripts/verify.py
pnpm --dir apps/web e2e
```

## Current snapshot after P23 — 2026-08-17 01:08 -05:00

### Qué quedó terminado

P23 está `done`. Se incorporaron threat model, matriz IDOR/BOLA, hardening
SSRF con DNS/redirect validation y límites, rate limiting de mutaciones,
headers de seguridad, almacenamiento privado de artefactos endurecido,
guards/trigger de inmutabilidad del audit log, secret scan, SAST, workflow de
auditoría, provisión de roles mínimos y runbook. La dependencia `pypdf` fue
actualizada de 6.10.0 a 6.16.1 después de remediar hallazgos de `pip-audit`.

### Verificaciones que pasaron

- `scripts/verify.py` con PostgreSQL: PASS; 131 backend passed, 1 skip
  esperado, 33 frontend passed; invariantes, OpenAPI/cliente, migraciones,
  Django, Ruff, formato, mypy, ESLint y TypeScript PASS.
- Security hardening/history/identity: 34 passed y 10 subtests; parser PDF
  focalizado con pypdf 6.16.1: 23 passed y 1 skip esperado.
- Secret scan, SAST, `pip-audit==2.9.0`, `uv pip check`, `pnpm audit` y
  `git diff --check` PASS. La auditoría de dependencias no reporta
  vulnerabilidades conocidas tras la actualización.

### No quedó terminado / riesgos

- No quedan hallazgos Critical/High resolubles dentro del repositorio. MFA/IdP
  institucional, antimalware gestionado, egress de red y rotación operativa
  de secretos quedan como prerrequisitos externos documentados.
- B1 sigue `UNKNOWN` por falta de snapshot normativo archivado; no se
  publican inferencias. Siguen ausentes globalmente `docs/SPEC.md`,
  `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md`.
- Los reviewers/subagentes y Skills especializados no están expuestos en la
  sesión; se dejó revisión manual read-only. No se creó commit automático.

### Siguiente acción exacta

Leer completamente `prompts/24_DEPLOYMENT_DR.md`, sus referencias y el estado
real de CI/CD, backups, restore y despliegue antes de comenzar P24.

### Comandos para reanudar

```powershell
$env:DATABASE_URL='postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum'
uv run --frozen python scripts/verify.py
uv run --frozen python scripts/scan_secrets.py
uv run --frozen python scripts/sast.py
pnpm --dir apps/web build
pnpm --dir apps/web e2e
```

## Authoritative latest snapshot (EOF) — 2026-08-17 10:46 -05:00

La auditoría completa está en `docs/audit/FINAL_AUDIT_2026-08-17.md` y el
veredicto continúa `NOT_READY`; este bloque es la referencia más reciente.

- PASS estático: deployment assets, state recovery (`27 done`, `8
  in_progress`, sin errores), anti-MVP (`196` archivos/14 contextos/0 issues),
  TODO release gate (`files_scanned=508`, `functional_hits=0`), docs clone-clean,
  baseline, secret scan, source watch offline, invariantes
  curriculares, OpenAPI breaking diff, JSON y `py_compile` del mantenimiento DB.
- PASS histórico conservado: backend 131 passed/1 skip, Vitest 33/33,
  Playwright 50/50 y axe 20/20; no sustituye rerun post-P24–P99.
- Bloqueado: `scripts/verify.py` completo, SAST con Python 3.14, Django,
  pnpm lint/typecheck/test/build/E2E, cliente generado, Docker/PostgreSQL,
  migraciones/restore/smoke, source watch remoto, resolución Next, reviewers
  y pruebas manuales de accesibilidad. También falló el intento no destructivo
  `uv python install 3.14 --install-dir .uv-python` por `WinError 10013` al
  descargar desde GitHub; no quedó un runtime alternativo instalado.
- P24–P26, P90–P92, P94 y P98 siguen `IN_PROGRESS`; P93/P95/P99 están cerrados
  en sus alcances. El Goal no se marca completo.
- Acción exacta: usar un runner con Python 3.14+Django+uv, Node/pnpm reparable,
  Docker/PostgreSQL y red; ejecutar los comandos canónicos de
  `docs/ACCEPTANCE.md`, iniciar API/web y repetir la matriz.
- `.codex/STATUS.md` no se pudo escribir por la ACL de sólo lectura de esa
  ruta en esta sesión; la trazabilidad equivalente quedó en este archivo,
  `ROADMAP_STATUS.json`, `SESSION_LOG.md`, `RISKS.md`, `OPEN_DECISIONS.md` y
  la auditoría final.

## Authoritative latest snapshot (EOF) — 2026-08-17 11:56 -05:00

Durante esta continuación se cerraron hallazgos reproducibles de las
revisiones de arquitectura, seguridad, código y UX, sin marcar los gates de
runtime como verdes:

- Inmutabilidad curricular: `RequirementGroup`, `PlanMembership` y
  `Requirement` validan y bloquean mutaciones de revisiones publicadas,
  superseded o retired; se añadieron triggers PostgreSQL para filas hijas,
  enlaces de evidencia y scopes de malla. `PlanMembership` también rechaza
  cursos de otra institución.
- Integridad multi-programa/multi-sede: se añadieron migraciones de triggers
  para membership, grupos, términos, ofertas, matrículas y course attempts;
  términos, perfiles y attempts ejecutan `full_clean()` en el guardado.
- Seguridad: MFA privilegiado continúa fail-closed y sólo consume la marca de
  sesión del adaptador IdP; la composición de producción la pasa explícitamente.
  Se reforzó el alcance editorial por institución/programa, se bloqueó la
  edición administrativa de `RoleAssignment`, y se rechazaron rangos IP no
  globales en el fetcher SSRF.
- Operaciones: backup/restore nunca ponen contraseñas en `argv`, el restore
  falla si no puede eliminar su base temporal, valida tablas críticas, y el
  preflight exige imágenes por digest, roles de base separados, secreto real y
  MFA. Todas las GitHub Actions ahora están ancladas a commits de 40
  caracteres y `scripts/check_action_pins.py` quedó en `scripts/verify.py`.
- UX: el centro de notificaciones restaura foco al disparador y enfoca el
  encabezado al abrir; la alternativa textual del grafo conserva nodos de
  condición y relaciones visibles; el live region del backoffice ya no cubre
  todo el detalle; se homogeneizaron encabezados internos en español.

### Verificaciones de esta continuación

- PASS: `py_compile` de todos los archivos Python modificados que no requieren
  sintaxis exclusiva de 3.14; `scripts/check_action_pins.py`; deployment
  assets; secret scan; docs clone-clean; state recovery; TODO release gate
  (`functional_hits=0`); anti-MVP (`196` archivos, `0` issues); curriculum
  invariants; OpenAPI breaking diff; operational helper assertions; y
  `git diff --check`.
- PASS focalizado estático: `scripts/verify.py` llega a todos los checks,
  incluyendo el nuevo action-pin gate; no se ocultaron errores ni se
  degradaron aserciones.
- BLOQUEADO/NO PASS actual: SAST requiere Python 3.14; `uv` no puede iniciar
  el entorno; Django, pytest, migraciones, Ruff y mypy no son ejecutables;
  Node/pnpm no puede abrir los binarios bajo `node_modules` por `EPERM`; falta
  `openapi-typescript` accesible; Docker/PostgreSQL/Compose no están
  disponibles. Los resultados históricos 131/1 backend, 33 Vitest, 50/50 E2E
  y 20/20 axe siguen etiquetados como históricos, no como rerun posterior a
  estas modificaciones.

### Siguiente acción exacta

En un runner autorizado con Python 3.14, uv/Django, Node/pnpm reparables,
Docker Engine, PostgreSQL y Chromium: ejecutar primero `uv run --frozen
python scripts/verify.py`, después migraciones/checks/tests backend, lint,
typecheck/build/frontend, integración, E2E/axe, backup/restore/smoke y
Compose/production preflight; resolver regresiones y actualizar esta matriz.

`.codex/STATUS.md` sigue sin ser editable por la ACL de esta sesión; no se
intentó forzarla y este bloque es la trazabilidad equivalente permitida.

## Authoritative latest snapshot (EOF) — 2026-08-17 12:18 -05:00

Se corrigió un defecto de configuración descubierto en la última revisión del
workflow: el servicio PostgreSQL de `production-gates.yml` crea
`curriculum_runtime`, por lo que su healthcheck, migration gate y canonical
verification ahora usan ese mismo usuario. El job separado de restore conserva
su usuario `curriculum`, que sí es el que crea explícitamente en su contenedor.

Verificaciones estáticas repetidas después de la corrección:

- `scripts/check_action_pins.py` PASS.
- `scripts/verify_deployment.py` PASS.
- `scripts/check_no_todos.py` PASS: `files_scanned=525`,
  `functional_hits=0`.
- `scripts/anti_mvp_audit.py` PASS: `product_files_scanned=200`,
  `bounded_contexts=14`, `anti_mvp_issues=0`.
- `scripts/validate_curriculum.py`, `scripts/verify_docs_clone_clean.py`,
  `scripts/source_freshness.py --offline`, `scripts/verify_state_recovery.py`,
  `scripts/scan_secrets.py`, `git diff --check` y `py_compile` focalizado PASS.

El verificador canónico se ejecutó completo y continúa en FAIL honesto: SAST
necesita Python 3.14 para parsear seis archivos válidos del proyecto; `uv` no
puede iniciar por WinError 5; los binarios Node bajo `node_modules` devuelven
EPERM; falta `openapi-typescript` accesible; y Docker/PostgreSQL no están
disponibles. No se reclasificó ningún gate bloqueado como PASS.

Siguiente acción exacta: en un runner autorizado, ejecutar primero
`uv run --frozen python scripts/verify.py` y después la matriz de
`docs/ACCEPTANCE.md`, incluyendo Django/PostgreSQL/migraciones, cliente
OpenAPI, lint/typecheck/build/Vitest, Playwright/axe, Docker/Compose,
backup/restore, smoke e integración; corregir regresiones y actualizar la
matriz antes de cerrar el Goal.

`.codex/STATUS.md` sigue sin poder editarse por la ACL de sólo lectura de la
ruta; el detalle equivalente está actualizado aquí, en `ROADMAP_STATUS.json`,
`SESSION_LOG.md`, `RISKS.md`, `OPEN_DECISIONS.md` y las auditorías.

## Authoritative latest snapshot (EOF) — 2026-08-17 13:08 -05:00

Se completó una auditoría interactiva en la sesión real de Chrome, primero
como administrador y luego como estudiante, observando simultáneamente la
consola del navegador y las respuestas de la aplicación. Se recorrieron las
rutas principales, se probaron escrituras reales y se corrigieron los defectos
reproducibles encontrados.

### Terminado

- La portada y la navegación ahora dependen de capacidades y perfil: un
  administrador editorial puro no cae en onboarding estudiantil, y la malla es
  la acción principal tanto en el inicio editorial como en el estudiantil.
- La malla invalida de forma coherente una selección que queda fuera de los
  filtros y explica el estado, sin mostrar simultáneamente cero resultados y
  el detalle de un curso oculto.
- Se eliminó el hydration mismatch real del tablero de planificación.
- Historia académica dejó de ser una superficie placeholder: permite crear,
  editar y anular intentos, registra recursadas con `attempt_number`, recupera
  todas las páginas y reserva `ANNULLED` para la operación auditable. El backend
  también rechaza crear o actualizar directamente ese estado.
- Importación de historia incorpora carga, preview, reconciliación y
  confirmación; valida 10 MiB en cliente, limpia el payload según decisión,
  permite mapear `ACCEPT`, exige nota en conflictos, mejora semántica accesible
  y usa `If-Match` para impedir confirmaciones obsoletas.
- La confirmación/resolución de importaciones bloquea lote y candidatos en
  orden estable. Las respuestas privadas relevantes usan `private, no-store`.
- `/sources` nunca cae al backoffice ante un fallo público; estudiantes ven
  procedencia pública y roles editoriales conservan gobernanza.
- En Chrome real se verificaron login/logout, separación admin/estudiante,
  malla, auditoría, grafo, oferta, planificación, analítica, historia,
  importación y fuentes. También se creó un escenario, se agregó un curso y se
  creó/anuló un intento académico sintético para validar escrituras y auditoría.

### Verificaciones finales

- `python scripts/verify.py`: `PASS`.
- Backend: `149 passed`, `1 skipped` esperado para trigger exclusivo de
  PostgreSQL; Django checks, migraciones, Ruff, formato y mypy pasan.
- Frontend: ESLint y TypeScript pasan; Vitest `15` archivos / `39` pruebas.
- OpenAPI y cliente TypeScript generado están sincronizados y el diff de
  contrato no introduce ruptura.
- Secret scan, SAST, deployment assets, action pins, documentación, estado,
  TODO release gate, anti-MVP e invariantes curriculares pasan.
- Revisiones read-only de seguridad, UX y código: `0 Critical`, `0 High`. La
  revisión final de código se repitió después de cerrar la vía backend de
  `ANNULLED`, el refresh de versión tras reconciliar y el retry idempotente de
  confirmación.

### No terminado / riesgos vivos

- La prueba de navegación bajo carga se ejecutó contra servidores de desarrollo:
  una primera ronda tuvo latencias de aproximadamente 5,8 s promedio, un máximo
  de 12 s y un timeout de navegación. El recorrido posterior quedó funcional y
  sin nuevos errores de consola, pero esto no sustituye carga contra build de
  producción, PostgreSQL y observabilidad desplegada.
- El parser PDF continúa siendo síncrono y necesita aislamiento por proceso/job
  con límites de memoria y tiempo para cerrar el riesgo DoS.
- `raw_payload` de importación requiere política explícita de allowlist/redacción
  y retención para minimizar PII.
- La recuperación completa de historia usa offsets; una inserción concurrente
  durante el recorrido puede duplicar u omitir filas. Debe evolucionar a cursor
  estable o snapshot.
- La reconciliación de importación aún expone algunos enums y JSON técnico; debe
  traducirse y resumirse por fila/campo, dejando el detalle en un disclosure.
- Docker/Compose, restore drill y carga E2E en un entorno de producción siguen
  siendo gates de P24/P25, no cubiertos por esta sesión de Chrome local.

### Siguiente acción exacta

Ejecutar el build standalone con PostgreSQL y Compose, correr Playwright/axe y
la prueba de carga instrumentada contra ese build, completar el restore drill,
aislar el parser PDF y aplicar minimización/retención a `raw_payload`. No se
creó commit, no se hizo push y no se desplegó.

## Authoritative latest snapshot (EOF) — 2026-08-17 16:20 -05:00

Se completó una segunda aceptación real en la sesión de Chrome del usuario con
una persona académica nueva y persistida, no con mocks del frontend. Los datos
representan un caso sintético de aceptación y no se presentan como historia
oficial de la Universidad Nacional.

### Terminado

- Se habilitó el acceso operativo local del administrador y su enlace explícito
  a la administración de estudiantes y matrículas. Las credenciales se entregan
  sólo en la conversación y no se guardaron en archivos versionados.
- Se creó una cuenta estudiantil nueva del plan 2514, seis períodos académicos,
  una matrícula activa y 23 intentos persistidos: 20 aprobados y 3 en curso.
- El motor calculó en vivo 70/141 créditos aplicados, 21 cursos matriculables,
  una obligatoria pendiente y ocho estados por verificar.
- Se creó y persistió el escenario `Sexto semestre · ruta 2026-2S`. La prueba
  visual detectó que el selector podía enseñar el curso 1000013 pero enviar el
  identificador previo; se corrigió la selección derivada y el escenario quedó
  con `1000013 · Probabilidad y estadística fundamental`.
- El planificador limita el selector a períodos abiertos/planeados o períodos
  históricos ya usados. La gramática del resumen distingue singular y plural.
- La malla abre directamente la ruta obligatoria y expone 20 aprobadas, 3 en
  curso, 21 matriculables, 32 bloqueadas y 21 por revisar sin portada ornamental.
- El grafo traduce estados, condiciones, relaciones, epistemología y severidad;
  la consola fresca no registra advertencias ni errores de producto.
- Historia valida que la asignatura manual pertenezca al catálogo del plan;
  importación usa `revisión previa` en lenguaje público y reserva datos técnicos
  para trazabilidad secundaria.
- La redacción de impactos de publicación impide que EDITOR reciba UUID, hashes
  o jobs individuales y conserva el detalle autorizado para REVIEWER/ADMIN.

### Evidencia final

- `python scripts/verify.py` → `PASS`.
- Backend: `149 passed`, `1 skipped` esperado para trigger PostgreSQL.
- Frontend: Vitest `15` archivos / `43` pruebas; suite focalizada de UX `22/22`;
  planificador final `5/5`; ESLint y TypeScript pasan.
- Ruff, formato, mypy, migraciones, Django checks, OpenAPI/cliente generado,
  secret scan, SAST, anti-MVP, TODO gate e invariantes curriculares pasan.
- Chrome real: cuenta nueva autenticada; `/`, `/curriculum`, `/audit`,
  `/history`, `/offerings`, `/planner`, `/analytics`, `/graph` e importación
  recorridas. En la comprobación final de malla, planificador y grafo hubo cero
  alertas visibles, cero overflow del documento y cero mensajes frescos
  `warn/error` de producto en consola.
- Revisores read-only de código, seguridad y UX: `0 Critical`, `0 High`.

### No terminado / riesgos vivos

- El catálogo de períodos del planificador todavía se obtiene globalmente; en
  una instalación multi-institución podría mostrar un período ajeno que el
  backend rechazará. El read model debe exponer institución/campus o proveer un
  endpoint de períodos scoped por matrícula.
- La aceptación se ejecutó sobre servidores locales de desarrollo y SQLite. No
  sustituye el gate production-like con PostgreSQL, build standalone, Compose,
  Playwright/axe móvil y carga instrumentada.
- Continúan los riesgos ya registrados: aislamiento del parser PDF, política de
  minimización/retención de `raw_payload`, paginación estable de historia y
  consolidación de CSS legacy que hoy depende de overrides finales.

### Siguiente acción exacta

Agregar alcance de matrícula/institución al read model de períodos y ejecutar
la matriz production-like completa con PostgreSQL y build standalone. Después,
aislar el parser PDF y cerrar la política de retención. No se creó commit, no se
hizo push y no se desplegó.

## Authoritative latest snapshot (EOF) — 2026-08-17 23:40 -05:00

La aceptación local de administrador y estudiante se completó de extremo a
extremo en Chrome real con una persona sintética persistida de sexto semestre.
No hay mocks ni reglas académicas inventadas en los resultados mostrados.

### Terminado

- La malla es la superficie primaria: abre con estado compacto y ruta
  obligatoria, conserva el desplazamiento sólo dentro del track y no desborda el
  documento a 390 px (`clientWidth=375`, `scrollWidth=375`).
- Administración dispone de alta nativa, búsqueda/paginación remota y resolución
  auditable de matrículas `NEEDS_REVIEW` con `If-Match`, fundamento, período de
  ingreso, estado y vigencia de la revisión. La activación se revalida y bloquea
  transaccionalmente.
- Historia e importación obtienen un contexto privado independiente de la
  auditoría. Una matrícula `NEEDS_REVIEW` puede conservar/corregir hechos mientras
  avance y elegibilidad permanecen explícitamente pausados.
- La confirmación de importación vuelve a validar vigencia temporal bajo locks
  adquiridos en orden global `CourseVersion -> AcademicTerm`; se cerraron TOCTOU
  y deadlocks cruzados con edición manual.
- El parser admite códigos UNAL puramente numéricos. La aceptación real aplicó
  23 candidatos y conserva 23 intentos/evidencias: 20 aprobados, 3 en curso,
  71 créditos reportados y 70/141 aplicados.
- Analítica maneja `NEEDS_REVIEW` sin inventar métricas, compacta bloqueos y deja
  trazabilidad completa bajo demanda. Grafo y estados visibles están traducidos.
- Procedencia pública incorpora búsqueda sobre los fragmentos archivados en vez
  de una lista larga sin navegación.
- El BFF limita cuerpos/respuestas, exige longitud en escrituras, valida formato,
  separa presupuestos auth/estándar/upload, aplica equidad por cliente, timeouts y
  envelopes Problem Details completos.
- Backup y restore drill reales pasaron con snapshot PostgreSQL compartido entre
  `pg_dump` y conteos del manifiesto. Artefacto local:
  `var/backups/curriculum-e2e-20260818T035027Z.dump`.

### Evidencia

- Chrome real: administrador y estudiante autenticados; inicio, malla, historia,
  importación, planificador, auditoría, oferta, analítica, grafo, procedencia y
  administración recorridos; cero `warn/error` de producto en consola final.
- Malla móvil 390x844: sin overflow documental; sólo el track obligatorio tiene
  scroll horizontal interno.
- Backend focal administración/historia/analítica: 36/36 PASS; frontend focal:
  5/5 PASS; TypeScript y ESLint PASS.
- `python scripts/verify.py` canónico: PASS; backend 170 passed + 1 skip
  esperado de trigger PostgreSQL; frontend 16 archivos / 46 pruebas; Ruff,
  formato, mypy, migraciones, OpenAPI/cliente, seguridad y gates documentales PASS.
- Reviewers read-only de arquitectura, código, currículo, seguridad y UX:
  `0 Critical`, `0 High`.

### No terminado / siguiente acción exacta

- P24/P25 permanecen `in_progress`: falta reconstruir y probar la imagen final
  de producción/Compose después de este diff y ejecutar carga instrumentada
  sobre ese artefacto. El restore drill ya no es un bloqueo.
- Antes de escalar a múltiples réplicas, trasladar o documentar el admission
  control global del BFF; hoy es deliberadamente por proceso y Caddy es el único
  ingress.
- Evolucionar el fundamento de resolución curricular desde metadata textual a
  evidencia institucional estructurada cuando exista el proceso documental.
- No se creó commit, no se hizo push y no se desplegó.

## Local bootstrap & administrator acceptance — 2026-08-18

### Terminado

- Se añadió `bootstrap_local_admin`: crea o rota de forma explícita un
  superusuario local sólo con `DJANGO_DEBUG=true` y guarda las credenciales en
  `var/local-admin-credentials.txt`, una ruta ignorada por Git.
- La escritura de credenciales es atómica, con archivo `0600`, directorio
  `0700`, rechazo de symlinks y rollback de identidad si no se puede persistir
  el archivo. README documenta el primer arranque sin versionar contraseñas.
- Se endureció el almacenamiento privado de importaciones frente a `umask` y
  el constructor de comandos de backup volvió a ser testeable sin Docker,
  manteniendo el fallo explícito al ejecutar sin Docker.
- API en `127.0.0.1:8000` y web en `localhost:3000` están activos con SQLite
  de desarrollo porque este host no dispone de Docker. Chrome autenticó
  correctamente a `admin@localhost` y mostró navegación editorial y
  administrativa.

### Verificaciones

- `python scripts/verify.py` → PASS: 173 backend passed, 1 skip esperado del
  trigger exclusivo de PostgreSQL; 16 archivos / 46 pruebas frontend PASS.
- `pnpm --dir apps/web build` → PASS. Health, CSRF, login, `/auth/me` y flags
  Django de superusuario → PASS contra localhost.
- Revisión read-only de código: los High sobre escritura de credenciales y
  consistencia transaccional se resolvieron; no quedan Critical/High abiertos.

### Siguiente acción / riesgo

- Docker no está instalado en este host; sigue pendiente la matriz
  PostgreSQL/Compose P24/P25. Para reanudar: `uv run --project apps/api python
  apps/api/manage.py runserver 127.0.0.1:8000` y `pnpm --dir apps/web dev`.
- Commit local `507df94` creado. El push a `origin/main` quedó pendiente porque
  este host no tiene credenciales HTTPS de GitHub ni `gh` instalado; el branch
  local está `ahead 1`.
