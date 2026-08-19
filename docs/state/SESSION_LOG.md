# Session Log

Añadir una entrada por sesión significativa:

## YYYY-MM-DD HH:MM — agent/model
- Objetivo:
- Cambios:
- Verificaciones:
- Pendiente:
- Siguiente:

## 2026-08-16 00:34 — Codex / GPT-5
- Objetivo: ejecutar y cerrar P00 (`prompts/01_TOOLCHAIN_AND_BOOTSTRAP.md`).
- Cambios: bootstrap Django/Next/cliente OpenAPI/Compose; versiones y lockfiles; CI/Renovate/README; Dockerfiles y `.dockerignore`; script standalone de Next corregido; estado y ADR-0011 actualizados.
- Verificaciones: `python scripts/verify.py` PASS; build Next PASS; Playwright E2E desktop/mobile PASS 2/2; migraciones/checks PASS; Compose config PASS; PostgreSQL 18 healthy; Django real contra PostgreSQL y health/OpenAPI HTTP 200.
- Pendiente: P01 es el siguiente milestone. Reviewers especializados no están disponibles como herramientas; se registró revisión manual.
- Siguiente: leer y ejecutar `prompts/02_DOMAIN_AND_BACKEND_FOUNDATION.md`.

## 2026-08-16 01:02 — Codex / GPT-5
- Objetivo: ejecutar y cerrar P01 (`prompts/02_DOMAIN_AND_BACKEND_FOUNDATION.md`).
- Cambios: bounded contexts y modelos/migraciones base; dominio puro; servicio de publicación; trigger PostgreSQL; factories/tests; ERD; UserManager; checks de migraciones y HSTS.
- Verificaciones: `python scripts/verify.py` PASS; SQLite migrations PASS; PostgreSQL migrations/trigger/full suite PASS (10/10); Ruff/format/mypy/frontend checks PASS; deploy check PASS con SSL/HSTS.
- Pendiente: P02 es el siguiente milestone. Reviewers especializados no están disponibles como herramientas; revisión manual registrada.
- Siguiente: leer y ejecutar `prompts/03_CURRICULUM_INGESTION.md`.

## 2026-08-16 01:31 — Codex / GPT-5
- Objetivo: ejecutar y cerrar P02 (`prompts/03_CURRICULUM_INGESTION.md`).
- Cambios: validador schema/fingerprint/totales/referencias/ciclos; ingestión 2514 DRAFT; PDF y SHA-256; SourceSnapshot/Evidence; ChangeProposal/diff; ImportBatch trazable; comandos de validación/import/diff; reporte humano; guardas de estados editoriales; migración de trigger metadata; tests y documentación.
- Verificaciones: baseline validator PASS; import real dos veces sin duplicados; `pytest` focalizado 5 passed; `python scripts/verify.py` PASS; PostgreSQL migrate/check/full pytest PASS 15; Ruff/format/mypy y frontend PASS.
- Pendiente: B1 externo sin snapshot local permanece pending; reviewers especializados no están disponibles; no commit automático.
- Siguiente: leer y ejecutar `prompts/04_RULE_ENGINE.md` como P03.

## 2026-08-16 01:50 — Codex / GPT-5
- Objetivo: ejecutar y cerrar P03 (`prompts/04_RULE_ENGINE.md`).
- Cambios: AST puro versionado 1.0.0; parser/serializer/hash; evaluator trivalente ampliado; explicación/facts/evidence; exact arithmetic; cycle utilities; schema extensions; `Requirement.ast_schema_version`; golden/property tests; benchmark.
- Verificaciones: `python scripts/verify.py` PASS (24 passed, 1 SQLite skip); PostgreSQL migration + full suite PASS (25); Ruff/format/mypy/frontend PASS; golden 12/12; Hypothesis PASS; benchmark PASS.
- Pendiente: NOT_APPLICABLE depende de hecho explícito; reviewers especializados no están disponibles; no commit automático.
- Siguiente: leer y ejecutar `prompts/05_DEGREE_AUDIT.md` como P04.

## 2026-08-16 02:15 — Codex / GPT-5
- Objetivo: ejecutar y cerrar P04 (`prompts/05_DEGREE_AUDIT.md`).
- Cambios: motor puro de auditoría con `AuditInput`/`AuditContext`/`AuditResult`; ledger determinista sin doble conteo; earned/applied/unapplied; grupos/componentes; libre elección abierta; requisitos externos/UNKNOWN; homologaciones; excepciones; remaining/next unlocks; servicio transaccional y persistencia de run/result/allocation; golden 2514 y tests.
- Verificaciones: focalizados de auditoría 7 passed; `python scripts/verify.py` PASS (31 passed + 1 skip SQLite); `ruff`, formato y `mypy` PASS; PostgreSQL migrate/no-pending/check y suite completa PASS (32); revisión manual sin Critical/High reproducible.
- Pendiente: no hay fallo funcional de P04; B1 sigue con riesgo documental externo heredado; reviewers especializados no están disponibles; no commit automático.
- Siguiente: leer y ejecutar `prompts/06_IDENTITY_SECURITY.md` como P05.

## 2026-08-16 02:54 — Codex / GPT-5
- Objetivo: ejecutar y cerrar P05 (`prompts/06_IDENTITY_SECURITY.md`).
- Cambios: autenticación de sesión first-party; CSRF/CORS/CSP/cookies seguras; login/logout/me; reset y verificación con tokens separados por propósito; invalidación de sesiones; roles y asignaciones con alcance/vigencia; ownership de estudiante/asesor; separación editor/reviewer; audit log append-only con redacción recursiva, digest de IP/identificadores y triggers PostgreSQL/SQLite; rate limit transaccional tolerante a carreras; ADR-0012 para frontera MFA; migraciones, ERD, `.env.example` y documentación.
- Verificaciones: `tests/test_identity_security.py` 10 passed en SQLite; suite SQLite 41 passed + 1 skip curricular esperado; suite PostgreSQL 42 passed; migraciones/check/no-pending PASS en ambas bases; `scripts/verify.py` PASS; Ruff/format/mypy/ESLint/TypeScript/Vitest PASS; OpenAPI y cliente generado PASS; `manage.py check --deploy` PASS sin warnings con configuración de producción; guard de TODO sin hits en código de producto.
- Pendiente: MFA de roles privilegiados queda explícitamente en P23 mediante ADR-0012; B1 externo sigue pendiente por falta de snapshot local. Reviewers especializados no están disponibles; revisión manual de seguridad/arquitectura/código sin Critical/High reproducible. No commit automático.
- Siguiente: leer y ejecutar `prompts/07_STUDENT_HISTORY_IMPORTS.md` como P06.

