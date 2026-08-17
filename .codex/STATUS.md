# Estado de ejecución de milestones

Este archivo es el registro operativo de la ejecución lexicográfica de `prompts/*.md`.
Un milestone sólo aparece como `done` después de ejecutar sus verificaciones y resolver los fallos reproducibles.

## P00 — Toolchain & repository bootstrap

Estado: `done`

### Implementación realizada

- Resolví y fijé Python 3.14.7, Node.js 24.19.0, pnpm 11.21.0, uv 0.11.19, Django 6.0.8, Django Ninja 1.6.2 y Next.js 16.3.1.
- Registré la incompatibilidad Django 6.1/Django Ninja y la decisión en ADR-0011 y `docs/research/TECHNOLOGY_BASELINE.md`.
- Creé el backend Django modular en `apps/api`, con usuario por correo, migración inicial, configuración segura de desarrollo, health live/readiness y OpenAPI.
- Creé el frontend Next.js App Router en `apps/web`, TypeScript strict, lint, Vitest, Playwright, build standalone y rutas de base para los dominios del producto.
- Creé `packages/api-client` con cliente TypeScript generado desde el contrato OpenAPI y verificación de frescura.
- Creé Compose canónico con PostgreSQL 18.0-alpine, healthcheck, volumen persistente y Dockerfiles no-root para API/web.
- Fijé lockfiles, archivos de versión, workspace pnpm, `pyproject.toml`, Renovate, CI inicial y `scripts/verify.py` como orquestador canónico.
- Actualicé README, documentación de infraestructura y estado permanente. Se inicializó el repositorio Git existente sin crear commit ni modificar historial.

### Pruebas ejecutadas

- `python scripts/verify.py`
- `pnpm --dir apps/web build`
- `pnpm --dir apps/web e2e` (2 proyectos: desktop y mobile)
- `uv run --project apps/api python apps/api/manage.py check`
- `uv run --project apps/api python apps/api/manage.py makemigrations --check --dry-run`
- `uv run --project apps/api python apps/api/manage.py migrate --check`
- `DATABASE_URL=postgresql://... uv run --project apps/api python apps/api/manage.py migrate --noinput`
- `docker compose -f infra/docker-compose.yml config`
- Arranque real de Next standalone y GET `/` (HTTP 200, contenido esperado)
- Arranque real de Django con PostgreSQL y GET `/api/v1/health/live`, `/api/v1/health/ready`, `/api/v1/openapi.json` (HTTP 200)

### Resultados

- Invariantes curriculares: PASS (`courses=102`, `memberships=97`, `requirements=73`).
- OpenAPI fresco: PASS.
- Django checks: PASS; migraciones en SQLite y PostgreSQL: PASS.
- Backend: 3 tests PASS, Ruff PASS, formato PASS, mypy PASS.
- Frontend: lint PASS, typecheck PASS, 1 archivo/1 test unitario PASS, build PASS.
- E2E: 2/2 PASS en desktop y mobile.
- PostgreSQL Compose: contenedor `infra-postgres-1` healthy y conexión de Django verificada.
- Revisión estática de P00: sin TODO/FIXME/stub en el código nuevo de producto. Los reviewers especializados no están disponibles como herramientas en este entorno; se realizó revisión manual de arquitectura/código y se dejó la limitación documentada.

### Problemas pendientes

- P00 no deja problemas funcionales pendientes. El catálogo completo y las reglas de dominio se implementarán en los milestones posteriores; no se inventó lógica académica en este scaffold.
- No se creó un commit Git porque AGENTS.md requiere autorización para commits automáticos.

### Siguiente

Ejecutar estrictamente `prompts/02_DOMAIN_AND_BACKEND_FOUNDATION.md` como P01, comenzando por el dominio puro y sus invariantes.

## P01 — Architecture & domain skeleton

Estado: `done`

### Implementación realizada

- Implementé bounded contexts persistentes para institutions, curriculum, rules, governance, offerings, student_records, imports, planning, audit y optimization, además de los módulos base definidos por AGENTS.
- Añadí `Institution`, `Campus`, `Faculty`, `Program`, `CurriculumPlan`, `CurriculumRevision`, `Course`, `CourseVersion`, `RequirementGroup` y `PlanMembership` con UUID, temporalidad, constraints e índices.
- Separé identidad durable de curso, versión temporal, pertenencia a revisión y oferta; no existe `prerequisite_id` en `Course`.
- Añadí `NormativeDocument`, `SourceSnapshot`, `Evidence`, `NormRelation`, `Requirement`, términos/ofertas/secciones/meetings, historial, reconocimientos, excepciones, escenarios, auditorías y ejecuciones de optimización base.
- Creé `apps/api/domain` con enums y hashing puros, sin imports Django/ORM/settings/network.
- Creé `CurriculumRevisionService` para publish/supersede/retire, guardas de modelo y trigger PostgreSQL para impedir mutación/borrado de contenido publicado.
- Añadí factories, tests de constraints, prueba de separación de identidad y revisión ERD ejecutable en `docs/ERD.md`/`diagrams/domain-model.mmd`.
- Añadí gestión de usuario por email con `UserManager`, configuración HSTS parametrizable y checks de migraciones en `scripts/verify.py`.

### Pruebas ejecutadas

- `uv run --frozen pytest tests/test_domain_foundation.py -q` → 6 passed, 1 skip esperado en SQLite.
- `DATABASE_URL=postgresql://... uv run --frozen pytest -q` → 10 passed, incluyendo el trigger PostgreSQL.
- `python scripts/verify.py` → PASS: invariantes, OpenAPI, checks, migration graph/state, backend tests, Ruff, formato, mypy, lint, typecheck y Vitest.
- `uv run --frozen python manage.py migrate --noinput` desde base SQLite limpia → PASS.
- PostgreSQL 18.0 Compose desde estado limpio → todas las migraciones PASS, `migrate --check` PASS.
- `DJANGO_DEBUG=false ... manage.py check --deploy` con SSL/HSTS explícitos → PASS.
- `git diff --check` → PASS (sólo avisos de normalización LF/CRLF de Git).

### Resultados

- Migraciones limpias desde cero en SQLite y PostgreSQL.
- Invariantes de identidad, temporalidad, rangos, unicidad y publicación verificadas por tests y base de datos.
- La revisión publicada no puede cambiar contenido mediante servicio/modelo ni mediante `QuerySet.update` en PostgreSQL.
- `Course`, `CourseVersion`, `PlanMembership` y `CourseOffering` permanecen separados.
- `apps/api/domain` permanece libre de imports Django.
- `verify.py` queda como gate canónico y pasa.

### Problemas pendientes

- No hay problemas funcionales pendientes de P01.
- El trigger PostgreSQL es intencionalmente no-op en SQLite; la guarda de modelo cubre desarrollo/tests SQLite y el test de trigger se ejecuta contra PostgreSQL real.
- Los reviewers especializados exigidos por el prompt no están expuestos como herramientas en esta sesión; se realizó revisión manual de arquitectura/código y se documentó la limitación.

### Siguiente

Ejecutar `prompts/03_CURRICULUM_INGESTION.md` como P02: ingestión, snapshot, evidencia, validación de schema e inmutabilidad de la revisión curricular sin publicar inferencias.

## P02 — Curriculum source ingestion & governance

Estado: `done`

### Implementación realizada

- Implementé el validador puro del baseline con `schema_version`, fingerprint canónico estable, totales 141/52/61/28, referencias, AST, ciclos y estados epistemológicos.
- Añadí `schemas/curriculum.schema.json` y mantuve la semántica adicional en `modules.imports.application.baseline`; el schema no autoriza publicación.
- Implementé ingestión idempotente del JSON 2514 en una revisión `DRAFT`, con institución/sede/facultad/programa/plan, 102 cursos, versiones temporales, 3 componentes padre, 12 agrupaciones fuente y 97 membresías.
- Verifiqué el PDF archivado contra SHA-256 `9253909e4208304dd0eb141b5c388956d0008bafe4e7b9033f2aabd5225e8bad`, persistí `NormativeDocument`/`SourceSnapshot` y 73 `Evidence` con locators por página.
- Añadí `ChangeProposal` con diff semántico determinista y amplié `ImportBatch` con fingerprint, schema, snapshot, revisión, reporte y diff.
- Conservé las 6 ambigüedades y el requisito externo sin snapshot local como `INFERRED_PENDING_REVIEW`; no se resolvió ninguna regla por intuición.
- Añadí `import_curriculum`, `validate_curriculum` y `diff_curriculum`, reporte Markdown humano y rechazo explícito de ingestas sobre revisiones `IN_REVIEW`, `APPROVED` o `PUBLISHED`.
- Añadí migración de trigger PostgreSQL para incluir `CurriculumRevision.metadata` en la inmutabilidad publicada y documenté el ERD/import workflow.

### Pruebas ejecutadas

- `uv run --frozen python manage.py validate_curriculum --json` → PASS.
- `uv run --frozen python manage.py import_curriculum --json` dos veces → PASS; mismo revision/fingerprint.
- Consulta de persistencia después de reimportar → PASS: 1 batch, 1 proposal, 1 revision, 102 courses, 102 versions, 15 groups, 97 memberships, 74 requirements, 73 evidence, 1 snapshot; estado `DRAFT`.
- `uv run --frozen pytest -q tests/test_curriculum_ingestion.py` → 5 passed.
- `python scripts/verify.py` → PASS: 13 passed + 1 skip esperado en SQLite, Ruff, formato, mypy, lint, typecheck y Vitest.
- PostgreSQL Compose: `migrate --noinput`, `migrate --check` y `uv run --frozen pytest -q` → PASS (15 tests; trigger incluido).
- `manage.py check`, `makemigrations --check --dry-run`, `migrate --check` y `diff_curriculum` contra sí mismo → PASS.
- Revisión manual de arquitectura, curriculum y código en modo solo lectura: sin hallazgos Critical/High reproducibles; los subagentes especializados solicitados por el prompt no están expuestos en esta sesión.

### Resultados

- Los gates de P02 quedan verificablemente satisfechos: import idempotente, distribución crediticia consistente, hash fuente verificado, evidencia asociada a reglas verificables, UNKNOWN preservado y diff estable.
- La ingestión nunca llama al servicio de publicación y no puede tocar una revisión editorial o publicada.

### Problemas pendientes

- El requisito de lengua extranjera tiene URL oficial en el baseline, pero no hay snapshot local de su contenido en el kit; por eso permanece pendiente y no se marca como `VERIFIED`.
- Los reviewers `curriculum-auditor`, `architecture-reviewer` y `code-reviewer` no están disponibles como herramientas; la limitación y la revisión manual quedan registradas.
- No se creó commit Git por la política de AGENTS.md.

### Siguiente

Ejecutar estrictamente `prompts/04_RULE_ENGINE.md` como P03: AST versionado, evaluador determinista, UNKNOWN y trazabilidad.

## P03 — Rule AST & evaluator

Estado: `done`

### Implementación realizada

- Implementé `apps/api/domain/rules/` como núcleo Python puro, sin Django, ORM, red ni LLM.
- Definí AST discriminado y versionado `1.0.0` para `ALL`, `ANY`, `NOT`, cursos aprobados/en curso, correquisito, créditos por grupo/componente, créditos totales, porcentaje, grupo completo, cursos obligatorios, nota mínima, externo, equivalencia y `UNKNOWN`.
- Añadí parser estricto con errores de schema/ruta, serializer canónico, wrapper `schema_version`, hash estable y aliases de API (`parse_ast`, `serialize_ast`, `hash_ast`).
- Añadí `AuditContext`, `RevisionFacts`, `EvaluationResult`/árbol de explicación, hechos utilizados, progreso, referencias de evidencia y estados `SATISFIED`, `UNSATISFIED`, `UNKNOWN`, `NOT_APPLICABLE`.
- Formalicé composición ALL/ANY/NOT; toda aritmética de créditos y porcentajes usa enteros, incluido el umbral exacto 112/113 para 80% de 141.
- Añadí análisis puro de dependencias directas/ciclos, benchmark reproducible y persistencia de `Requirement.ast_schema_version`.
- Integré el parser/hash versionado en la ingestión curricular y amplié `schemas/requirement.schema.json` con los nodos del motor.

