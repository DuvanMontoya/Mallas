# Current State

## Snapshot

P00–P08 están terminados y verificados. El repositorio tiene backend Django modular, frontend Next.js con shell responsive/role-aware y design system accesible, cliente TypeScript generado con frescura comprobable, Compose PostgreSQL, ingestión normativa idempotente, AST/evaluador académico puro, auditoría de grado determinista con ledger de créditos, identidad con ownership/RBAC, sesiones first-party seguras, rate limiting, audit log append-only, historia académica con importación privada, reconciliación y evidencia, y contrato API v1 con errores correlacionables, paginación, concurrencia optimista e idempotencia; todo sobre un núcleo persistente multiinstitución separado del dominio puro. Las capacidades de producto completas todavía se construirán en P09–P26.

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
  python scripts/verify.py                         PASS (60 passed, 1 SQLite skip)
pnpm --dir apps/web build                        PASS
pnpm --dir apps/web e2e                          PASS (2/2)
manage.py check                                  PASS
makemigrations --check --dry-run                 PASS
migrate --check                                  PASS
PostgreSQL Compose + migrate + full tests         PASS (61)
curriculum validation/import/diff                 PASS
rule engine/golden/Hypothesis/benchmark           PASS
degree audit golden/service                       PASS (7 focused; included in 42 PostgreSQL tests)
identity security focused                          PASS (10 SQLite)
student history/API contract focused               PASS (19 SQLite; included in 61 PostgreSQL tests)
SQLite full suite                                  PASS (60 passed, 1 expected skip)
PostgreSQL full suite                              PASS (61)
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
- P08 no deja fallos funcionales pendientes dentro de su alcance. La revisión manual NVDA/VoiceOver queda para releases institucionales; los módulos de dashboard/currículo/oferta aún esperan sus read models de P09 en adelante y muestran estados vacíos honestos.

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

## Siguiente acción exacta

Leer y ejecutar completamente `prompts/10_DASHBOARD_AUDIT_UX.md` (P09): dashboard de estudiante y UX de auditoría.

## Comandos para reanudar

```bash
docker compose -f infra/docker-compose.yml up -d postgres
python scripts/verify.py
pnpm --dir apps/web build
pnpm --dir apps/web e2e
DATABASE_URL=postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum uv run --project apps/api pytest
DATABASE_URL=postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum uv run --project apps/api python manage.py migrate --check
pnpm --dir packages/api-client verify
python scripts/check_openapi_breaking.py --base-revision <git-base-sha>
pnpm --dir apps/web test -- --run
```