## 2026-08-16 03:35 — Codex / GPT-5
- Objetivo: ejecutar y cerrar P06 (`prompts/07_STUDENT_HISTORY_IMPORTS.md`).
- Cambios: parser puro CSV/JSON/PDF text-only con pypdf 6.10.0; formato `student-history/1.0.0`; RawArtifact/CandidateRecord/Reconciliation/ImportEvidence; storage privado y validación de uploads; preview idempotente por enrollment+SHA-256; resolución de conflictos/códigos externos; confirmación transaccional con evidencia y recálculo de auditoría; CRUD manual de CourseAttempt con ownership/RBAC, auditoría y anulado; API `/history`; migraciones; documentación y cliente OpenAPI regenerado.
- Verificaciones: P06 focalizado 12/12 SQLite y 12/12 PostgreSQL; suite completa 53 passed + 1 skip esperado en SQLite y 54 passed en PostgreSQL 18; migraciones/check PASS; Ruff/format/mypy PASS; exportación/verificación OpenAPI y cliente PASS. Se corrigió el flush SQLite del audit log y el lock PostgreSQL sobre joins nullable durante el ciclo implementación→prueba→diagnóstico→reparación.
- Pendiente: no hay fallo funcional de P06 dentro del repositorio. Scanning antimalware externo y MFA privilegiado quedan en el alcance posterior documentado; B1 externo sigue `UNKNOWN` por falta de snapshot normativo local; no commit automático.
- Siguiente: leer y ejecutar `prompts/08_API_CONTRACT.md` como P07.

## 2026-08-16 04:15 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P07 (`prompts/08_API_CONTRACT.md`).
- Cambios: routers separados por bounded context; `ProblemDetails` uniforme con handlers de validación/HTTP/CSRF y correlación `X-Request-ID`; paginación/filtros/sort deterministas; ETag/If-Match y locks de fila para optimistic concurrency; `Idempotency-Key` persistente y serializado para imports; detector de breaking changes; frescura byte-level del cliente `openapi-typescript`/`openapi-fetch`; documentación API/versionado/auth/CSRF; CI y `scripts/verify.py` actualizados.
- Verificaciones: 19 tests focalizados SQLite; `python scripts/verify.py` PASS con 60 tests + 1 skip esperado; migraciones/check PASS; cliente generado y OpenAPI PASS; PostgreSQL 18.0 Compose healthy, migraciones nuevas aplicadas y suite completa PASS con 61 tests; Ruff/format/mypy/ESLint/TypeScript/Vitest PASS.
- Resultados: gates P07 satisfechos y sin fallos funcionales pendientes dentro de su alcance. La comparación contra una base real queda conectada al job de pull request mediante SHA; self-check local PASS.
- Riesgos: B1 sin snapshot normativo, MFA privilegiado y antimalware externo siguen documentados en sus milestones correspondientes. Reviewers especializados no están expuestos en la sesión; revisión manual read-only sin Critical/High reproducibles. No commit automático.
- Siguiente: leer y ejecutar `prompts/09_FRONTEND_FOUNDATION.md` como P08.

## 2026-08-16 04:58 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P08 (`prompts/09_FRONTEND_FOUNDATION.md`).
- Cambios: App Router shell responsive y role-aware; auth shell `/login`; sesión/CSRF/login/logout mediante cliente OpenAPI generado; eliminación de datos académicos ficticios; tokens semánticos light/dark; primitives y componentes presentacionales del design system; i18n `es-CO`/`en`; URL state seguro; boundaries loading/error/not-found; axe/Vitest y Playwright; ADR-0013 y documentación frontend.
- Verificaciones: `pnpm install --frozen-lockfile`, typecheck, lint, 4 archivos/6 tests unitarios+axe, build Next PASS; Playwright PASS 4/4 desktop/mobile; `python scripts/verify.py` PASS con 60 tests + 1 skip esperado, OpenAPI fresco, checks, Ruff/format/mypy y frontend.
- Resultados: gates P08 satisfechos sin fallos funcionales pendientes dentro del alcance. Los módulos de datos todavía esperan los read models de P09+ y muestran estados vacíos honestos; no se inventan reglas ni métricas.
- Riesgos: revisión manual NVDA/VoiceOver para release institucional; B1 externo, MFA privilegiado y antimalware externo siguen documentados. `feature-delivery` y reviewers especializados no están expuestos en la sesión; revisión manual read-only sin Critical/High reproducibles. No commit automático.
- Siguiente: leer y ejecutar `prompts/10_DASHBOARD_AUDIT_UX.md` como P09.

## 2026-08-16 05:53 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P09 (`prompts/10_DASHBOARD_AUDIT_UX.md`).
- Cambios: read model y endpoint autenticado `GET /api/v1/academic-overview` con ownership/RBAC, ETag, ledger de créditos, componentes/grupos, requisitos externos, `UNKNOWN`, warnings, elegibilidad conservadora, próximos desbloqueos, hashes y evidencia; dashboard `/` y `/audit` conectado al cliente OpenAPI sin recálculo en frontend; estados sin historial/incompletos, deep links, disclosure de evidencia, fixture de estudiante y servidor E2E; ADR-0014 y documentación API/UX/frontend actualizadas.
- Verificaciones: overview focalizado 3/3 SQLite y 3/3 PostgreSQL; `python scripts/verify.py` PASS con 63 tests + 1 skip esperado; PostgreSQL full suite PASS con 64 tests; Compose healthy, migraciones/check PASS; OpenAPI/cliente PASS; Ruff/format/mypy/ESLint/TypeScript PASS; Vitest 5 archivos/8 tests + axe PASS; Next build PASS; Playwright 6/6 desktop/mobile PASS.
- Resultados: gates P09 satisfechos; 100% de créditos no se presenta como graduación cuando faltan requisitos externos/UNKNOWN; B1 permanece visible como `UNKNOWN` con evidencia/estado; no hay fallos funcionales pendientes dentro del alcance.
- Pendiente: B1 requiere snapshot normativo archivado; NVDA/VoiceOver y reviewers especializados no están disponibles en esta sesión, por lo que queda revisión manual read-only documentada. `docs/SPEC.md` y `docs/REQUIREMENTS.md` no existen en el kit original y deberán declararse en la auditoría final. No commit automático.
- Siguiente: leer y ejecutar `prompts/11_CURRICULUM_MAP.md` como P10.