### Pruebas ejecutadas

- `uv run --frozen pytest -q tests/test_rule_engine.py` → 10 passed.
- Tests focalizados combinados de ingestión + motor → 15 passed.
- `python scripts/verify.py` → PASS: 24 passed + 1 skip esperado en SQLite, Ruff, formato, mypy, lint, typecheck y Vitest.
- Hypothesis: propiedades de porcentaje exacto, round-trip/hash y determinismo → PASS.
- Golden cases `data/fixtures/golden_rule_cases.json` → PASS (12 casos).
- `uv run --project apps/api python scripts/benchmark_rules.py` → PASS, 7.300 evaluaciones, ~44.58 µs/evaluación en este entorno.
- PostgreSQL Compose: migración `rules.0003` y suite completa → PASS (25 tests).
- `manage.py check`, `makemigrations --check --dry-run`, `migrate --check` y revisión de imports puros → PASS.
- Revisión manual architecture/code/curriculum: sin Critical/High reproducible; subagentes especializados no están expuestos en esta sesión.

### Resultados

- Los gates P03 quedan satisfechos: no hay imports Django en el evaluador, 112 no satisface 80% y 113 sí, ALL/ANY/UNKNOWN están formalmente cubiertos, el round-trip conserva hash/semántica y los golden/Hypothesis pasan.

### Problemas pendientes

- `NOT_APPLICABLE` requiere que la capa de aplicación lo marque explícitamente en `AuditContext`; el motor no lo infiere por ausencia de datos.
- No se creó commit Git por la política de AGENTS.md; los reviewers especializados siguen sin estar disponibles como herramientas.

### Siguiente

Ejecutar estrictamente `prompts/05_DEGREE_AUDIT.md` como P04: auditoría de grado, asignación determinista de créditos y trazabilidad.

## P04 — Degree audit & credit allocation

Estado: `done`

### Implementación realizada

- Implementé `apps/api/domain/audit/engine.py` como motor Python puro y determinista con `AuditInput`, `AuditContext`, `AuditResult`, snapshots de revisión, `CreditLedger`, `CreditAllocation`, componentes, agrupaciones, requisitos de grado, `remaining_requirements` y `next_unlocks`.
- Resolví intentos aprobados, intentos en curso, repeticiones, cursos reconocidos, créditos de homologación, excepciones aprobadas y estados `UNKNOWN` mediante hechos explícitos; cada curso se procesa una sola vez.
- Separé `earned_credits`, `applied_credits` y `unapplied_credits`; el exceso de un curso 4cr que completa un bucket 3cr no se reasigna automáticamente.
- Modelé `FREE_ELECTIVE` como bucket abierto explícito: recibe cursos sin bucket elegible o electivos cuyos buckets explícitos ya están completos, conservando la trazabilidad de la política de asignación.
- Evalué grupos, componentes y requisitos no crediticios de graduación sin convertir un porcentaje de créditos en graduación; el requisito externo B1 queda en el AST y puede resultar `UNKNOWN` sin sumar créditos.
- Añadí reconocimiento de créditos a `AuditInput` y el servicio de aplicación prepara fuentes/credits reconocidos, excepciones y snapshots desde ORM.
- Implementé `modules.audit.application.services.run_degree_audit`, que persiste transaccionalmente `DegreeAuditRun`, `DegreeAuditResult` y `CreditAllocation` con fingerprints de historia/excepciones, hash de revisión, versión del motor, snapshot de entrada y hash reproducible del resultado.
- Añadí fixture golden completo de 2514 y cobertura de homologaciones, excepciones, duplicados, plan completo, requisito externo desconocido, hash estable, Hypothesis y persistencia del servicio.
- Registré la implementación en `docs/06_DEGREE_AUDIT_SPEC.md`.

### Pruebas ejecutadas

- `uv run --frozen pytest -q tests/test_degree_audit.py tests/test_degree_audit_service.py` → 7 passed.
- `uv run --frozen ruff check domain/audit modules/audit tests/test_degree_audit.py tests/test_degree_audit_service.py` → PASS.
- `uv run --frozen ruff format --check domain/audit modules/audit tests/test_degree_audit.py tests/test_degree_audit_service.py` → PASS.
- `uv run --frozen mypy domain/audit modules/audit` → PASS.
- `uv run --frozen python scripts/verify.py` → PASS: 31 passed + 1 skip esperado en SQLite; invariantes, OpenAPI, Django checks, migraciones, Ruff, formato, mypy, lint, typecheck y Vitest.
- `DATABASE_URL=postgresql://... uv run --frozen python manage.py migrate --noinput` y `migrate --check` → PASS; no había migraciones pendientes.
- `DATABASE_URL=postgresql://... uv run --frozen pytest -q` → 32 passed en PostgreSQL 18.0, incluyendo el trigger de publicación/inmutabilidad.
- Revisión manual de arquitectura, código y datos curriculares: sin hallazgos Critical/High reproducibles. Los reviewers especializados solicitados por AGENTS no están expuestos como herramientas en esta sesión.

### Resultados

- Todos los gates de P04 están verificablemente satisfechos: no doble conteo, threshold 4/3 con excedente, ledger separado, UNKNOWN material, hash reproducible, homologación/excepción y golden del plan completo 2514.
- El servicio de aplicación conserva explicación y procedencia suficiente para reconstruir auditorías históricas contra la revisión usada.

### Problemas pendientes

- No hay problemas funcionales pendientes de P04 dentro del repositorio. El snapshot documental del contenido externo de B1 sigue siendo un riesgo de gobernanza heredado de P02; el motor lo trata explícitamente como hecho externo y no lo inventa.
- No se creó commit Git porque AGENTS.md exige autorización explícita para commits automáticos.

### Siguiente

Leer y ejecutar estrictamente `prompts/06_IDENTITY_SECURITY.md` como P05: identidad, autenticación, RBAC, privacidad, auditoría de acciones y revisión de seguridad.

## P05 — Identity, auth, RBAC & audit log

Estado: `done`

### Implementación realizada

- Extendí `identity.User` con marcas de verificación de correo y cambio de contraseña; mantuve la cuenta separada de `StudentProfile`.
- Añadí `RoleAssignment` con rol, alcance institucional/programa, vigencia y rationale; añadí `StudentAdvisorAssignment` para delegación explícita y temporal de acceso a historia.
- Implementé sesión first-party de Django con cookies `HttpOnly`, `SameSite=Lax` y `Secure` fuera de DEBUG, invalidación de sesiones después de cambio/reset de contraseña y configuración de secretos/orígenes por entorno.
- Implementé endpoints versionados de CSRF, login, logout, `/me`, reset de contraseña y verificación de correo; los tokens de reset y verificación son purpose-specific, expirables y no enumeran cuentas.
- Centralicé ownership/RBAC: estudiante sólo ve/edita su historia, asesor requiere asignación vigente, editor puede trabajar drafts pero no publicar, reviewer/admin puede publicar y una revisión publicada no es editable.
- Añadí `AuditEvent` append-only con admin de sólo lectura, protección de modelo y trigger PostgreSQL; metadata sensible anidada, identificadores e IP se redactan o almacenan como digest. Añadí `RateLimitBucket` transaccional con manejo de carrera de inserción.
- Añadí middleware de origen/CORS mínimo, CSRF, CSP, Permissions-Policy, COOP, CORP, referrer/content-type protections y `check --deploy` verificable; documenté la frontera MFA en ADR-0012 sin fingir una implementación.
- Actualicé ERD, seguridad, matriz de autorización, `.env.example` y migraciones identity/student_records.

### Pruebas ejecutadas

- `uv run --frozen pytest -q tests/test_identity_security.py` → 10 passed en SQLite.
- `uv run --frozen pytest -q` → 41 passed + 1 skip esperado en SQLite (trigger curricular PostgreSQL-only).
- `DATABASE_URL=postgresql://... uv run --frozen pytest -q` → 42 passed en PostgreSQL 18.0; incluye triggers de publicación y audit log.
- SQLite y PostgreSQL: `manage.py migrate --noinput`, `migrate --check` y `makemigrations --check --dry-run` → PASS; migraciones nuevas `identity.0004` y `identity.0005` aplicadas. La migración `identity.0006` deja SQLite sin trigger para permitir el flush normal de tests; la protección de aplicación y admin permanece.
- `uv run --frozen python scripts/verify.py` → PASS: 41 passed + 1 skip, invariantes curriculares, OpenAPI, Django checks, migraciones, Ruff, formato, mypy, ESLint, TypeScript y Vitest.
- `uv run --frozen python manage.py check --deploy` con `DJANGO_DEBUG=false`, secreto largo, hosts/orígenes explícitos, SSL redirect y HSTS → PASS sin warnings.
- `uv run --frozen python scripts/check_no_todos.py` → 6 hits sólo en documentación/guardas del kit, ninguno en código de producto; `git diff --check` → PASS con warnings de normalización LF/CRLF de Git únicamente.
- OpenAPI export/check y cliente TypeScript generado → PASS; revisión manual de seguridad, arquitectura y código sin Critical/High reproducible. Los reviewers especializados solicitados por AGENTS no están expuestos como herramientas en esta sesión.

### Resultados

- Los gates de P05 están verificablemente satisfechos: ownership negativo, separación editor/reviewer, revisión publicada inmutable, sesión segura de producción, CSRF/CORS/CSP, rate limiting, audit events y ausencia de secretos reales en el repositorio.
- La inmutabilidad del audit log no depende sólo del ORM: las actualizaciones/borrados bulk también fallan en PostgreSQL. En SQLite la guarda de modelo/admin cubre las rutas de aplicación y los tests directos del trigger se ejecutan sólo contra PostgreSQL. `AuditEvent.actor` es `PROTECT` para evitar que un borrado de cuenta modifique evidencia; la eliminación/anonymización futura debe pasar por un workflow de retención dedicado.

### Problemas pendientes

- MFA para roles privilegiados no se inventó en P05: la frontera, controles temporales y condición de salida están documentados en `docs/adr/0012-session-auth-and-privileged-mfa-boundary.md`; el hardening dedicado P23 debe implementar o validar TOTP/WebAuthn antes de producción institucional.
- B1 externo continúa pendiente por falta de snapshot normativo local, heredado de P02; no afecta la autorización de identidad y el motor mantiene `UNKNOWN`.
- No se creó commit Git porque AGENTS.md exige autorización explícita para commits automáticos.

### Siguiente

Leer y ejecutar estrictamente `prompts/07_STUDENT_HISTORY_IMPORTS.md` como P06: historia académica, importaciones, validación, deduplicación, privacidad y trazabilidad.

## P06 — Student history & imports

Estado: `done`

### Implementación realizada

- Implementé el parser puro versionado `student-history/1.0.0` para CSV/JSON y un parser PDF text-only con `pypdf` 6.10.0. La normalización conserva estado oficial, errores/warnings por fila, fingerprints, confidence, locators y metadata de página/línea; PDF siempre requiere confirmación.
- Añadí `RawArtifact`, `CandidateRecord`, `Reconciliation` e `ImportEvidence`, además de enrollment/creador/fingerprints/confirmación en `ImportBatch`, con migraciones y constraints de unicidad, confianza, tamaño y lineage.
- Implementé almacenamiento privado fuera de media pública con límite 10 MiB, extensión/MIME/firma/UTF-8/NUL checks, rechazo de ejecutables/archivos comprimidos, nombres seguros, containment path y metadata `never-executed`.
- Implementé preview/import idempotente por enrollment + SHA-256, resolución explícita `ACCEPT`/`EXTERNAL`/`SKIP`, detección de conflictos por curso/período/número de intento, códigos externos con reconocimiento, errores bloqueantes y confirmación transaccional sin overwrite.
- Implementé CRUD manual de `CourseAttempt` con ownership/RBAC backend, validación de institución/estado/nota/créditos, origen/usuario, actualización de campos permitidos y anulado auditable; cada mutación confirmada recalcula la auditoría de grado y escribe `AuditEvent`.
- Añadí endpoints autenticados `/api/v1/history/imports` y `/api/v1/history/attempts`, schemas Ninja, contrato OpenAPI y cliente TypeScript regenerado. Actualicé documentación de historia, importadores, seguridad y ERD.

