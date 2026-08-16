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