## 2026-08-16 06:47 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P10 (`prompts/11_CURRICULUM_MAP.md`).
- Cambios: read model `GET /api/v1/curriculum-map` con ownership/RBAC, ETag, layouts no normativos, dependencia determinista, evidencia/AST, oferta explícita, estado personal protegido y contrato OpenAPI; frontend `/curriculum` y `/curriculum/print` con CourseCard interactiva, filtros, selección contextual, ficha, leyenda, componente/grupo, mobile roadmap, print y preferencias persistidas; corrección del runtime standalone de Next; ADR-0015 y documentación UX/diseño/frontend/API.
- Verificaciones: 3 tests focalizados SQLite; suite SQLite 66 passed + 1 skip esperado; PostgreSQL 67 passed; `scripts/verify.py` PASS; OpenAPI/cliente/breaking diff; migraciones/check; Ruff/format/mypy/ESLint/TypeScript; Vitest 6 archivos/12 tests + axe; build Next; Playwright 8/8 desktop/mobile; `pnpm audit`/`uv pip check`; deploy check con configuración de producción efímera sin warnings; baseline real importado como DRAFT en PostgreSQL (102 cursos, 3 componentes, 12 grupos, 97 membresías, 12 ambigüedades); Django+Next+Chromium real verificó health, map 200/ETag, 102 tarjetas, selección/ficha y print.
- Pendiente: B1 externo sigue `UNKNOWN`; `docs/SPEC.md`, `docs/REQUIREMENTS.md` y `docs/07_CURRICULUM_MAP_SPEC.md` no existen; reviewers/skill feature-delivery no están expuestos; NVDA/VoiceOver, MFA privilegiado y antimalware externo quedan documentados para fases posteriores. No hay fallo funcional P10 pendiente; no commit automático.
- Siguiente: leer y ejecutar `prompts/12_DEPENDENCY_GRAPH.md` como P11.

## 2026-08-16 11:13 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P11 (`prompts/12_DEPENDENCY_GRAPH.md`).
- Cambios: proyección semántica pura del AST en `domain/rules/graph.py` con nodos de cursos/condiciones, relaciones directas/transitivas, rutas, foco, desbloqueos y ciclos; read model/API `/api/v1/dependency-graph` con ETag, evidencia, estados epistemológicos y autorización; OpenAPI/cliente regenerados; `/graph` React Flow + ELK lazy, filtros, textual alternative, ciclos y canvas no editable; ADR-0016 y documentación UX/diseño/frontend/API; prueba de regresión del cliente.
- Reparación durante verificación: `openapi-fetch` requiere filtros en `params.query`; el adaptador los enviaba bajo `query`, lo que descartaba `selected` en producción. Se corrigieron overview/map/graph y se añadió `apps/web/tests/api.test.ts`.
- Verificaciones: 6 tests focalizados SQLite; `scripts/verify.py` PASS con 72 tests + 1 skip; PostgreSQL full suite PASS con 73; migraciones/check/OpenAPI/client PASS; frontend 8 archivos/15 tests, axe, lint, typecheck, build y E2E 10/10 PASS; audit/pip/diff/TODO PASS; Django/PostgreSQL/Next/Chromium real verificó 200/ETag, 126 nodos, 87 relaciones y foco `2016379`.
- Pendiente: B1 sigue `UNKNOWN` por falta de snapshot normativo; `docs/SPEC.md`/`docs/REQUIREMENTS.md` no existen; NVDA/VoiceOver y reviewers especializados no están disponibles. No commit automático.
- Siguiente: leer y ejecutar `prompts/13_OFFERINGS_SCHEDULES.md` como P12.

## 2026-08-16 12:24 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P12 (`prompts/13_OFFERINGS_SCHEDULES.md`).
- Cambios: modelo temporal de términos/ofertas/grupos/reuniones con
  `SourceSnapshot`, capacidad opcional, fechas parciales y sesiones alternas;
  dominio puro de frescura y conflictos exactos; `OfferingSourceAdapter`,
  importador JSON idempotente con hash y adaptador SIA seguro; CRUD scoped/API
  de términos, ofertas, reuniones y evaluación de agenda; `/offerings` con
  filtros, badges, fuente/timestamp, capacidad honesta, selección optimista y
  ScheduleGrid/conflictos; OpenAPI/cliente, ADR-0017, registro de fuentes y
  docs actualizados.
- Reparaciones durante verificación: se validó `day_of_week` para mypy; se
  tipó correctamente el read model de elegibilidad; se aplicó la migración
  SQLite y PostgreSQL `offerings.0002`; se corrigió la selección controlada
  durante navegación Next y se amplió el timeout del smoke del grafo lazy.
- Verificaciones: 5 tests focalizados; `scripts/verify.py` PASS con 77 passed
  + 1 skip; frontend 9 archivos/18 tests+axe, lint/typecheck PASS; build
  standalone PASS; E2E 12/12 desktop/mobile PASS; PostgreSQL real importó 2
  ofertas/2 grupos/2 reuniones y devolvió 200/ETag con 26 conflictos; Next
  standalone + Chromium verificó `/offerings` y comparación real de grupos.
- Pendiente: B1 sigue `UNKNOWN`; captura SIA actual requiere proceso autorizado
  y no se automatiza acceso autenticado; `docs/SPEC.md` y
  `docs/REQUIREMENTS.md` no existen; reviewers/skills especializados y
  NVDA/VoiceOver no están disponibles. No commit automático.
- Siguiente: leer y ejecutar `prompts/14_PLANNER.md` como P13.

## 2026-08-16 16:20 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P13 (`prompts/14_PLANNER.md`).
- Cambios: escenarios persistentes privados/versionados; cursos planificados
  por término y sección; preferencias; validador puro de prerrequisitos,
  correquisitos, oferta, disponibilidad y conflictos; locks; duplicar/archivar;
  comparación; sharing redacted; `ScenarioAuditProjection` sin mutar historia;
  API OpenAPI/cliente; `/planner` accesible y BFF; ADR-0018 y docs actualizadas.
- Reparaciones: se tiparon `PlanScenario.save()` y helper de test para mypy; se
  ajustó `scripts/verify.py` a `python -m pytest` por bloqueo del ejecutable en
  Windows; se aplicó `planning.0004` en PostgreSQL; se renovó CSRF después del
  login en la verificación HTTP real.
- Verificaciones: P13 focalizado 6/6; backend completo 83 passed + 1 skip
  esperado; `scripts/verify.py` PASS; migraciones/OpenAPI/cliente/Ruff/format/
  mypy/ESLint/TypeScript PASS; Vitest 20/20 + axe; build standalone PASS;
  Playwright 14/14 desktop/mobile; audit/pip/secret/TODO/diff PASS; PostgreSQL
  real y Next standalone verificaron login, escenario, proyección, curso,
  sharing/404, archive, BFF y `/planner`.
- Pendiente: B1 externo UNKNOWN, fuente SIA institucional autorizada, revisión
  NVDA/VoiceOver y reviewers especializados; `docs/SPEC.md`/`REQUIREMENTS.md`
  ausentes. No commit automático.
- Siguiente: leer y ejecutar estrictamente `prompts/15_OPTIMIZER.md` como P14.