### Pruebas ejecutadas

- `uv run --frozen pytest -q tests/test_student_history.py` → 12 passed en SQLite.
- `DATABASE_URL=postgresql://... uv run --frozen pytest -q tests/test_student_history.py` → 12 passed en PostgreSQL 18.0.
- `uv run --frozen pytest -q` → 53 passed + 1 skip curricular esperado en SQLite.
- `DATABASE_URL=postgresql://... uv run --frozen pytest -q` → 54 passed en PostgreSQL 18.0.
- SQLite/PostgreSQL: `manage.py migrate --noinput`, `migrate --check` y `makemigrations --check --dry-run` → PASS; migraciones `student_records.0004`, `imports.0004`, `imports.0005`, `imports.0006` e `identity.0006` aplicadas.
- `uv run --frozen ruff check`, `ruff format --check` y `mypy config modules domain tests` → PASS.
- `uv run --project apps/api --frozen python scripts/verify.py` → PASS: 53 passed + 1 skip esperado; invariantes, OpenAPI freshness, Django checks/migration state, Ruff, format, mypy, ESLint, TypeScript y Vitest.
- `python scripts/export_openapi.py`; generación y verificación de `packages/api-client` → PASS.
- Revisión manual read-only de parser, storage, ORM, autorización, transacciones y API sin hallazgos Critical/High reproducibles. Los reviewers especializados exigidos por AGENTS no están expuestos como herramientas en esta sesión.

### Resultados

- Los gates de P06 están verificablemente satisfechos: reimportación sin duplicados, conflictos no sobrescritos, PDF pendiente hasta revisión, aislamiento entre usuarios, errores por fila explicables, evidencia de procedencia y auditoría actualizada después de confirmar.
- La confirmación bloquea errores o decisiones pendientes, serializa el batch por fila base en PostgreSQL, y revierte la mutación de historia si falla el recálculo.

### Problemas pendientes

- No hay fallos funcionales pendientes dentro del alcance de P06. El hardening de malware scanning externo y MFA de roles privilegiados sigue siendo alcance de P23/operación institucional, no se simula en el importador.
- B1 externo continúa pendiente por falta de snapshot normativo local, heredado de P02; el motor mantiene `UNKNOWN`.
- No se creó commit Git porque AGENTS.md exige autorización explícita para commits automáticos.

### Siguiente

Leer y ejecutar estrictamente `prompts/08_API_CONTRACT.md` como P07: contrato OpenAPI, compatibilidad, errores, paginación, versionado y generación del cliente TypeScript.

## P07 — OpenAPI & generated TypeScript client

Estado: `done`

### Implementación realizada

- Consolidé la API v1 con routers por bounded context: `Identity`, `Student history imports`, `Student records` y `Operations`; los imports y los intentos ya no comparten un router monolítico.
- Añadí `ProblemDetails`/`ApiProblemError` con `type`, `code`, `title`, `detail`, `status`, `correlation_id` y `fields`; handlers para validación Ninja/Django, `HttpError`, 404, permisos y errores inesperados; el servidor devuelve `X-Request-ID` correlacionable y detalles seguros.
- Documenté y probé autenticación de sesión, CSRF (`/auth/csrf` + `X-CSRFToken`), origin policy, códigos de error y respuestas estándar en todas las operaciones OpenAPI.
- Implementé paginación determinista de `/history/attempts` con `limit`, `offset`, `status`, `sort`, metadatos de página, filtros validados y ordenamientos con desempates estables.
- Implementé optimistic concurrency: recursos mutables exponen `version`, mutaciones devuelven `ETag`, y `If-Match` obligatorio produce `428 PRECONDITION_REQUIRED` o `409 STALE_RESOURCE` bajo carrera.
- Implementé `Idempotency-Key` para importaciones, con validación, serialización por enrollment, persistencia/indexación, replay seguro del mismo contenido y rechazo `409 IDEMPOTENCY_KEY_REUSED` para contenido distinto.
- Añadí detector estructural de breaking changes (`scripts/check_openapi_breaking.py`), comparación contra revisión base en CI y frescura exacta del cliente mediante regeneración en memoria.
- Regeneré `artifacts/openapi.json` y `packages/api-client/src/generated.ts` con `openapi-typescript` 7.13.0 + `openapi-fetch` 0.17.0; `scripts/verify.py` ahora ejecuta también la verificación del cliente.
- Actualicé `docs/16_API_CONTRACT.md`, `docs/30_API_AND_DATA_VERSIONING.md`, ADR-0005, README y `.env.example`.

### Pruebas ejecutadas

- `uv run --frozen pytest -q tests/test_openapi_contract.py tests/test_student_history.py` → 19 passed en SQLite.
- Suite SQLite: `python scripts/verify.py` → PASS: 60 passed + 1 skip esperado para el trigger curricular exclusivo de PostgreSQL; invariantes, OpenAPI, breaking-diff self-check, checks/migraciones, Ruff, formato, mypy, cliente generado, ESLint, TypeScript y Vitest.
- `pnpm --dir packages/api-client generate` + `pnpm --dir packages/api-client verify` → PASS; el cliente coincide byte a byte con el OpenAPI archivado.
- `uv run --frozen python ..\..\scripts\check_openapi.py` → PASS; `check_openapi_breaking.py` self-check → PASS.
- PostgreSQL 18.0 Compose healthy; `manage.py migrate --noinput`, `makemigrations --check --dry-run` y `migrate --check` → PASS; migraciones `identity.0006`, `student_records.0004` e `imports.0007` aplicadas.
- Suite PostgreSQL: `DATABASE_URL=postgresql://... uv run --frozen pytest -q` → 61 passed, incluidos trigger PostgreSQL, CSRF, paginación, idempotencia y concurrencia.
- Revisión manual read-only de arquitectura, contrato, código y seguridad: sin hallazgos Critical/High reproducibles. Los subagentes `code-reviewer` y `architecture-reviewer` solicitados por el prompt no están expuestos como herramientas en esta sesión.

### Resultados

- Los gates P07 quedan verificablemente satisfechos: no hay DTOs API duplicados para el contrato generado, generación reproducible, breaking diff ejecutable, errores consistentes, auth/CSRF documentados y `verify.py` comprueba frescura del cliente.
- No quedan fallos funcionales pendientes dentro del alcance de P07. No se creó commit Git porque AGENTS.md exige autorización explícita.

### Problemas pendientes

- La verificación de breaking diff contra una rama base real depende de que CI reciba el SHA de un pull request; el self-check local y el paso de CI quedaron implementados y pasan.
- MFA de roles privilegiados, snapshot normativo B1 y escaneo antimalware externo siguen siendo riesgos heredados/documentados de milestones anteriores, fuera del alcance del contrato API P07.

### Siguiente

Leer y ejecutar estrictamente `prompts/09_FRONTEND_FOUNDATION.md` como P08: fundación frontend, sistema de diseño y shell de navegación.

## P08 — Frontend foundation & design system

Estado: `done`

### Implementación realizada

- Reemplacé el dashboard estático por un App Router shell común, responsive y keyboard-first, con skip link, navegación activa, sidebar desktop, bottom navigation mobile, menú editorial por roles y auth shell separado para `/login`.
- Conecté el shell al cliente OpenAPI real mediante `apps/web/lib/api.ts`: sesión server-side con cookie reenviada al backend, `credentials: include` en navegador, CSRF oficial, login/logout, `ProblemDetails` y estados `authenticated`/`anonymous`/`unavailable`.
- Eliminé valores académicos ficticios de la vista inicial; la UI no calcula ni hardcodea elegibilidad, créditos aprobados, desbloqueos ni graduación. Los componentes reciben hechos ya resueltos por el backend.
- Añadí tokens semánticos claros/oscuros en `globals.css`, `next-themes`, estados redundantes a color, reduced motion, focus-visible, popovers accesibles y responsive mobile/desktop.
- Implementé primitives y componentes presentacionales del design system: `CourseCard`, `CourseStatusBadge`, `RequirementChip`, `ProgressMeter`, `CreditLedger`, `ComponentProgressCard`, `GroupProgressTable`, `EvidencePopover`, `RequirementExplanation`, `CurriculumGrid`, `DependencyGraph` con alternativa textual, `GraphLegend`, `PlannerTermColumn`, `ScenarioCompare`, `OfferingBadge`, `ScheduleGrid`, `AuditWarning`, `UnknownState`, `SourceViewer` y `SemanticDiff`.
- Añadí catálogos i18n `es-CO`/`en`, `safeInternalPath`, `useWorkspaceUrlState`, loading/error/not-found boundaries y una capa única de API sin fetches dispersos.
- Configuré Testing Library/Vitest con `axe-core`, cleanup, alias Vite y worker estable; Playwright verifica shell desktop/mobile, foco por teclado y entrada de autenticación.
- Actualicé docs 13/15/26/27, `.env.example` y ADR-0013 sobre el límite shell/API.

### Pruebas ejecutadas

- `pnpm install --frozen-lockfile` → PASS; workspace de 3 proyectos y dependencia `@curriculum-navigator/api-client` resuelta.
- `pnpm --dir apps/web typecheck` → PASS.
- `pnpm --dir apps/web lint` → PASS.
- `pnpm --dir apps/web test -- --run` → PASS: 4 archivos, 6 tests; axe sin violaciones en shell y componentes base.
- `pnpm --dir apps/web build` → PASS; todas las rutas dinámicas compilan con Next.js 16.3.1.
- `pnpm --dir apps/web e2e` → PASS: 4/4 en desktop y mobile, incluyendo foco del skip link y auth shell.
- `python scripts/verify.py` → PASS: 60 tests backend + 1 skip PostgreSQL-only esperado, cliente OpenAPI fresco, Ruff/format/mypy, ESLint, TypeScript y Vitest.
- Revisión manual read-only UX/código/arquitectura: sin Critical/High reproducibles. El `ux-reviewer` y `code-reviewer` exigidos por el prompt no están expuestos como herramientas en esta sesión.

### Resultados

- Los gates P08 quedan satisfechos: navegación por teclado, axe limpio en componentes base, loading/error/empty consistentes, sin elegibilidad hardcoded, responsive mobile/desktop, auth/role shell, i18n preparada, URL state y tests verdes.
- No quedan fallos funcionales pendientes dentro del alcance de P08. No se creó commit Git porque AGENTS.md exige autorización explícita.

### Problemas pendientes

- La revisión manual con NVDA/VoiceOver queda como actividad de release institucional; axe y Playwright automatizados pasan y la alternativa textual del grafo está preparada.
- El backend aún no expone los read models de dashboard/currículo/oferta; las pantallas de esos módulos muestran estados vacíos honestos y quedan para P09 en adelante, sin datos ficticios.

### Siguiente

Leer y ejecutar estrictamente `prompts/10_DASHBOARD_AUDIT_UX.md` como P09: dashboard de estudiante y UX de auditoría.

## P09 — Student dashboard & audit UX

Estado: `done`

### Implementación realizada

- Implementé el read model backend `GET /api/v1/academic-overview`, autenticado y autorizado por ownership/RBAC, con ETag, ProblemDetails y una sola fuente de verdad para el dashboard. El endpoint reutiliza auditorías persistidas cuando existen y genera una previsualización determinista de solo lectura cuando el estudiante todavía no tiene una corrida guardada.
- Expuse el ledger de créditos requerido/ganado/aplicado/no aplicado y el porcentaje de créditos calculado por el backend, manteniendo explícita la diferencia entre progreso crediticio y graduación. La UI no recalcula elegibilidad, porcentajes, grupos ni cumplimiento.
- Añadí componentes de componentes/grupos, faltantes obligatorios, opciones, requisitos externos, evidencia normativa, advertencias y estados `UNKNOWN`/`NO_HISTORY`/`INCOMPLETE`, con deep links y trazabilidad a snapshot, locator, página, sección y excerpt.
- Añadí elegibilidad backend de cursos (`ELIGIBLE`, `BLOCKED`, `UNKNOWN`, `PASSED`, `IN_PROGRESS`) y próximos desbloqueos conservadores; una regla ausente o ambigua no se convierte en elegibilidad inventada.
- Integré el dashboard en `/` y `/audit`, con responsive desktop/mobile, teclado, axe, disclosure de evidencia y mensaje visible de que 100% de créditos no equivale a graduación si quedan requisitos externos o desconocidos.
- Regeneré OpenAPI y el cliente TypeScript; actualicé el contrato API, arquitectura frontend y ADR-0014 (`academic-overview-read-model`). Añadí fixture de estudiante y servidor de fixture aislado para E2E.