## 2026-08-16 17:50 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P14 (`prompts/15_OPTIMIZER.md`).
- Cambios: motor puro CP-SAT con snapshot canónico, variables de curso/período
  y grupo, restricciones académicas/temporales/horarias, políticas UNKNOWN,
  objetivos lexicográficos sin pesos mágicos, límites/cancelación/estados y
  explicaciones; `OptimizationRun` persistido con hashes/solver metadata; API,
  OpenAPI/cliente, BFF, panel de comparación y ADR-0019.
- Reparaciones: el preflight de locks usaba la variable residual del último
  candidato; se corrigió para consultar el candidato bloqueado. Se impidió
  reprogramar aprobados, se añadió error 400 para políticas inválidas y se
  incorporó una propiedad Hypothesis/regresiones.
- Verificaciones: focalizado 11 passed; backend final 94 passed + 1 skip
  esperado; `scripts/verify.py` PASS; migraciones SQLite/PostgreSQL,
  OpenAPI/cliente, Ruff/format/mypy, ESLint/TypeScript/Vitest 21/21 + axe,
  build Next y Playwright 14/14 desktop/mobile PASS; audit/pip/deploy/secret/
  diff checks PASS.
- Integración real: PostgreSQL/Django y Next standalone+BFF verificaron login,
  escenarios, optimizer 202, polling `INFEASIBLE` con output hash/conflicto y
  `/planner` 200 con origen CSRF/CORS explícito.
- Pendiente global: B1 UNKNOWN por falta de evidencia institucional; revisores
  especializados/NVDA/VoiceOver no expuestos; `docs/SPEC.md`,
  `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md` ausentes. No commit automático.
- Siguiente: leer y ejecutar estrictamente `prompts/16_ADMIN_GOVERNANCE.md` como
  P15.

## 2026-08-16 18:51 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P15 (`prompts/16_ADMIN_GOVERNANCE.md`).
- Cambios: backoffice `/sources`; Source Inbox, documentos/snapshots,
  candidatos de extracción, diff semántico, validación/impacto, inspector AST
  + explicación humana + evidencia, review queue y publicación con recibo;
  `ExtractionCandidate`, `Review`, `Publication`, migración `governance.0003`,
  ETag/If-Match, preview-token bulk review, editor/reviewer separation, audit
  trail relacionado, OpenAPI/cliente, UI responsive y ADR-0020.
- Reparaciones: se corrigió el locking Postgres de propuestas con outer join
  nullable (`select_for_update(of=("self",))`), se actualizó la auditoría para
  incluir candidatos/requisitos/publicaciones relacionados y se hizo visible
  el resultado del vínculo de evidencia en la UI.
- Verificaciones: 4/4 SQLite + 4/4 PostgreSQL focalizados; suite 98 passed + 1
  skip esperado; `scripts/verify.py` PASS; migraciones/check/OpenAPI/client,
  Ruff/format/mypy/ESLint/TypeScript PASS; Vitest 23/23 + axe; Next build
  PASS; Playwright 16/16 desktop/mobile PASS; HTTP real PostgreSQL/Django
  inbox/detail/submit/request-changes/restore PASS.
- Pendiente: P16 en adelante; B1 `UNKNOWN`; `docs/SPEC.md`,
  `docs/REQUIREMENTS.md` y `docs/ACCEPTANCE.md` ausentes; reviewers
  especializados y NVDA/VoiceOver no expuestos; no commit automático.
- Siguiente: leer y ejecutar estrictamente `prompts/17_PUBLICATION_IMPACT.md`
  como P16.

## 2026-08-16 19:50 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P16 (`prompts/17_PUBLICATION_IMPACT.md`).
- Cambios: publicación transaccional con supersesión, `PublicationEvent`,
  `PublicationImpact` por matrícula y `NotificationOutbox`; endpoint de impacto,
  OpenAPI/cliente, vista `/sources`, auditoría relacionada, migraciones
  `governance.0004`/`notifications.0001`, ADR-0021 y documentación de
  versionado/procedencia/auditoría/backoffice/eventos/notificaciones.
- Reparaciones: se eliminó la limpieza de conexión del ejecutor síncrono que
  rompía requests posteriores en PostgreSQL; se hizo UTF-8 el guard TODO en
  Windows; se aisló el estado mutable del fixture editorial E2E para evitar que
  desktop/mobile compartieran el estado de una propuesta.
- Verificaciones: 3 focused SQLite + 3 PostgreSQL; suite PostgreSQL 102 passed;
  suite canónica SQLite 101 passed + 1 skip esperado; `scripts/verify.py`
  PASS; migraciones/check/OpenAPI/client/Ruff/formato/mypy/ESLint/TypeScript
  PASS; Vitest 23/23 + axe; build Next PASS; Playwright 16/16 desktop/mobile;
  `pnpm audit`, `uv pip check`, diff y guard TODO UTF-8 PASS.
- Pendiente: P17 en adelante; el outbox está listo pero el dispatcher/entrega
  efectiva pertenece a P17; B1 `UNKNOWN`; documentos
  `docs/24_PUBLICATION_AND_IMPACT.md`/`docs/05_AUDIT_AND_CREDIT_ALLOCATION.md`
  y `docs/SPEC.md`/`REQUIREMENTS.md`/`ACCEPTANCE.md` no existen; reviewers y
  NVDA/VoiceOver no expuestos; no commit automático.
- Siguiente: leer y ejecutar estrictamente `prompts/18_NOTIFICATIONS.md` como
P17, empezando por outbox, dispatcher, deduplicación, reintentos y canales.

## 2026-08-16 20:48 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P17 (`prompts/18_NOTIFICATIONS.md`).
- Cambios: `NotificationEvent`/`Delivery`/`Preference`, outbox post-commit,
  dispatcher y management command con deduplicación/backoff, draft gate,
  plantillas `es-CO`/`en`, adaptador email opcional/idempotente, API de feed,
  lectura/preferencias con cursor, cliente OpenAPI, centro frontend accesible,
  fixture E2E, migración `notifications.0002`, ADR-0022 y documentación de
  seguridad/eventos/API/ERD/notificaciones.
- Reparaciones: se implementó cursor consumible en vez de `next_cursor` falso;
  se añadió prueba IDOR/cursor; se formatearon tres archivos que el verificador
  detectó; se reconstruyó el standalone antes de E2E para evitar probar un
  build anterior.
- Verificaciones: 5 focused SQLite + 5 PostgreSQL; `scripts/verify.py` PASS con
  106 backend tests + 1 skip esperado y Vitest 26/26 + axe; OpenAPI/client,
  migraciones, Ruff/formato/mypy/ESLint/TypeScript PASS; Next build PASS;
  Playwright 18/18 desktop/mobile; `pnpm audit`, `uv pip check`, deploy check
  explícito, diff y guard TODO UTF-8 PASS.