### Pruebas ejecutadas

- `uv run --frozen pytest -q tests/test_academic_overview.py` → 3 passed en SQLite.
- Suite focalizada y completa contra PostgreSQL 18.0 serializada → 3/3 del overview y 64/64 tests totales; Compose PostgreSQL healthy, migraciones y `migrate --check` PASS.
- `python scripts/verify.py` → PASS: 63 passed + 1 skip esperado por trigger PostgreSQL-only; invariantes curriculares, OpenAPI freshness, breaking-diff self-check, Django checks/migrations, Ruff, formato, mypy, cliente generado, ESLint, TypeScript y Vitest 5 archivos/8 tests.
- `pnpm install --frozen-lockfile` → PASS; `pnpm --dir apps/web typecheck` → PASS; `pnpm --dir apps/web lint` → PASS.
- `pnpm --dir apps/web test -- --run` → PASS: 5 archivos, 8 tests; axe sin violaciones. Los avisos de `HTMLCanvasElement.getContext` provienen de jsdom/axe y no producen fallos.
- `pnpm --dir apps/web build` → PASS con Next.js 16.3.1.
- `pnpm --dir apps/web e2e` → PASS: 6/6 desktop/mobile, incluyendo fixture de estudiante, 7/141, UNKNOWN de B1, disclosure de evidencia, disclaimer de graduación, deep link, skip link y auth shell.
- Revisión manual read-only de API, dominio, UX, responsive, accesibilidad y seguridad: sin hallazgos Critical/High reproducibles. Los reviewers `ux-reviewer`, `code-reviewer` y `curriculum-auditor` exigidos por AGENTS no están expuestos como herramientas en esta sesión.

### Resultados

- Los gates de P09 quedan verificablemente satisfechos: no hay graduación falsa por total de créditos, `UNKNOWN` es visible, la evidencia es accesible, la UI consume hechos del backend, los estados sin historial son honestos, la navegación profunda funciona y el flujo principal E2E está verde.
- No quedan fallos funcionales pendientes dentro del alcance de P09. No se creó commit Git porque AGENTS.md exige autorización explícita para commits automáticos.

### Problemas pendientes

- B1 continúa `UNKNOWN` por ausencia de snapshot normativo archivado local; el dashboard lo muestra como requisito externo pendiente y no lo resuelve por inferencia.
- La revisión manual con NVDA/VoiceOver queda como actividad de release institucional; axe, tests de teclado y Playwright desktop/mobile pasan.
- `docs/SPEC.md` y `docs/REQUIREMENTS.md` no existen en el kit original; la revisión final usará los documentos normativos disponibles y dejará registrada esta ausencia.

### Siguiente

Leer y ejecutar estrictamente `prompts/11_CURRICULUM_MAP.md` como P10: mapa curricular interactivo y navegación de la malla.

## P10 — Interactive curriculum map

Estado: `done`

### Implementación realizada

- Implementé el read model backend `GET /api/v1/curriculum-map` con revisión curricular, política de layouts, componentes, agrupaciones, 102 cursos, requisitos AST, evidencia, profundidades de dependencia, desbloqueos directos, oferta por período y deep links. La revisión DRAFT, `UNKNOWN`, `NOT_ASSESSED` y la ausencia de período se conservan explícitamente.
- Apliqué ownership/RBAC para `enrollment_id`, ETag basado en el hash de contenido, ProblemDetails y cliente TypeScript generado desde OpenAPI. El endpoint público no expone estados personales; una matrícula ajena devuelve 403.
- Construí `/curriculum` y `/curriculum/print` con `CurriculumMap`, CourseCard seleccionable, layouts `dependency-depth` y `component-lanes`, filtros de texto/componente/agrupación/estado/créditos/oferta, selección contextual sin flechas masivas, ficha completa, requisitos/evidencia, leyenda accesible, estado móvil vertical, impresión y preferencias URL/localStorage.
- Las opciones `suggested-path` y `user-scenario` permanecen seleccionables y persistibles, pero muestran un aviso explícito y una referencia por profundidad hasta que planificación/escenarios publiquen datos; nunca se representan como semestres oficiales.
- Corregí el empaquetado local del runtime standalone de Next copiando `.next/static` y `public` mediante `apps/web/scripts/prepare-standalone.mjs`; las rutas de producción ya arrancan con sus assets.
- Actualicé `docs/12_UX_INFORMATION_ARCHITECTURE.md`, `docs/13_DESIGN_SYSTEM.md`, `docs/15_FRONTEND_ARCHITECTURE.md`, `docs/16_API_CONTRACT.md` y ADR-0015. El documento `docs/07_CURRICULUM_MAP_SPEC.md` no existe en el kit; se usaron las especificaciones UX, diseño, API, rendimiento, accesibilidad y aceptación disponibles.

### Pruebas ejecutadas

- `uv run --frozen pytest -q tests/test_curriculum_map.py` → 3 passed en SQLite; suite SQLite → 66 passed + 1 skip esperado por trigger PostgreSQL.
- Suite PostgreSQL 18.0 serializada con `DATABASE_URL=postgresql://...` → 67 passed; `migrate --check`, `makemigrations --check --dry-run`, `manage.py check` y `showmigrations` → PASS.
- `uv run --project apps/api --frozen ruff check ...`, formato y `mypy modules/curriculum tests/test_curriculum_map.py` → PASS; el typecheck ejecutado desde la raíz sin `pyproject` falló por configuración fuera de contexto y fue reejecutado desde `apps/api` correctamente.
- Export/OpenAPI freshness, `packages/api-client` generated freshness y breaking-diff self-check → PASS.
- `pnpm --dir apps/web test -- --run` → 6 archivos, 12 tests passed; `pnpm lint` y `pnpm typecheck` → PASS; axe sin violaciones. El único output adicional es el warning conocido de canvas de jsdom/axe.
- `pnpm --dir apps/web build` → PASS con Next 16.3.1 y runtime standalone preparado; `pnpm --dir apps/web e2e` → 8/8 passed en desktop/mobile.
- `uv run --project apps/api --frozen python scripts/verify.py` → PASS: invariantes, 66 tests + 1 skip, OpenAPI, breaking diff, Django, migraciones, Ruff/format/mypy, cliente generado, ESLint, TypeScript y Vitest.
- Seguridad: `pnpm audit --prod --audit-level high`, `uv pip check` y `git diff --check` → PASS; `manage.py check --deploy` con configuración de producción efímera → 0 warnings; escaneo de secretos sólo encontró placeholders/lecturas de variables, y el guard TODO no encontró TODO/FIXME en código de producto.
- Integración real: Compose PostgreSQL healthy; `import_curriculum --json` insertó el baseline auditable como DRAFT (102 cursos, 3 componentes, 12 grupos, 97 membresías, 12 ambigüedades); Django readiness y `/curriculum-map` devolvieron 200/ETag. Next standalone real devolvió `/curriculum` 200 y Chromium verificó 102 tarjetas, selección/ficha y `/curriculum/print`.
- Reviewers `architecture-reviewer`, `code-reviewer`, `curriculum-auditor`, `security-reviewer` y `ux-reviewer`, además de la skill `feature-delivery`, no están expuestos como herramientas en esta sesión; se realizó revisión manual read-only y no se observaron hallazgos Critical/High reproducibles.

### Resultados

- Los gates de P10 están verificablemente satisfechos: la malla es interactiva, responsive, trazable, no confunde layout con semestre, no calcula reglas en frontend, mantiene estados epistemológicos honestos y pasa pruebas unitarias, integración, PostgreSQL, build, E2E, seguridad y flujo real.
- No quedan problemas funcionales pendientes dentro del alcance de P10. No se creó commit Git porque AGENTS.md exige autorización explícita para commits automáticos.

### Problemas pendientes

- B1 externo continúa `UNKNOWN` por falta de snapshot normativo archivado; no se publica inferencia.
- MFA privilegiado, scanning antimalware externo y revisión NVDA/VoiceOver siguen documentados para milestones/operación institucional posteriores.
- `docs/SPEC.md` y `docs/REQUIREMENTS.md` no existen en el kit original; deberán declararse en la revisión final junto con la documentación disponible.

### Siguiente

Leer y ejecutar estrictamente `prompts/12_DEPENDENCY_GRAPH.md` como P11: grafo de dependencias y análisis de desbloqueos.

## P11 — Dependency graph & unlock analysis

Estado: `done`

### Implementación realizada

- Implementé una proyección semántica pura del AST de reglas en `apps/api/domain/rules/graph.py`, conservando nodos `COURSE` y `CONDITION`, operadores `ALL`/`ANY`, umbrales crediticios, condiciones no basadas en cursos, correquisitos, equivalencias, `NOT` y `UNKNOWN`. Las relaciones directas, transitivas, rutas cortas y ciclos se calculan sin convertir umbrales en falsas aristas curso→curso ni duplicar reglas.
- Añadí el read model autenticado `GET /api/v1/dependency-graph` con revisión, evidencia, estados epistemológicos, componentes/grupos, relaciones directas, foco contextual, ancestros/descendientes, desbloqueos, rutas explicativas, ciclos y enlaces navegables. Mantiene ETag, ProblemDetails y la frontera de autorización del mapa curricular.
- Regeneré `artifacts/openapi.json` y `packages/api-client/src/generated.ts`; corregí el adaptador frontend para enviar filtros bajo `params.query`, que es el contrato real de `openapi-fetch`, y fijé esa regresión con una prueba específica.
- Construí `/graph` con React Flow cargado de forma diferida, auto-layout ELK, canvas no editable ni arrastrable, filtros/foco, leyenda semántica, panel de rutas, visualización de ciclos y alternativa textual accesible que no depende del dibujo ni del color. Añadí fixture/servidor E2E, pruebas de componentes/axe y documentación/ADR-0016.

### Pruebas ejecutadas

- `uv run --frozen pytest tests/test_dependency_graph.py tests/test_dependency_graph_api.py -q` → 6 passed en SQLite.
- `python scripts/verify.py` → PASS: 72 tests passed + 1 skip esperado por trigger PostgreSQL-only; OpenAPI, cliente generado, checks Django/migraciones, Ruff, formato, mypy, ESLint y TypeScript incluidos.
- Suite PostgreSQL 18.0 serializada → 73 passed; Compose healthy y `migrate --check`/`makemigrations --check` PASS.
- `pnpm test` → 8 archivos, 15 tests passed; `pnpm lint` → PASS; `pnpm typecheck` → PASS; axe sin violaciones. Los avisos de `HTMLCanvasElement.getContext` son del entorno jsdom/axe y no producen fallos.
- `pnpm build` → PASS con Next.js 16.3.1; runtime standalone preparado.
- `pnpm e2e` → 10/10 desktop/mobile con fixture; se verifican condiciones semánticas, foco, alternativa textual y canvas no arrastrable.
- Integración real: Django/PostgreSQL devolvió `/api/v1/dependency-graph?selected=2016379` con 200, ETag, 126 nodos, 87 relaciones y foco; Next standalone en 3101 devolvió `/graph?selected=2016379` 200 y Chromium verificó encabezado, panel de foco `2016379`, alternativa textual, condición y canvas. La petición server-side real quedó confirmada como `GET /api/v1/dependency-graph?selected=2016379`.
- `pnpm audit --prod --audit-level high`, `uv pip check`, `git diff --check` y guard de TODO → PASS. Se realizó revisión manual read-only de arquitectura, código, currículo, seguridad y UX; las herramientas reviewer/skill `feature-delivery` obligatorias no están expuestas en esta sesión.

### Resultados

- Los gates de P11 quedan verificablemente satisfechos: el grafo es una proyección explicable y trazable, distingue relaciones directas/transitivas, conserva condiciones, evita doble conteo semántico, ofrece foco y rutas, es accesible sin depender del canvas, y pasa SQLite/PostgreSQL, contrato, build, E2E y flujo real.
- No quedan fallos funcionales pendientes dentro del alcance de P11. No se creó commit Git porque AGENTS.md exige autorización explícita para commits automáticos.

### Problemas pendientes

- B1 externo continúa `UNKNOWN` por falta de snapshot normativo archivado local; no se publica inferencia.
- La revisión manual con NVDA/VoiceOver y la validación institucional de tecnologías asistivas quedan para release; axe, teclado, textual alternative y Playwright desktop/mobile pasan.
- `docs/SPEC.md` y `docs/REQUIREMENTS.md` no existen en el kit original; se declararán en la revisión final junto con la documentación existente.

### Siguiente

Leer y ejecutar estrictamente `prompts/13_OFFERINGS_SCHEDULES.md` como P12: períodos académicos, oferta, secciones y horarios.

## P12 — Academic terms, offerings, sections & schedules

Estado: `done`

### Implementación realizada

- Extendí el modelo temporal `AcademicTerm → CourseOffering → Section → Meeting` con `SourceSnapshot`, fechas parciales, sesiones alternas, capacidad opcional y restricciones de fechas/intervalos. La oferta no muta ni crea revisiones curriculares.
- Implementé el dominio puro de frescura (`FRESH`/`STALE`/`UNKNOWN`) y conflictos recurrentes exactos con zona horaria/DST, fechas parciales, límites no solapados y resultado `UNKNOWN` para zonas inválidas.
- Añadí `OfferingSourceAdapter`, payload normalizado versionado, importador JSON archivado/idempotente con SHA-256, `retrieved_at`, evidencia, selección temporal de `CourseVersion` y adaptador de referencia SIA que rechaza scraping autenticado.
- Publiqué CRUD administrativo acotado de términos y lecturas públicas de términos/ofertas/secciones/reuniones/schedule evaluation, con ProblemDetails, ETags, autorización por institución y estados independientes `offered`/`eligible`/`schedulable`.
- La capacidad permanece `UNKNOWN` o `REPORTED_NOT_REAL_TIME` salvo declaración explícita de la fuente; la UI muestra fuente, timestamp, frescura, advertencias honestas, grupos, horarios y conflictos. Construí `/offerings` responsive con selección optimista, `ScheduleGrid`, alternativa de comparación y deep links.
- Regeneré OpenAPI/cliente y actualicé contrato, UX, design system, arquitectura frontend, registro de fuentes oficiales y ADR-0017. La investigación oficial documenta el buscador público/FAQ/manual del SIA, calendario de Bogotá y el límite de no automatizar sesiones privadas.

### Pruebas ejecutadas

- `uv run --frozen pytest tests/test_offerings.py -q` → 5 passed; incluye idempotencia, independencia de oferta/elegibilidad, CRUD scoped, capacidad desconocida, conflictos, fechas parciales y timezone `UNKNOWN`.
- `uv run --project apps/api --frozen python scripts/verify.py` → PASS: 77 passed + 1 skip PostgreSQL-only esperado; invariantes, OpenAPI freshness/breaking diff, Django checks, migraciones, Ruff/format/mypy, cliente generado, ESLint, TypeScript y 18 tests Vitest incluidos.
- `pnpm --dir apps/web lint` → PASS; `pnpm --dir apps/web typecheck` → PASS; `pnpm --dir apps/web test` → PASS: 9 archivos, 18 tests, axe sin violaciones funcionales. Los avisos de canvas son del entorno jsdom/axe.
- `pnpm --dir apps/web build` → PASS con Next.js 16.3.1 y standalone preparado; `pnpm --dir apps/web e2e` → PASS: 12/12 desktop/mobile. La primera ejecución expuso y se reparó la selección controlada durante navegación y la espera del grafo lazy.
- PostgreSQL 18.0 local: se aplicó `offerings.0002_source_freshness_and_meeting_dates`; importador real insertó 2 ofertas, 2 grupos, 2 reuniones y un `SourceSnapshot` desde payload archivado; API real devolvió 200/ETag, estados honestos (`OFFERED`, `NOT_ASSESSED`, `UNKNOWN`, `STALE`) y 26 ocurrencias de conflicto; Next standalone + Chromium verificaron `/offerings`, selección de dos grupos y panel de solapamientos.
- `pnpm audit --prod --audit-level high`, `uv pip check`, secret scan, guard TODO/FIXME/XXX y `git diff --check` → PASS; los reviewers especializados y skills `feature-delivery`/`api-change` no están expuestos en esta sesión.

### Resultados

- Los gates de P12 quedan verificablemente satisfechos: la temporalidad está separada del currículo, oferta y elegibilidad no se confunden, la frescura y capacidad no se inventan, los conflictos son exactos, el frontend consume el contrato generado y los flujos SQLite/PostgreSQL/standalone/E2E pasan.
- No se creó commit Git porque AGENTS.md exige autorización explícita.

### Problemas pendientes

- B1 externo continúa `UNKNOWN` por falta de snapshot normativo local; no se infiere.
- La fuente pública SIA queda como referencia y adaptador seguro; una captura institucional autorizada es necesaria para datos actuales. No se automatiza acceso autenticado.
- Revisión manual NVDA/VoiceOver y reviewers especializados no disponibles; axe, teclado y E2E desktop/mobile pasan.
- `docs/SPEC.md` y `docs/REQUIREMENTS.md` no existen en el kit original; se registrará en la auditoría final junto con la documentación disponible.

### Siguiente

Leer y ejecutar estrictamente `prompts/14_PLANNER.md` como P13: escenarios persistentes, planificación accesible y comparación.

## P13 — Planner scenarios

Estado: `done`

### Implementación realizada

- Implementé escenarios persistentes versionados (`PlanScenario`) con ownership
  por matrícula/usuario, estado activo/archivado, nombre, término objetivo,
  preferencias de créditos/disponibilidad/prioridad y sharing privado por
  defecto mediante token revocable.
- Implementé `PlannedCourse` por término, sección opcional, bloqueo explícito,
  consistencia de institución/curso/término y mutaciones protegidas por
  `If-Match`/ETag para no perder ediciones concurrentes.
- Implementé el validador puro `domain.planning.validator`: orden de
  prerrequisitos, correquisitos en el mismo término, requisitos ALL/ANY/NOT,
  equivalencias, créditos desconocidos, oferta/frescura, disponibilidad y
  conflictos exactos de agenda. Los estados no demostrables producen
  `UNKNOWN` y warnings trazables.
- Añadí `ScenarioAuditProjection`, que recalcula la auditoría proyectada sin
  crear `CourseAttempt`, mutar historial real ni cambiar la revisión normativa;
  entradas incompletas generan una proyección `UNKNOWN` explícita.
- Publiqué API autenticada para listar/crear/renombrar/duplicar/archivar,
  comparar escenarios, añadir/mover/bloquear/eliminar cursos y cambiar
  preferencias, más vista pública redacted sólo cuando sharing está activo.
  Regeneré OpenAPI y el cliente TypeScript.
- Construí `/planner` con columnas por término, drag/drop con teclado y
  selector “Mover a”, bloqueo, warnings, auditoría proyectada, comparación,
  duplicación/archivo y panel de privacidad. La UI no evalúa reglas: consume
  hechos del backend. Añadí BFF `/api/v1/[...path]` para que el navegador use
  cookies/CSRF contra el backend interno sin exponer una URL localhost fija.
- Documenté la decisión en ADR-0018 y actualicé contrato API, arquitectura
  frontend, UX y design system. Ajusté `scripts/verify.py` para invocar
  `python -m pytest`, forma reproducible en Windows cuando la política local
  bloquea el ejecutable `pytest`.

### Pruebas ejecutadas

- `uv run --frozen python -m pytest tests/test_planning.py -q` → 6 passed.
- Suite backend canónica desde `apps/api` → 83 passed + 1 skip esperado por
  trigger PostgreSQL-only; `scripts/verify.py` pasa completamente con
  invariantes, Django, migraciones, OpenAPI/breaking diff, Ruff, formato,
  mypy, cliente generado, ESLint, TypeScript y Vitest.
- `makemigrations --check --dry-run`, `migrate --check`, `manage.py check`,
  OpenAPI freshness y `packages/api-client verify` → PASS. PostgreSQL local
  aplicó `planning.0004_plannedcourse_is_locked_plannedcourse_section_and_more`.
- Frontend: 10 archivos/20 tests Vitest + axe, lint, typecheck y Next
  production build/standalone → PASS. Playwright E2E → 14/14 desktop/mobile.
- Seguridad: `pnpm audit --prod --audit-level high` sin vulnerabilidades
  conocidas, `uv pip check`, `git diff --check`, secret scan y guard de
  TODO/FIXME/XXX de producto → PASS.
- Flujo real Django/PostgreSQL: health live/ready 200; login con CSRF 200;
  creación de escenario privada 201 con proyección; listado 200; curso
  planificado 200 con warnings; compartir 200; vista pública redacted 200;
  revocar y comprobar 404; archivar 200. Next standalone en 3101, conectado
  al backend real, devolvió BFF de escenarios 200, health 200 y `/planner`
  200 con contenido de planificador/privacidad.

### Resultados

- Los gates de P13 están verificablemente satisfechos: planificar no altera
  la historia real, el orden de prerrequisitos y la excepción de correquisitos
  son explícitos, el escenario privado es el default, existe alternativa
  accesible al drag/drop y la comparación es clara y scoped.
- No quedan problemas funcionales pendientes dentro del alcance de P13. No se
  creó commit Git porque AGENTS.md exige autorización explícita.

### Problemas pendientes

- B1 externo continúa `UNKNOWN` por falta de snapshot normativo archivado; no
  se publica inferencia. La captura actual de oferta SIA requiere proceso
  institucional autorizado y no se automatiza acceso autenticado.
- NVDA/VoiceOver y reviewers especializados no están expuestos en esta sesión;
  se realizó revisión manual read-only y pasan axe, teclado y E2E desktop/mobile.
- `docs/SPEC.md` y `docs/REQUIREMENTS.md` no existen en el kit original; se
  declararán en la auditoría final junto con la documentación disponible.

### Siguiente

Leer y ejecutar estrictamente `prompts/15_OPTIMIZER.md` como P14, empezando por
`docs/11_PLANNER_OPTIMIZER.md`, `docs/04_RULE_ENGINE_SPEC.md` y las referencias
de optimización que indique el prompt.

## P14 — Constraint optimizer

Estado: `done`

### Implementación realizada

- Implementé `apps/api/domain/optimization/` como motor puro Python con
  `OptimizationInput`/`OptimizationResult` canónicos, serialización estable,
  hash SHA-256 y versión explícita del solver.
- Modelé `x(course, term)` y asignaciones de grupo `y` en OR-Tools CP-SAT con
  restricciones duras para obligatoriedad, grupos, créditos objetivo, límites
  por período, prerrequisitos, correquisitos, oferta, elecciones bloqueadas y
  conflictos de secciones. Los cursos ya aprobados no pueden volver a ser
  programados; una elección bloqueada incompatible se explica como
  `INFEASIBLE`.
- Conservé `UNKNOWN` para reglas, créditos, horarios u ofertas no verificables.
  `ALLOW_UNKNOWN` y `REQUIRE_OFFERED` son políticas explícitas; la API rechaza
  una política inválida con `400 OPTIMIZATION_REQUEST_INVALID`.
- Implementé objetivos lexicográficos en pasadas separadas —`last_term`,
  `unknown_offerings`, `credit_balance`, `preference_penalty`— fijando el
  óptimo de cada pasada, sin pesos mágicos. El límite total, semilla y
  cancelación cooperativa se conservan en la ejecución.
- Extendí `OptimizationRun` con snapshot/hash de entrada, hash de salida,
  versión, estados operativos, objetivos, solución, explicaciones y marcas de
  inicio/cancelación/completitud. Añadí los endpoints de creación, listado,
  detalle y cancelación, OpenAPI y cliente TypeScript generado.
- Añadí `OptimizerPanel` al planificador: polling, cancelación, estado,
  hashes, versión, diferencias de cursos, conflictos, decisiones y supuestos.
  La interfaz no evalúa reglas ni aplica automáticamente la solución.