- Pendiente global: P18–P26; B1 `UNKNOWN`; email no configurado localmente;
  reviewers/NVDA/VoiceOver no expuestos; `docs/SPEC.md`, `docs/REQUIREMENTS.md`
  y `docs/ACCEPTANCE.md` ausentes; no commit automático.
- Siguiente: leer y ejecutar estrictamente `prompts/19_ANALYTICS.md` como P18.

## 2026-08-16 21:33 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P18/P19 (`prompts/19_ANALYTICS.md`), tratados
  como un bloque porque el prompt contiene analítica estudiantil e institucional.
- Cambios: servicios y API de analytics sobre auditorías `PUBLISHED`, métricas
  privadas, tendencias, cuellos de botella, requisitos, escenarios, agregados
  institucionales, demanda potencial, rutas HMAC, duración observada, RBAC de
  alcance, supresión de celdas, exportación JSON/CSV auditada, definiciones,
  OpenAPI/cliente y página frontend `/analytics` con accesibilidad. ADR-0023
  y documentación de analítica/seguridad/RBAC añadidas.
- Reparaciones: se corrigieron fixture de créditos no reconciliados, contrato
  `as_of` date-time, validación de período institucional, localizadores E2E
  estrictos y se reconstruyó el standalone antes de repetir Playwright.
- Verificaciones: 4 focused SQLite + 4 PostgreSQL; `scripts/verify.py` PASS
  con 110 backend tests + 1 skip esperado; OpenAPI/client, migraciones,
  Ruff/formato/mypy, ESLint/TypeScript; Vitest 30/30 + axe; Next build y
  Playwright 20/20 desktop/mobile; audit/pip checks previos PASS.
- Limitaciones: `feature-delivery`/`security-change` y reviewers
  especializados no están expuestos; revisión manual read-only completada;
  NVDA/VoiceOver no disponibles; B1 sigue `UNKNOWN`; documentos
  `docs/SPEC.md`, `docs/REQUIREMENTS.md`, `docs/ACCEPTANCE.md` ausentes; no
  commit automático.
- Siguiente: leer completamente `prompts/20_OBSERVABILITY.md` como P20.

## 2026-08-16 22:25 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P20 (`prompts/20_OBSERVABILITY.md`). Se leyó el
  prompt completo, `docs/20_OBSERVABILITY_OPERATIONS.md`, estado, seguridad,
  autorización y baseline tecnológico; la skill `feature-delivery` y los
  reviewers especializados no están expuestos, por lo que se hizo revisión
  manual read-only.
- Cambios: módulo backend de redacción/log JSON/correlación/OTel/métricas,
  middleware de requests, health live/ready/metrics, timing para auditoría,
  grafo, optimizer, importación, publicación y notificaciones; exporter OTLP
  HTTP 1.44.0 fijado en pyproject/lock. Adaptador frontend opt-in de errores y
  Web Vitals; dashboard/runbooks/smoke/ADR-0024; OpenAPI/cliente regenerados.
- Reparaciones: el smoke inicialmente truncaba el OpenAPI grande y se amplió
  con techo de 4 MiB; se evitó ocultar UUIDs de correlación en logs; se
  protegió `/health/metrics` en producción, se añadió no-store y se reconstruyó
  standalone después de detener el servidor que bloqueaba `.next` en Windows.
- Verificaciones: focused observability 7 passed; `scripts/verify.py` PASS con
  117 backend + 1 skip y 33 frontend; PostgreSQL migrate/makemigrations check,
  plan 0 y suite 118 passed; `pnpm build`; Playwright 20/20 desktop/mobile;
  API/Web reales en 8020/3020 y smoke live/ready/OpenAPI/Web PASS; headers
  correlation/trace/no-store observados; `pnpm audit`, `uv pip check`,
  `check --deploy`, OTel imports y `git diff --check` PASS.
- Limitaciones: el guard TODO amplio sólo encuentra referencias históricas en
  documentación/metadatos y no TODO funcional nuevo; no hay SLO numérico sin
  baseline; métricas en memoria requieren collector OTLP para persistencia;
  B1 continúa UNKNOWN; faltan `docs/SPEC.md`, `docs/REQUIREMENTS.md` y
  `docs/ACCEPTANCE.md`; no commit automático.
- Siguiente: leer y ejecutar estrictamente `prompts/21_PERFORMANCE.md` como P21.

## 2026-08-16 23:07 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P21 (`prompts/21_PERFORMANCE.md`). Se leyó el
  prompt completo, `docs/25_PERFORMANCE.md`, requisitos no funcionales,
  estrategia de pruebas y estado del repositorio. La skill
  `feature-delivery` y reviewers especializados no están expuestos; se hizo
  revisión manual read-only de arquitectura, código, currículo, seguridad y
  UX.
- Cambios: benchmark de reglas/servicios/consultas/EXPLAIN, load probe y
  auditoría de bundle; helper SQL de enrollment prioritario; prefetch de
  evidencias en snapshots de auditoría; índices internos reutilizados para
  mapa/grafo; límites de tiempo/workers/jobs del optimizador; tests de query
  budget/capacidad; documentación de baseline y ADR-0025.
- Reparaciones: el primer profiling reveló 164 consultas en auditoría; se
  localizó `requirement.evidence.all()` dentro de `build_revision_snapshot` y
  se redujo a 19 con `prefetch_related("evidence__snapshot")`. Mypy detectó
  una reutilización de nombre entre lista y set en el índice de desbloqueos;
  se renombró y volvió a pasar. Se ajustó el benchmark para crear un
  enrollment válido efímero y hacer rollback, sin mutar la base local.
- Verificaciones: `tests/test_performance.py` 4 passed; regresión focalizada
  34 passed; `scripts/verify.py` PASS con 122 backend y 33 frontend; benchmark
  PostgreSQL p95 reglas 16.489 µs, mapa 172.191 ms, grafo 168.314 ms,
  auditoría 239.645 ms; queries 16/16/19; EXPLAIN usa índices existentes;
  Next build, bundle audit, Playwright 20/20, smoke/API/Web real, migraciones
  plan 0/PostgreSQL 18, deploy check, audit de dependencias, pip check y
  diff check PASS.
- Limitaciones: el load probe concurrente contra `runserver` mostró
  contención propia del servidor de desarrollo, no un SLO de producción. El
  baseline de despliegue requiere worker/proxy/pool y siete días de OTel;
  no se añadió caché ni Redis por intuición. `check_no_todos.py` reportó 35
  hits históricos/documentales/metadatos/propios, sin TODO funcional P21.
  B1 sigue `UNKNOWN`; faltan las tres especificaciones globales; no hubo
  commit automático.