- Añadí ADR-0019 y actualicé las especificaciones de optimización, API, UX,
  frontend y ERD. Los reviewers/subagentes y la skill `feature-delivery` no
  están expuestos en esta sesión; se realizó revisión manual read-only y se
  corrigió una regresión real del preflight de elecciones bloqueadas.

### Pruebas ejecutadas

- Focalizado optimizer: 11 passed, incluyendo golden de prerrequisito y
  correquisito, política de oferta desconocida, conflicto de horario,
  round-trip/hash, cancelación, regresión de elección bloqueada, curso ya
  aprobado, propiedad Hypothesis y API 400/202/persistencia.
- Suite backend canónica: `uv run --frozen python -m pytest -q` → 94 passed,
  1 skip esperado por trigger exclusivo de PostgreSQL. `scripts/verify.py` →
  PASS con la misma suite, invariantes curriculares, OpenAPI/breaking diff,
  migraciones, Ruff, formato, mypy, cliente generado, ESLint, TypeScript y
  21 pruebas Vitest + axe.
- Migraciones: `optimization.0004_optimizationrun_execution_metadata` se
  aplicó y `manage.py check`, `makemigrations --check --dry-run`,
  `migrate --check` pasaron en SQLite y PostgreSQL local.
- Frontend final: `pnpm --dir apps/web build` → PASS con Next 16.3.1 y
  standalone; Playwright → 14/14 desktop/mobile; lint y typecheck PASS.
- Seguridad/dependencias: `pnpm audit --prod --audit-level high` sin
  vulnerabilidades conocidas, `uv pip check`, `git diff --check`, secret scan
  y `manage.py check --deploy` con configuración efímera de producción sin
  warnings. El guard TODO devuelve sólo referencias históricas/documentales y
  del propio guard; no hay TODO/FIXME/HACK/XXX en código de producto nuevo.
- Integración real: PostgreSQL local + Django devolvió login 200, escenarios
  200, creación de ejecución 202, polling a `INFEASIBLE` con `output_hash` y
  conflicto explicable. Next standalone en 3101, mediante BFF y origen CSRF/
  CORS explícito, devolvió login 200, escenarios 200, optimización 202,
  polling `INFEASIBLE` y `/planner` 200 con contenido del planificador.

### Resultados

- Los gates de P14 quedan verificablemente satisfechos: el solver sólo produce
  planes compatibles con los hechos representados, distingue óptimo/factible/
  inviable/desconocido, conserva trazabilidad y no muta la historia oficial.
- No se creó commit Git porque AGENTS.md exige autorización explícita.

### Problemas pendientes

- B1 externo sigue `UNKNOWN` por falta de snapshot normativo archivado; no se
  publica inferencia ni se automatiza acceso autenticado al SIA.
- NVDA/VoiceOver y reviewers especializados no están disponibles; axe,
  teclado, E2E desktop/mobile y revisión manual read-only pasan.
- `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md` no existen en
  el kit original; deberán declararse en la auditoría final junto con la
  cobertura de los documentos equivalentes disponibles.

### Siguiente

Leer y ejecutar estrictamente `prompts/16_ADMIN_GOVERNANCE.md` como P15:
backoffice curricular, diff semántico y workflows de gobernanza.

## P15 — Curriculum backoffice & semantic diff

Estado: `done`

### Implementación realizada

- Añadí el workflow editorial auditable `DRAFT → IN_REVIEW → APPROVED →
  APPLIED`, con `ExtractionCandidate`, `Review` y `Publication` inmutables a
  nivel de modelo, migración `governance.0003` y recibo de publicación con
  hashes, diff, validación, impacto y confirmación humana.
- Implementé Source Inbox, visor de documentos/snapshots, detalle de
  propuestas, candidatos de extracción, diff semántico, validación, análisis
  de impacto, inspector de reglas AST + explicación humana + evidencia, cola de
  revisión y línea de auditoría completa.
- Apliqué autorización scoped con separación editor/revisor: un editor puede
  preparar y enviar una propuesta, pero el backend bloquea su autoaprobación y
  toda publicación requiere una segunda función autorizada. Las escrituras
  usan ETag/`If-Match`; los conflictos son explícitos.
- Las operaciones masivas exigen un preview sin escrituras y un token derivado
  de versión, selección, decisión, estado epistemológico y evidencia. Las
  reglas `VERIFIED` sin evidencia, candidatos pendientes o errores
  estructurales bloquean publicación. Las revisiones publicadas no se editan.
- Conecté `/sources`, el cliente generado/OpenAPI y BFF/frontend responsive,
  con estados de error, confirmación de publicación, actualización de vínculos
  de evidencia y prueba móvil/desktop. Documenté ADR-0020 y amplié las guías
  de backoffice/procedencia.

### Pruebas ejecutadas

- `uv run --frozen python -m pytest -q tests/test_governance_backoffice.py` →
  4 passed en SQLite y 4 passed en PostgreSQL local.
- Suite backend canónica → 98 passed + 1 skip esperado exclusivamente por el
  trigger PostgreSQL-only.
- `uv run --frozen python scripts/verify.py` → PASS completo: invariantes,
  Django, migraciones, OpenAPI freshness/breaking diff, Ruff, formato, mypy,
  cliente generado, ESLint, TypeScript y 23 pruebas Vitest con axe.
- `governance.0003_extractioncandidate_publication_review` aplicado y
  `makemigrations --check --dry-run`, `migrate --check`, `manage.py check` y
  OpenAPI/client verify PASS.
- `pnpm --dir apps/web build` → PASS con Next 16.3.1/standalone; Playwright →
  16/16 desktop/mobile; lint/typecheck y focused governance UI → PASS.
- Integración real PostgreSQL/Django: login con CSRF, inbox/detail, 296
  candidatos, submit a `IN_REVIEW`, request changes y restauración auditable a
  `DRAFT`, todos con HTTP/ETag exitosos. El servidor temporal fue detenido.

### Resultados

- Los gates de P15 están verificablemente satisfechos: no hay salto directo de
  extracción a publicación, la evidencia y el estado epistemológico son
  explícitos, el diff es semántico, la publicación es inmutable, la revisión
  requiere separación de funciones, la concurrencia no sobrescribe y el
  backoffice expone la procedencia y auditoría necesarias.
- No se creó commit Git porque AGENTS.md exige autorización explícita.

### Problemas pendientes

- B1 externo permanece `UNKNOWN` por falta de snapshot normativo institucional
  archivado; no se inventan reglas ni se automatiza SIA autenticado.
- NVDA/VoiceOver y reviewers/subagentes especializados no están expuestos en
  esta sesión; se realizó revisión manual read-only, axe, teclado y E2E
  desktop/mobile.
- `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md` no existen en
  el kit original; la auditoría final deberá comprobar los documentos
  equivalentes existentes y declarar esta ausencia.

### Siguiente

Leer y ejecutar estrictamente `prompts/17_PUBLICATION_IMPACT.md` como P16,
empezando por sus documentos de impacto/publicación y el estado real del
repositorio.

## P16 — Publicación e impacto

Estado: `done`

### Implementación realizada

- Añadí `PublicationEvent` inmutable, `PublicationImpact` por matrícula y
  `NotificationOutbox` transaccional, con estados explícitos, claves de evento/
  recomputación y planes versionados de impacto, jobs y notificación.
- La publicación bloquea propuesta/candidata/revisión vigente, valida que la
  base siga actual, publica la candidata y supersede la revisión anterior en
  una única transacción. La revisión publicada, el recibo, el evento y las
  auditorías históricas no se editan; una corrección/rollback exige una nueva
  revisión.
- El impacto conserva la revisión base de cada matrícula, su auditoría previa
  y `result_hash`, identifica cursos/grupos/requisitos cambiados y deja la
  recomputación pendiente de una decisión explícita de revisión. Las
  notificaciones se encolan sólo como outbox posterior al commit.
- Añadí `GET /api/v1/governance/publications/{publication_id}/impact`, sus
  esquemas OpenAPI y cliente TypeScript, además de la vista responsive del
  evento/impacto en `/sources`. La línea de auditoría de la propuesta incluye
  ahora el `PublicationEvent`.
- Documenté la decisión en ADR-0021 y actualicé versionado curricular,
  procedencia, auditoría, notificaciones, backoffice, arquitectura, eventos y
  contrato API. Los archivos específicos referidos por el prompt
  `docs/24_PUBLICATION_AND_IMPACT.md` y `docs/05_AUDIT_AND_CREDIT_ALLOCATION.md`
  no existen en el kit; se usaron sus documentos equivalentes disponibles.
- Durante la verificación corregí la limpieza de conexiones del ejecutor
  síncrono de optimización, que cerraba la conexión de Django para tests/API
  posteriores en PostgreSQL. También hice UTF-8 el guard de TODO de Windows y
  aislé el estado mutable del fixture editorial E2E entre navegadores.

### Pruebas ejecutadas

- `tests/test_publication_impact.py` → 3 passed en SQLite y 3 passed en
  PostgreSQL.
- Suite backend PostgreSQL → 102 passed; suite canónica SQLite mediante
  `scripts/verify.py` → 101 passed + 1 skip esperado por trigger PostgreSQL-only.
- Migraciones `governance.0004_publicationevent_publicationimpact_and_more` y
  `notifications.0001_initial` aplicadas en SQLite/PostgreSQL; `manage.py
  check`, `makemigrations --check --dry-run`, `migrate --check` y
  OpenAPI freshness/breaking check PASS.
- `scripts/verify.py` → PASS completo: invariantes, Django, migraciones,
  backend, Ruff/formato/mypy, cliente generado, ESLint, TypeScript y Vitest
  23/23 con axe.
- `pnpm --dir apps/web build` → PASS con Next 16.3.1 y runtime standalone;
  Playwright E2E → 16/16 desktop/mobile después de reparar el aislamiento del
  fixture editorial.
- `pnpm audit --prod --audit-level high`, `uv pip check`, `git diff --check`,
  Ruff focalizado y guard TODO UTF-8 → PASS. El guard reporta únicamente
  referencias históricas/documentales y su propio patrón, no TODO funcional
  del código de producto.

### Resultados

- Los gates de P16 quedan verificablemente satisfechos: una publicación inválida
  no muta la revisión vigente ni crea evento/outbox; una válida supersede sin
  reescribir auditorías, identifica afectados y expone el plan auditable; el
  contenido nuevo permanece inmutable; no existe publicación automática por
  LLM.
- No se creó commit Git porque AGENTS.md exige autorización explícita.

### Problemas pendientes

- P17–P26 y los prompts finales de auditoría/operación aún deben ejecutarse.
- B1 externo permanece `UNKNOWN` por falta de snapshot normativo institucional;
  no se inventan reglas ni se automatiza SIA autenticado.
- El outbox queda preparado para el dispatcher y la entrega efectiva que se
  implementarán/verificarán en P17; P16 sólo encola solicitudes post-commit.
- NVDA/VoiceOver y reviewers/subagentes especializados no están expuestos en
  esta sesión; se realizó revisión manual read-only, axe, teclado y E2E
  desktop/mobile.
- `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md` no existen en
  el kit original; la auditoría final comprobará los documentos equivalentes y
  declarará esta ausencia.

### Siguiente

Leer y ejecutar estrictamente `prompts/18_NOTIFICATIONS.md` como P17,
empezando por su documentación y el estado real del outbox recién creado.

## P17 — Notificaciones

Estado: `done`

### Implementación realizada

- Implementé `NotificationEvent` inmutable, `NotificationDelivery` por
  destinatario/canal, `NotificationPreference` por tipo de evento y outbox
  durable con estados de materialización, reintento y supresión. La migración
  `notifications.0002_notificationdelivery_notificationevent_and_more` quedó
  aplicada en SQLite y PostgreSQL.
- Cerré el dispatcher reemplazable mediante `process_notifications --limit`:
  sólo materializa fuentes `PUBLISHED`, registra el evento una vez, aplica
  preferencias, evita doble entrega con unicidad/`dedupe_key`, usa backoff y
  deja fallos con códigos seguros. La publicación abortada o un draft no
  produce evento ni delivery.