- Siguiente: leer y ejecutar estrictamente `prompts/22_ACCESSIBILITY_E2E.md`
  como P22.

## 2026-08-16 23:55 — Codex / GPT-5

- Objetivo: ejecutar y cerrar P22 (`prompts/22_ACCESSIBILITY_E2E.md`). Se leyó
  el prompt completo, `docs/26_ACCESSIBILITY.md`, arquitectura UX, design
  system, estrategia de pruebas y requisitos no funcionales. Los reviewers y
  `feature-delivery` no están expuestos; se hizo revisión manual read-only.
- Baseline: un probe page-level axe encontró contraste serio del token
  `#6f8177` (4.13:1 sobre blanco) y abrió el área de foco/landmarks para
  revisión. El bundle viejo se distinguió del bundle reconstruido antes de
  aceptar resultados.
- Cambios: suite `accessibility.spec.ts`, foco/restauración/Escape del menú
  móvil, foco de ficha curricular y foco/anuncio del grafo, handles React Flow
  sin ARIA inválido, fixture de grafo sensible a `selected`, selector y
  columnas del planner con nombres accesibles, token `--text-muted` corregido,
  checklist manual de contraste/NVDA/VoiceOver, workflow editorial E2E
  extendido hasta publicación y backoffice con una sola landmark `main`.
- Reparaciones: se limpió el artefacto de cero bytes generado por el panic de
  Turbopack (`apps/web/n.target)}))}))`); se reconstruyó Next standalone; se
  corrigió `setState` síncrono en efecto señalado por ESLint; se repararon
  aserciones de fixture/viewport y finalmente los landmarks duplicados de
  `/sources`. El gate axe se endureció de serious/critical a cero violaciones.
- Verificaciones: Vitest 33/33, lint, typecheck, build Next 16.3.1, E2E
  completo 50/50 desktop/mobile, axe final 20/20 sin violaciones y suite
  focalizada 10/10. Se documentaron ratios WCAG y las comprobaciones manuales
  que no pueden ejecutarse con el entorno headless.
- Limitaciones: NVDA/VoiceOver/dispositivo físico no disponibles; B1 sigue
  `UNKNOWN`; faltan `docs/SPEC.md`, `docs/REQUIREMENTS.md` y
  `docs/ACCEPTANCE.md`; no commit automático.
- Siguiente: leer y ejecutar estrictamente `prompts/23_SECURITY_HARDENING.md`
  como P23.

## 2026-08-17 00:04 — cierre verificable de P22

- Se repitió `pnpm e2e` completo después de corregir el landmark duplicado de
  `/sources`; el resultado final fue 50/50 desktop/mobile PASS. El resultado
  incluye 20/20 ejecuciones axe sin violaciones y los flujos de teclado, foco,
  planner móvil, zoom 200%, reduced motion, journeys y publicación editorial.
- `scripts/verify.py` terminó con 122 pruebas backend y 33 frontend PASS,
  además de Ruff, mypy, cliente OpenAPI, ESLint y TypeScript.
- P22 queda cerrado; el siguiente trabajo es el threat model y hardening de
  P23. Los reviewers especializados y las Skills `security-change` y
  `feature-delivery` no están expuestos en esta sesión; se documentará la
  revisión manual equivalente.

## 2026-08-17 01:08 — cierre verificable de P23

- Objetivo: ejecutar y cerrar P23 (`prompts/23_SECURITY_HARDENING.md`). Se leyó
  el prompt completo, threat model, autorización, privacidad, importación,
  observabilidad, despliegue y estrategia de pruebas. Las Skills y reviewers
  especializados de seguridad no están expuestos; se realizó revisión manual
  read-only y no se fabricó sign-off.
- Cambios: trust boundaries y matriz IDOR/BOLA; `SafeSourceFetcher` con
  allowlist, validación DNS/redirect, conexiones fijadas y límites; rate
  limiting de mutaciones; headers; upload storage privado; audit log inmutable;
  secret scan/SAST; workflow de seguridad; SQL de roles mínimos y runbook.
- Reparación: `pip-audit==2.9.0` encontró vulnerabilidades corregibles en
  `pypdf==6.10.0`; se actualizó a `pypdf==6.16.1`, se regeneró `uv.lock`, se
  reinstaló con `--frozen` y pasaron los tests del parser. El escáner encontró
  y corrigió un falso positivo específico para nombres de variables psql,
  manteniendo la detección de valores reales.
- Verificaciones: security/history/identity 34 passed y 10 subtests; parser
  PDF 23 passed y 1 skip; secret scan, SAST, pip-audit sin vulnerabilidades
  conocidas, `uv pip check`, `pnpm audit`; `scripts/verify.py` PASS con 131
  backend passed, 1 skip esperado y 33 frontend passed, además de migraciones,
  OpenAPI/cliente, Ruff, formato, mypy, ESLint y TypeScript.
- Limitaciones: MFA/IdP institucional, antimalware gestionado, egress de red y
  rotación operativa de secretos son prerrequisitos externos documentados; B1
  continúa UNKNOWN sin snapshot normativo; faltan las tres especificaciones
  globales; no hubo commit automático.
- Siguiente: leer y ejecutar estrictamente `prompts/24_DEPLOYMENT_DR.md` como
  P24.

## 2026-08-17 — cierre documentado de P24–P99 y auditoría final parcial

- Se ejecutaron lexicográficamente los prompts disponibles posteriores a P23
  y se inspeccionaron sus referencias antes de modificar el repositorio.
- P24: infraestructura de producción, Compose, imágenes no-root, healthchecks,
  backup/restore/smoke/scan scripts, workflows y ADR-0027. Verificación
  estática PASS; Docker CLI/socket no accesible, por lo que build, scan,
  restore y smoke reales quedaron `BLOCKED_EXTERNAL`.
- P25: matriz de trazabilidad y auditoría de sistema; `verify_docs_clone_clean`
  integrado y PASS. El sign-off especializado queda pendiente porque los
  reviewers no están expuestos.
- P26: source watch, cola de reglas `UNKNOWN`, mantenimiento DB, baseline y
  workflows recurrentes; offline PASS, remoto `ERROR` por `WinError 10013`.
- P90: reauditoría oficial del plan 2514 con snapshot, comparación semántica y
  registro de fuentes. Hash del PDF local y JSON PASS; no se publicó ninguna
  regla remota o inferida.
- P91: revisión de dependencias y advisory de Next; se propuso resolver
  `next@16.2.12` estable, pero el registry no está accesible. No se modificó
  lockfile manualmente.
- P92: auditoría cognitiva de las vistas y bundle; historial P22 de 50/50 E2E,
  20/20 axe y 33 Vitest PASS; rerun actual y lector de pantalla bloqueados.
- P93: revisión estática de bugs/deuda sin bug activo reproducible; P95: runbook
  de incidentes documentado; ambos quedaron cerrados en su alcance posible.
- P94: prueba sintética multi-programa y documento de límites; `py_compile`
  PASS, ejecución Django pendiente por runtime.
- P98: gate anti-MVP PASS sobre 196 archivos/14 contextos/0 señales y creación
  de los índices canónicos `docs/SPEC.md`, `docs/REQUIREMENTS.md` y
  `docs/ACCEPTANCE.md`.
- P99: recovery PASS (`27 done`, `8 in_progress`, sin errores), checks
  estáticos PASS y `scripts/verify.py` finalizado con bloqueos explícitos en
  vez de fallar silenciosamente; se documentó que el Goal global sigue abierto.

### Comandos y resultados del cierre

- PASS: `python scripts/verify_deployment.py`.
- PASS: `python scripts/verify_state_recovery.py`.
- PASS: `python scripts/anti_mvp_audit.py`.
- PASS: `python scripts/verify_docs_clone_clean.py`.
- PASS: `python scripts/update_technology_baseline.py --check`.
- PASS: JSON/Markdown checks, source watch offline, curriculum invariants,
  OpenAPI breaking diff y `py_compile` compatible.
- NO CERRADO: `scripts/verify.py` global, backend Django/Python 3.14, pnpm
  frontend, integración/E2E actual, Docker/DB, source watch remoto y manual
  accessibility, por restricciones de ACL/red/runtime descritas en
  `docs/state/CURRENT_STATE.md`.
- `scripts/check_no_todos.py` se inició pero no produjo salida durante más de
  un minuto y se interrumpió para no dejar un proceso colgado; `anti_mvp_audit`
  y la búsqueda `rg` equivalente no encontraron deuda funcional en producto.

No se hicieron commits, pushes, despliegues ni publicaciones normativas.

## Continuación del Goal — 2026-08-17 — reparación del gate TODO

- Inspeccioné de nuevo AGENTS, CURRENT_STATE, ROADMAP, OPEN_DECISIONS, git y
  todos los prompts lexicográficos. Los runtimes siguen sin Python 3.14
  ejecutable, Django/uv funcional, Docker o paquetes Node legibles.
- Pnpm confirmó que el lockfile está instalado pero la instalación aislada
  offline no puede resolver metadata de `@testing-library/react` porque el
  mirror de registry está inaccesible; no se modificaron lockfiles ni manifests.
- Corregí `scripts/check_no_todos.py`: ahora poda `.pnpm-store`, caches y
  dependencias, reporta errores de lectura, clasifica hits no funcionales y
  falla sólo ante marcadores dentro de código de producto.
- Integré el gate al verificador canónico `scripts/verify.py`.
- Resultado: `files_scanned=508`, `nonfunctional_hits=46`,
  `functional_hits=0`, `TODO_RELEASE_GATE=PASS`; `py_compile`, anti-MVP y
  docs clone-clean también PASS.
- `scripts/verify.py` vuelve a llegar a todos sus gates con el TODO gate PASS,
  pero permanece no-cero por SAST/runtime/Node/DB/Docker, sin ocultar esos
  bloqueos.

## Continuación del Goal — 2026-08-17 — probe de runtime Python

- Intenté recuperar Python 3.14 sin tocar el venv existente usando
  `uv --cache-dir .uv-cache python install 3.14 --install-dir .uv-python`.
- El intento falló después de tres reintentos por `WinError 10013` al acceder
  a GitHub/releases.astral.sh; no se instaló un binario alternativo ni se
  modificó el lockfile. Los directorios de probe quedaron fuera del alcance
  del código y no contienen cambios de producto.
- La alternativa Node/pnpm offline tampoco pudo recrear dependencias aisladas:
  pnpm necesita metadata local de `@testing-library/react` que no está
  disponible en el mirror accesible. Se detuvo el proceso de probe iniciado
  por esta sesión.

## Continuación del Goal — 2026-08-17 11:56 -05:00 — reparación de integridad y gates de seguridad

- Revisé los hallazgos read-only de arquitectura, seguridad, código y UX.
- Implementé inmutabilidad de filas hijas de revisiones publicadas y enlaces
  de evidencia; añadí validaciones de scope para plan membership, grupos,
  términos, ofertas, matrículas y course attempts, con migraciones PostgreSQL
  para proteger también `QuerySet`/cargas masivas.
- Reforcé el fetcher SSRF contra direcciones no globales, la autorización MFA
  fail-closed y el alcance editorial por institución/programa. `RoleAssignment`
  ya no es editable desde admin.
- Añadí protección `m2m_changed` para evidencia de requisitos publicados,
  pruebas de MFA/scoping/operaciones, el helper de cleanup del restore y el
  verificador de pins inmutables para GitHub Actions.
- Anclé los workflows a commits verificados de las releases usadas y pasé
  explícitamente `PRIVILEGED_MFA_REQUIRED` a Compose de producción.
- PASS ejecutable en esta estación: py_compile focalizado de cambios,
  action pins, deployment assets, secret scan, docs clone-clean, state
  recovery, TODO gate, anti-MVP, curriculum invariants, OpenAPI breaking diff,
  helpers operativos y `git diff --check`.
- `scripts/verify.py` se ejecutó completo y terminó `FAIL` honesto: SAST no
  puede parsear Python 3.14 con el bundled 3.12; uv/Django/pytest/Ruff/mypy,
  Node/pnpm/openapi-typescript y Docker/PostgreSQL siguen bloqueados por ACL,
  red o ausencia de herramienta. No se actualizaron lockfiles ni se hicieron
  commits.

## Continuación del Goal — 2026-08-17 12:18 -05:00 — corrección del workflow y cierre estático

- La revisión de `.github/workflows/production-gates.yml` encontró que el
  servicio PostgreSQL declaraba `POSTGRES_USER: curriculum_runtime`, mientras
  el healthcheck y dos gates usaban `curriculum`. Se corrigieron esos tres
  usos; el job de restore mantiene su usuario explícito independiente.
- Repetí `check_action_pins`, `verify_deployment`, `check_no_todos`,
  `anti_mvp_audit`, `validate_curriculum`, `verify_docs_clone_clean`,
  `source_freshness --offline`, `verify_state_recovery`, `scan_secrets`,
  `git diff --check` y `py_compile` focalizado: PASS. Los conteos actuales son
  525 archivos escaneados por el guard TODO, 0 funcionales, y 200 archivos de
  producto en el gate anti-MVP, 14 contextos, 0 issues.