- Añadí plantillas locales `es-CO`/`en`, payloads deliberadamente sin códigos
  de revisión, historia, correo ni impacto individual, y un adaptador email
  opcional detrás de `NOTIFICATIONS_EMAIL_ENABLED=false`. El boundary del
  proveedor recibe contenido estático y la clave estable de idempotencia;
  errores no filtran detalles del proveedor.
- Añadí los endpoints autenticados de feed, lectura individual/global y
  preferencias; el feed tiene cursor opaco consumible, ownership estricto y
  ProblemDetails. Regeneré `artifacts/openapi.json` y el cliente TypeScript.
- Reemplacé el placeholder del shell por un centro responsive y accesible con
  contador numérico, carga/error, lectura, preferencias de canal/idioma y
  enlaces internos validados. Añadí prueba de componente con axe y flujo E2E
  desktop/mobile; actualicé fixture, mensajes y estilos.
- Documenté ADR-0022 y actualicé contrato API, sistema de notificaciones,
  seguridad/privacidad, modelo de eventos y ERD. La skill `feature-delivery` y
  los reviewers especializados no están expuestos en esta sesión; hice
  revisión manual read-only de arquitectura, código, currículo, seguridad y
  UX, dejando la limitación explícita.

### Pruebas ejecutadas

- `tests/test_notifications.py`: 5 passed en SQLite y 5 passed en PostgreSQL;
  incluye idempotencia, retry/dedupe email, draft gate, preferencias,
  privacidad, cursor inválido y prevención de acceso cruzado.
- `uv run --frozen python scripts/verify.py`: PASS completo — invariantes,
  OpenAPI freshness/breaking, Django/migraciones, 106 backend tests + 1 skip
  esperado por trigger PostgreSQL-only, Ruff/formato/mypy, cliente generado,
  ESLint, TypeScript y Vitest 26/26 con axe.
- `notifications.0002` aplicada; `makemigrations --check --dry-run`,
  `migrate --check`, `showmigrations`, `manage.py check` y API client verify
  PASS en SQLite/PostgreSQL.
- `pnpm build`: PASS con Next 16.3.1 y runtime standalone; `pnpm e2e`: 18/18
  desktop/mobile, incluyendo apertura del centro, preferencias y marcar todo
  como leído.
- Seguridad/operación: `pnpm audit --prod --audit-level high`, `uv pip check`,
  `git diff --check`, guard UTF-8 de TODO, y `manage.py check --deploy` con
  configuración de producción explícita (HSTS/SSL/cookies) PASS sin issues.

### Resultados

- Los gates de P17 quedan verificablemente satisfechos: ningún draft o
  publicación fallida genera una notificación; cada reintento conserva la
  misma identidad; las preferencias se respetan; el centro sólo muestra
  entregas del usuario; los canales no reciben detalles académicos privados;
  lectura, cursor y enlaces internos funcionan en desktop/mobile.
- No se creó commit Git porque AGENTS.md exige autorización explícita.

### Problemas pendientes

- P18–P26 y los prompts finales de auditoría/operación aún deben ejecutarse.
- B1 externo continúa `UNKNOWN` por falta de snapshot normativo institucional;
  no se inventan reglas ni se automatiza SIA autenticado.
- El proveedor email no está configurado en el entorno local y permanece
  opcional/deshabilitado por diseño; el worker debe programarse/observarse en
  el despliegue según ADR-0022.
- NVDA/VoiceOver y reviewers/subagentes especializados no están disponibles;
  axe, teclado, E2E desktop/mobile y revisión manual read-only pasan.
- `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md` no existen en
  el kit original; la auditoría final debe declararlo y contrastar los
  documentos equivalentes disponibles.

### Siguiente

Leer y ejecutar estrictamente `prompts/19_ANALYTICS.md` como P18, comenzando
por su documentación, estado y modelos de datos antes de modificar código.

## P20 — Observabilidad y tooling operacional

Estado: `done`

### Implementación realizada

- Añadí `modules.observability` con redacción recursiva de secretos/PII,
  normalización de rutas e ids, logs JSON estructurados, contexto de
  correlación, propagación W3C `traceparent`, `X-Request-ID`/`X-Trace-ID` y
  spans OpenTelemetry de requests/operaciones.
- Fijé `opentelemetry-exporter-otlp-proto-http==1.44.0` junto al SDK
  `1.44.0`, actualicé `uv.lock` y dejé la exportación OTLP opt-in por
  `OTEL_EXPORTER_OTLP_ENDPOINT`/endpoints específicos. Añadí métricas RED de
  API, health DB, jobs, auditoría, grafo, optimizer, importación y publicación,
  con etiquetas controladas y snapshot agregado seguro.
- Separé liveness y readiness: `/api/v1/health/live` no accede a DB;
  `/api/v1/health/ready` ejecuta `SELECT 1`, registra el resultado y devuelve
  `503 NOT_READY` seguro ante dependencia no disponible. Añadí
  `/api/v1/health/metrics`, protegido por `OBSERVABILITY_METRICS_TOKEN` fuera
  de desarrollo, con `Cache-Control: no-store`.
- Añadí el adaptador frontend opt-in `lib/observability.ts` y
  `ObservabilityClient`: errores globales/rechazos y LCP/CLS/FID sin mensajes,
  cookies, credenciales, query strings ni PII; el error boundary conserva
  digest de soporte acotado.
- Añadí `scripts/smoke.py` para live/ready/OpenAPI y URL Web opcional, más la
  especificación de dashboard, runbooks de alertas y guía de smoke en
  `docs/ops/`; amplié `docs/20_OBSERVABILITY_OPERATIONS.md`, el baseline
  tecnológico y añadí ADR-0024.
- Decoré las operaciones públicas de auditoría, grafo, optimizer, importación,
  publicación y dispatcher de notificaciones sin cambiar su semántica; los
  errores se cuentan sin serializar mensajes ni payloads académicos.
- Regeneré `artifacts/openapi.json` y `packages/api-client/src/generated.ts`.

### Pruebas ejecutadas

- Focalizado backend: `tests/test_observability.py` 7 passed; health/OpenAPI
  13 passed; regresiones de importación/gobernanza 12 passed.
- Regresión canónica: `python scripts/verify.py` PASS — 117 backend passed +
  1 skip esperado por trigger PostgreSQL-only; OpenAPI freshness/breaking,
  Django checks, migraciones, Ruff, formato, mypy, cliente, ESLint,
  TypeScript y Vitest 33/33 PASS.
- PostgreSQL real: `migrate --check`, `makemigrations --check --dry-run`,
  plan de migraciones 0 y suite completa `118 passed`; PostgreSQL 18.0
  responde y no hay migraciones pendientes.
- Frontend: `pnpm build` PASS con Next 16.3.1 standalone; Playwright
  `20 passed` desktop/mobile; producción real Web/API arrancó y smoke
  `scripts/smoke.py --base-url http://127.0.0.1:8020 --web-url
  http://127.0.0.1:3020` PASS; live/ready/OpenAPI/Web reales 200 y métricas
  devolvieron request/trace ids y `no-store`.
- Seguridad/dependencias: `pnpm audit --prod --audit-level high` sin
  vulnerabilidades conocidas; `uv pip check` PASS; `manage.py check --deploy`
  con HSTS/SSL/cookies explícitos PASS sin warnings; exportadores OTel
  importables; `git diff --check` PASS.

### Resultados

- Los gates de P20 quedan satisfechos: fallos y latencia son observables,
  readiness distingue proceso de DB, correlación atraviesa request→span→log,
  exportación OTel es configurable, no se registran secretos/PII por diseño y
  dashboard/runbooks/smoke son artefactos revisables.
- El guard amplio `scripts/check_no_todos.py` reporta sólo referencias
  históricas/documentales y metadatos (`AGENTS.md`, `MANIFEST*`, estado y el
  propio guard); no hay TODO/FIXME/HACK/XXX funcional en el código nuevo de P20.
- La skill obligatoria `feature-delivery`, `security-change` y reviewers
  especializados no están expuestos en esta sesión; completé revisión manual
  read-only de arquitectura, código, seguridad y UX, con tests y gates
  ejecutables.
- No se creó commit Git porque requiere autorización explícita.

### Problemas pendientes

- No quedan fallos resolubles dentro de P20. Las métricas en memoria se pierden
  al reiniciar si no se configura un collector OTLP; esto está documentado y es
  la responsabilidad del despliegue operacional.
- Falta definir un SLO numérico después de baseline real; no se inventa uno.
- El proveedor email sigue deshabilitado localmente; B1 normativo externo
  continúa `UNKNOWN` por falta de snapshot archivado y no se publican reglas
  inferidas.
- NVDA/VoiceOver y reviewers/subagentes no están disponibles. Siguen ausentes
  `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md`; la auditoría
  final debe usar y citar los equivalentes existentes.

### Siguiente

Leer completamente `prompts/21_PERFORMANCE.md` y sus referencias antes de
comenzar P21.

## P18/P19 — Analítica estudiantil e institucional

Estado: `done`

### Implementación realizada

- Implementé `modules.analytics` como servicios de lectura deterministas sobre
  `DegreeAuditRun`/`DegreeAuditResult` persistidos y revisiones `PUBLISHED`.
  La vista estudiantil entrega créditos aplicados/restantes, requisitos
  pendientes y `UNKNOWN`, cursos críticos, tendencia de snapshots y
  comparación de proyecciones privadas; una lectura sin snapshot responde un
  estado explícito sin crear auditorías.
- Implementé vista institucional agregada para avance, cursos cuello de
  botella, requisitos rezagados, demanda potencial por período, rutas
  frecuentes y duración observada. La demanda distingue `PLANNED`/`ELIGIBLE`
  y no afirma oferta ni matrícula; el tiempo oficial a grado queda `UNKNOWN`
  y sólo se muestra duración observada cuando hay hechos suficientes.
- Apliqué RBAC de alcance para `ANALYST`/`ADMIN`, validación de institución,
  programa y período, supresión de celdas pequeñas configurable con mínimo
  operativo, ausencia de PII institucional y rutas HMAC sin identificadores
  de estudiante. Añadí exportación JSON/CSV agregada con `no-store`,
  `nosniff`, nombre seguro y `AuditEvent` por exportación.
- Añadí catálogo visible de definiciones/fuentes/estado epistemológico,
  endpoints `/analytics/definitions`, `/analytics/student`,
  `/analytics/institutional` y exportación, regeneré OpenAPI/cliente y
  conecté `/analytics` en Next con tablas accesibles, progreso textual,
  advertencias metodológicas y definiciones junto a los datos.
- Añadí pruebas backend de autorización, snapshot persistido, minimización,
  agregación y exportación; pruebas frontend con axe, serialización del
  cliente y E2E desktop/mobile. Documenté ADR-0023 y actualicé analítica,
  seguridad y matriz de autorización.

### Pruebas ejecutadas y resultados

- `uv run --frozen python tests/test_analytics.py` equivalente vía pytest:
  4 passed en SQLite y 4 passed en PostgreSQL.
- `uv run --frozen python scripts/verify.py`: PASS — 110 passed + 1 skip
  esperado por trigger PostgreSQL-only, invariantes, Django, migraciones,
  OpenAPI freshness/breaking, Ruff/formato, mypy y cliente generado.
- Frontend: ESLint PASS, TypeScript PASS, Vitest `30 passed` en 13 archivos
  con axe, `pnpm build` PASS con Next 16.3.1 standalone, y Playwright
  `20 passed` desktop/mobile incluyendo `/analytics`.
- `migrate --check`/`manage.py check` PASS; `pnpm audit --prod
  --audit-level high`, `uv pip check` y comprobaciones previas de despliegue
  siguen PASS. No hay migración nueva porque la primera implementación es
  read-only sobre datos existentes.

### Problemas pendientes

- No quedan fallos resolubles dentro de P18/P19. P20–P26 y los prompts
  finales aún deben ejecutarse.
- B1 externo permanece `UNKNOWN` por falta de evidencia normativa archivada;
  no se inventan reglas ni se automatiza SIA autenticado.
- Revisores/subagentes especializados y NVDA/VoiceOver no están expuestos;
  se realizó revisión manual read-only, axe, teclado y E2E desktop/mobile.
- `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md` no existen en
  el kit; la auditoría final contrastará los equivalentes disponibles y
  declarará la ausencia.
- No se creó commit automático.

### Siguiente