- `scripts/verify.py` volvió a terminar en FAIL reproducible por el mismo
  conjunto externo: Python 3.12 no puede validar sintaxis 3.14, uv/Django no
  arrancan, Node/pnpm tiene EPERM en `node_modules`, falta el paquete
  accesible del cliente OpenAPI y no hay Docker/PostgreSQL. No se falsificó un
  PASS ni se modificaron lockfiles.

## Continuación del Goal — 2026-08-17 13:08 -05:00 — Chrome real y cierre funcional

- Se controló la sesión actual de Chrome y se recorrió la aplicación como
  administrador y estudiante, inspeccionando consola y estado visible.
- Se validaron rutas públicas, editoriales y privadas; login/logout; separación
  de capacidades; filtros y detalle de malla; creación de escenario y curso;
  creación y anulación auditable de un intento académico.
- Se corrigieron home/navigation role-aware, selección filtrada de malla,
  hydration del planner, historia completa, importación/reconciliación,
  procedencia pública, control de concurrencia `If-Match`, locks de import,
  `ANNULLED` reservado al comando dedicado y cache privado `no-store`.
- Se exportó OpenAPI y regeneró el cliente TypeScript.
- `python scripts/verify.py` terminó `PASS`: backend `149 passed, 1 skipped`
  esperado; frontend `15 files, 39 tests`; Ruff/format/mypy/ESLint/TypeScript,
  migraciones, Django, contrato, secretos, SAST y gates documentales pasan.
- Reviewers read-only de seguridad y UX reportaron `0 Critical / 0 High`; se
  pidió revisión final de código después de cerrar la última vía backend de
  `ANNULLED`.
- No se creó commit, push ni despliegue. Permanecen como trabajo explícito la
  prueba production-like/Compose, parser PDF aislado, minimización de
  `raw_payload`, cursor estable de historia y traducción del detalle técnico de
  importación.
- Una revisión final encontró y se cerraron dos regresiones de concurrencia:
  la UI refresca la versión autoritativa del lote después de cada resolución y
  un retry del mismo confirm ya aplicado devuelve éxito idempotente sin crear
  registros duplicados. Los tests HTTP cubren ambos caminos; el reviewer final
  confirmó `0 Critical / 0 High`.

## Continuación del Goal — 2026-08-17 16:20 -05:00 — persona nueva y aceptación de sexto semestre

- Se creó en la base local una persona de aceptación nueva, matrícula activa
  del plan 2514, seis períodos y 23 intentos reales persistidos; el frontend no
  usa mocks ni hardcodes para sus resultados. La historia es sintética y está
  identificada como tal, no como registro oficial UNAL.
- Chrome real verificó login de administrador, consola administrativa, login de
  estudiante, inicio, malla, auditoría, historia, oferta, planificador,
  analítica, grafo e importación.
- La prueba E2E encontró y corrigió un desfase de selección del planificador:
  el texto visible podía corresponder a 1000013 mientras el submit conservaba
  otro ID. Se unificaron inicialización, búsqueda y submit bajo el mismo orden
  priorizado y se añadieron regresiones por ID exacto.
- Se redujo el catálogo de períodos a abiertos/planeados o ya referenciados, se
  tradujeron tokens técnicos del grafo y flujos estudiantiles, se validó el
  curso manual contra el catálogo y se corrigió singular/plural del escenario.
- Consola fresca de Chrome en malla, planificador y grafo: cero `warn/error` de
  producto; cero alertas visibles y cero desbordamiento horizontal de documento.
- `python scripts/verify.py` PASS: backend 149 passed + 1 skip esperado;
  frontend 15 archivos/43 pruebas; lint, tipos, formato, migraciones, contrato,
  seguridad, anti-MVP e invariantes pasan. Suite focalizada UX 22/22 y planner
  final 5/5.
- Reviewers read-only de seguridad, UX y código: 0 Critical / 0 High. Quedan
  explícitos el scope multi-institución de términos, el gate production-like,
  aislamiento PDF, retención de payload y consolidación CSS. No se guardaron
  credenciales en Git y no hubo commit, push ni despliegue.

## Continuación del Goal — 2026-08-17 23:40 -05:00 — aceptación integral y cierre anti-MVP

- Se recorrió la sesión real de Chrome como administrador y como estudiante de
  aceptación de sexto semestre, con inspección visual, DOM accesible y consola.
- Se cerraron overflow móvil de malla, densidad de analítica/procedencia,
  resolución administrativa `NEEDS_REVIEW`, contexto de historia independiente,
  traducción de estados y ayudas de formularios.
- El flujo real persistido conserva lote aplicado con 23 candidatos, 23 intentos
  y 23 evidencias; 20 asignaturas aprobadas, 3 en curso, 70/141 créditos aplicados
  y escenario con curso 1000013 en 2026-2S.
- Se cerraron concurrencia temporal de import/manual mediante locks globales
  estables, replay sin atribución falsa de auditoría y payload analítico completo
  para matrículas en revisión.
- El BFF quedó acotado por tamaño, timeout, clase de solicitud, capacidad global
  por proceso y cuota por cliente; Problem Details y request IDs son uniformes.
- Backup y restore drill reales pasaron con SHA-256
  `eda98873688b5db4fe135b4cb24e0a72aad993348171af6ae190f99cb6972f33` y
  conteos de negocio en el mismo snapshot exportado.
- Revisores read-only de arquitectura, código, currículo, seguridad y UX:
  0 Critical / 0 High. No hubo commit, push ni despliegue.
- `python scripts/verify.py` final PASS: 170 backend passed + 1 skip esperado,
  16 archivos / 46 pruebas frontend, lint, tipos, formato, migraciones,
  OpenAPI/cliente, secretos, SAST, anti-MVP e invariantes curriculares PASS.

## Continuación — 2026-08-18 — bootstrap local y aceptación de administrador

- Se instaló el runtime local faltante (`uv` 0.11.19) y dependencias fijadas;
  Docker no está presente, por lo que la ejecución local usa SQLite.
- Se implementó y probó `bootstrap_local_admin`: credenciales locales sólo en
  `var/local-admin-credentials.txt` (`0600`) y directorio `0700`; README tiene
  únicamente instrucciones de creación/rotación.
- Se corrigieron permisos privados bajo `umask`, el constructor de backup sin
  Docker y los tipos Windows del aislamiento de parser.
- `python scripts/verify.py` PASS: 173 backend passed + 1 skip esperado,
  Vitest 16 archivos / 46 tests, checks, migraciones, Ruff, formato, mypy,
  OpenAPI/cliente, secretos y SAST verdes. Build Next PASS.
- Chrome real autenticó `admin@localhost` y mostró superficies editorial y
  administrativa. No se versionaron credenciales.
- Commit local `507df94` creado; push pendiente por ausencia de credenciales
  HTTPS de GitHub y de `gh` en este host (`main` está ahead 1).