Leer completamente `prompts/20_OBSERVABILITY.md` como P20, incluyendo sus
referencias y el estado real de instrumentación, antes de modificar código.

## Current milestone status — P20 complete — 2026-08-16 22:25 -05:00

P20 está `done`. Logs JSON/redaction, request correlation, W3C/OTel traces,
RED/job/domain metrics, liveness/readiness/metrics health, frontend error/Web
Vitals adapter, timing instrumentation, smoke, dashboard y runbooks fueron
implementados. La verificación canónica, PostgreSQL, build, E2E, smoke real,
security/dependency checks y deploy check pasan; P21 es el siguiente milestone.

## P21 — Performance y escala — 2026-08-16 23:07 -05:00

Estado: `done`

### Implementación realizada

- Añadí `scripts/benchmark_performance.py`, que mide el motor puro de reglas,
  malla, grafo y auditoría con p50/p95, payload, conteo de consultas y
  `EXPLAIN (FORMAT JSON)` sin mutar datos. Añadí `scripts/load_test.py` para
  requests GET explícitos y `apps/web/scripts/audit-bundle.mjs` junto al
  comando `pnpm audit:bundle`.
- Eliminé el N+1 de evidencia en `build_revision_snapshot` con
  `prefetch_related("evidence__snapshot")`. En PostgreSQL, el caso válido de
  auditoría del plan 2514 bajó de 164 a 19 consultas y de p50 681.149 ms a
  192.993 ms (p95 239.645 ms).
- Sustituí el sondeo secuencial de cinco estados de matrícula por una consulta
  con `CASE`, manteniendo exactamente la prioridad
  `ACTIVE → NEEDS_REVIEW → COMPLETED → SUSPENDED → WITHDRAWN` y desempate por
  fecha. Añadí regresión del caso vacío y de la prioridad, ambos en una sola
  consulta.
- Optimicé el read path del grafo reutilizando adyacencia e índice de nodos en
  el foco, y el mapa reutilizando el índice inverso de cursos desbloqueados;
  la proyección semántica, ciclos, relaciones y explicaciones permanecen
  deterministas.
- Hice explícitos los límites del optimizador: 300 segundos por run, dos
  workers y 20 jobs en vuelo. La sobrecapacidad se registra como `REJECTED`
  con `termination_reason=optimization_capacity` y se responde con 409.
- Los `EXPLAIN` muestran cobertura por los índices existentes
  `revision_one_published_per_plan` y `audit_run_enrollment_time_idx`, además
  de los índices compuestos de revisión, enrollment, oferta y horarios. No
  añadí una migración especulativa, Redis ni una caché que pueda competir con
  el `DegreeAuditResult` persistido como fuente de verdad.
- Documenté baseline antes/después, límites HTTP/locales y ADR-0025 en
  `docs/ops/PERFORMANCE_BASELINE.md`, `docs/25_PERFORMANCE.md` y
  `docs/adr/0025-performance-read-paths-and-job-bounds.md`.

### Pruebas ejecutadas y resultados

- `tests/test_performance.py`: 4 passed; regresiones focalizadas de auditoría,
  malla, grafo y optimización: 34 passed.
- `python scripts/verify.py` con PostgreSQL: PASS — 122 tests backend, checks
  Django, migraciones, OpenAPI/cliente, Ruff, formato, mypy, ESLint,
  TypeScript y 33 tests frontend.
- Benchmark PostgreSQL/Python 3.14.7: reglas p95 16.489 µs por evaluación;
  malla p95 172.191 ms/16 queries; grafo con foco p95 168.314 ms/16 queries;
  auditoría válida p95 239.645 ms/19 queries.
- `pnpm build` Next 16.3.1 standalone PASS; `pnpm audit:bundle` PASS con 19
  chunks y 2,444.6 KiB, manteniendo React Flow/ELK en la ruta dinámica del
  grafo; `pnpm e2e` PASS con 20/20 desktop/mobile.
- API 8020 y Next standalone 3020 arrancaron con el código final. Smoke
  `live/ready/OpenAPI/Web` PASS; las rutas reales live, ready, metrics,
  curriculum-map, dependency-graph, OpenAPI, `/`, `/analytics` y `/graph`
  respondieron 200. Se observaron `X-Request-ID`, `X-Trace-ID` y
  `Cache-Control: no-store` en las respuestas de health.
- `migrate --check`, `makemigrations --check --dry-run` y plan de migración
  PostgreSQL: PASS, plan 0, PostgreSQL 18.0 (`server_version_num=180000`).
  `manage.py check --deploy` con configuración segura explícita: 0 warnings;
  `pnpm audit --prod --audit-level high`, `uv pip check` y `git diff --check`:
  PASS.

### Problemas pendientes

- No queda un fallo resoluble dentro de P21. El load probe concurrente en
  `runserver` mostró contención propia del servidor de desarrollo; el baseline
  de producción sigue deliberadamente pendiente de worker/proxy/pool y siete
  días de métricas, por lo que no se inventa un SLO.
- `scripts/check_no_todos.py` reporta 35 referencias históricas,
  documentales/metadatos y del propio guard; la clasificación manual no
  encontró TODO/FIXME/HACK/XXX funcional en código de producto P21.
- Siguen globalmente pendientes P22–P26 y la auditoría final. B1 externo sigue
  `UNKNOWN` por falta de evidencia normativa archivada; no se publican reglas
  inferidas. `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md` no
  existen en el repositorio y deberán contrastarse con los equivalentes
  disponibles. Reviewers/subagentes y la skill `feature-delivery` no están
  expuestos; se dejó revisión manual read-only. No se creó commit.

### Siguiente

Leer completamente `prompts/22_ACCESSIBILITY_E2E.md` y ejecutar P22.

## P22 — Accesibilidad y E2E cross-device — 2026-08-16 23:55 -05:00

Estado: `done`

### Implementación realizada

- Añadí `apps/web/tests/e2e/accessibility.spec.ts` con axe-core 4.13.0
  inyectado en las rutas críticas y cobertura de teclado, skip link, foco,
  Escape, mobile, zoom equivalente a 200%, reduced motion, recorrido
  estudiante y alternativa accesible del planificador. El gate quedó en
  cero violaciones axe, incluidas las de severidad moderada.
- El menú móvil enfoca el primer control al abrirse, cierra con `Escape` y
  devuelve el foco al disparador. La ficha curricular enfoca su título y
  devuelve el foco a la tarjeta que la abrió. El grafo enfoca/anuncia el
  título del curso seleccionado y conserva la lista textual como canal
  independiente del canvas.
- Retiré `aria-label` inválidos de los handles `div` que genera React Flow,
  manteniendo las relaciones descritas en la alternativa textual. El
  planificador conserva el selector `Mover a` como alternativa completa a
  drag/drop y expone nombres accesibles de las columnas.
- Corregí el token claro `--text-muted` de `#6f8177` a `#5a6d61`, documenté
  ratios WCAG y añadí `docs/ops/ACCESSIBILITY_MANUAL_CHECKS.md` para NVDA,
  VoiceOver, zoom, reflow, foco y movimiento. El backoffice dejó de anidar
  un landmark `<main>` dentro del shell; ahora usa una región etiquetada.
- El fixture E2E del grafo responde al parámetro `selected` para verificar
  realmente el cambio de foco contextual. No hubo cambio arquitectónico ni
  se requirió ADR.

### Pruebas ejecutadas y resultados

- `pnpm test`: 33/33 tests frontend PASS.
- `pnpm lint`: PASS; `pnpm typecheck`: PASS.
- `pnpm build`: Next.js 16.3.1 standalone PASS.
- `pnpm e2e`: 50/50 desktop/mobile PASS después de la reparación semántica
  final; incluye 20/20 ejecuciones axe sin ninguna violación y los flujos de
  teclado, mobile, zoom, reduced motion y recorridos críticos.
- Revisiones manuales read-only de arquitectura, código, currículo,
  seguridad y UX realizadas; contraste calculado para temas claro/oscuro.

### Problemas pendientes

- NVDA/VoiceOver y dispositivos físicos no están disponibles en el entorno
  headless; la lista de comprobación manual queda documentada para el paso de
  release y no se presenta como ejecutada.
- Los reviewers/subagentes especializados y la skill `feature-delivery` no
  están expuestos. B1 continúa `UNKNOWN` por falta de evidencia normativa;
  no se publican inferencias. `docs/SPEC.md`, `docs/REQUIREMENTS.md` y
  `docs/ACCEPTANCE.md` siguen ausentes; se auditarán contra sus equivalentes.
- No se creó commit automático. P23–P26 y la auditoría final siguen pendientes.

### Siguiente

Leer completamente `prompts/23_SECURITY_HARDENING.md` y ejecutar P23.

## P23 — Security hardening & threat remediation

Estado: `done`

### Implementación realizada

- Añadí el threat model y la matriz de IDOR/BOLA con límites de confianza,
  activos, abuso, propietarios de recursos y casos negativos reproducibles.
- Implementé la frontera SSRF `SafeSourceFetcher`: allowlist explícita,
  HTTPS/puerto por defecto, normalización IDNA, bloqueo de localhost,
  loopback, redes privadas/link-local/multicast/reservadas y direcciones
  IPv4-mapped, conexión fijada al resultado DNS, revalidación de cada redirect,
  límites de bytes/redirects/timeout y SHA-256.
- Añadí límites de mutaciones por usuario/IP y por clase de endpoint, con
  `Retry-After`, y amplié los headers CORS/seguridad requeridos.
- Reforcé almacenamiento privado de artefactos con permisos 0700/0600,
  containment, archivos regulares, límites de tamaño, firmas ejecutables,
  MIME/extensión, PDF/UTF-8/NUL y colisiones de nombre.
- Hice inmutable el audit log mediante guards ORM y trigger PostgreSQL; los
  eventos sólo aceptan correlation IDs validados y conservan redacción.
- Añadí `scripts/scan_secrets.py`, `scripts/sast.py`, workflow semanal de
  seguridad, provisión SQL de roles mínimos, runbook de respuesta y ADR-0026.
- La auditoría de dependencias detectó inicialmente vulnerabilidades en
  `pypdf==6.10.0`; actualicé a `pypdf==6.16.1`, regeneré `uv.lock` y dejé la
  resolución y procedencia documentadas en `TECHNOLOGY_BASELINE.md`.

### Pruebas ejecutadas y resultados

- `tests/test_security_hardening.py`, `tests/test_identity_security.py` y
  `tests/test_student_history.py`: 34 passed, 10 subtests passed; el skip de
  trigger en la prueba aislada está cubierto por la suite PostgreSQL de
  identidad.
- `pypdf==6.16.1`: parser/history/security focalizados 23 passed, 1 skip.
- `python scripts/scan_secrets.py`: PASS; `python scripts/sast.py`: PASS.
- `pip-audit==2.9.0` sobre el export congelado sin dependencias no fijadas:
  PASS, sin vulnerabilidades conocidas; `uv pip check`: PASS; `pnpm audit
  --prod --audit-level high`: PASS.
- `scripts/verify.py` con PostgreSQL: PASS — 131 backend passed, 1 skip,
  33 frontend passed; Django/deploy checks, migraciones, OpenAPI/cliente,
  Ruff, formato, mypy, ESLint y TypeScript PASS.
- Revisión manual read-only de arquitectura, código, seguridad, currículo y
  UX documentada en `docs/security/SECURITY_REVIEW.md`; no se inventó el
  sign-off de reviewers especializados no disponibles.

### Problemas pendientes

- No quedan hallazgos Critical/High resolubles dentro del repositorio. MFA/IdP
  institucional, antimalware gestionado, egress de red y gestión operativa de
  secretos son prerrequisitos externos documentados, no controles simulados.
- B1 continúa `UNKNOWN` por falta de snapshot normativo archivado; no se
  publican reglas inferidas. `docs/SPEC.md`, `docs/REQUIREMENTS.md` y
  `docs/ACCEPTANCE.md` no existen y se contrastarán contra equivalentes.
- Los reviewers/subagentes y Skills especializados no están expuestos; queda
  registrada la revisión manual read-only. No se creó commit automático.

### Siguiente

Leer completamente `prompts/24_DEPLOYMENT_DR.md` y ejecutar P24.
