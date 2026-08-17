# P25 — Matriz de trazabilidad integral

Fecha de auditoría: 2026-08-17  
Fuente de alcance: [`docs/00_PRODUCT_SCOPE.md`](../00_PRODUCT_SCOPE.md)  
Fuentes funcionales complementarias: `docs/06_*`, `docs/08_*`,
`docs/10_*`–`docs/36_*`, `docs/41_ACCEPTANCE_GATES_MATRIX.md` y
`docs/acceptance/DOMAIN_ACCEPTANCE.md`.

Esta matriz es el índice verificable de alcance. Una fila sólo se marca como
`PASS` cuando identifica implementación, prueba y evidencia ejecutable. Los
datos normativos que no tienen snapshot oficial archivado conservan el estado
`INFERRED_PENDING_REVIEW`/`UNKNOWN`; no se convierten en una afirmación
académica publicada.

## Personas y permisos

| ID | Requisito de alcance | Implementación | Prueba/evidencia | Estado |
| --- | --- | --- | --- | --- |
| PS-PER-01 | Estudiante consulta trayectoria, auditoría, elegibilidad y planificación | `modules.student_records`, `modules.audit`, `modules.planning`, `apps/web/components/academic-dashboard.tsx`, `planner-board.tsx` | `tests/test_student_history.py`, `test_degree_audit.py`, `test_academic_overview.py`, `test_planning.py`; `tests/e2e/smoke.spec.ts` | PASS |
| PS-PER-02 | Aspirante explora currículo sin historia personal | `modules.curriculum.api`, `application/map.py`, `apps/web/app/curriculum/page.tsx` | `test_curriculum_map.py`, `curriculum-map.test.tsx`, E2E de currículo | PASS |
| PS-PER-03 | Asesor audita estudiantes y escenarios autorizados | `modules.identity.application.authorization`, `modules.audit.api`, `modules.planning.api` | `test_identity_security.py`, `test_degree_audit_service.py`, `test_planning.py` | PASS |
| PS-PER-04 | Editor propone y corrige cambios curriculares | `modules.governance.api`, `application/services.py`, `apps/web/components/governance-backoffice.tsx` | `test_governance_backoffice.py`, `governance-backoffice.test.tsx`, E2E editorial | PASS |
| PS-PER-05 | Revisor contrasta evidencia y publica una revisión | `modules.governance.application.services.publish_governance_proposal`, guards de rol y confirmación | `test_governance_backoffice.py`, `test_publication_impact.py`, E2E editor → reviewer → publish | PASS |
| PS-PER-06 | Analista ve sólo agregados autorizados | `modules.analytics.api`, `application/services.py` | `test_analytics.py`, `analytics-dashboard.test.tsx`, E2E analytics | PASS |
| PS-PER-07 | Administrador gestiona instituciones, programas, roles y fuentes | `modules.institutions`, `modules.identity`, `modules.governance` | `test_structure.py`, `test_identity_security.py`, `test_governance_backoffice.py` | PASS |

## Módulos finales obligatorios

| ID | Requisito | Implementación principal | Pruebas/evidencia | Estado |
| --- | --- | --- | --- | --- |
| PS-MOD-01 | Catálogo académico y currículo versionado | `modules.institutions.models`, `modules.curriculum.models`, migraciones de currículo | `test_domain_foundation.py`, `test_curriculum_ingestion.py`, `test_structure.py`; ADR-0004 | PASS |
| PS-MOD-02 | Motor de requisitos | `domain/rules/ast.py`, `evaluator.py`, `graph.py` | `test_rule_engine.py`, `test_dependency_graph.py`; golden + Hypothesis | PASS |
| PS-MOD-03 | Auditoría de grado | `modules.audit.application.services.py`, `overview.py`, `api.py` | `test_degree_audit.py`, `test_degree_audit_service.py`, `test_academic_overview.py` | PASS |
| PS-MOD-04 | Historia académica | `modules.student_records`, `modules.imports.application.history.py` | `test_student_history.py`, `test_security_hardening.py` | PASS |
| PS-MOD-05 | Malla curricular interactiva | `modules.curriculum.application.map.py`, `apps/web/components/curriculum-map.tsx` | `test_curriculum_map.py`, `curriculum-map.test.tsx`, E2E + print view | PASS |
| PS-MOD-06 | Grafo de dependencias | `domain/rules/graph.py`, `modules.curriculum.application.graph.py`, React Flow/ELK shell | `test_dependency_graph.py`, `test_dependency_graph_api.py`, `dependency-graph.test.tsx`, axe E2E | PASS |
| PS-MOD-07 | Oferta por período | `modules.offerings.models`, `application/services.py`, `api.py` | `test_offerings.py`, `offerings-explorer.test.tsx`, E2E offerings | PASS |
| PS-MOD-08 | Secciones y horarios | `domain/offerings/schedule.py`, `modules.offerings.models` | `test_offerings.py`, `test_planning.py`, E2E conflict flow | PASS |
| PS-MOD-09 | Planificador manual de escenarios | `domain/planning`, `modules/planning`, `planner-board.tsx` | `test_planning.py`, `planner-board.test.tsx`, E2E planner | PASS |
| PS-MOD-10 | Optimizador de trayectoria | `domain/optimization/model.py`, `solver.py`, `modules/optimization` | `test_optimization.py`, `test_optimization_api.py`, `test_performance.py`, E2E optimizer | PASS |
| PS-MOD-11 | Requisitos no crediticios de grado | `RequirementPurpose`, `RequirementKind`, audit read model `external_graduation_requirements` | `test_degree_audit.py`, `test_academic_overview.py`, `academic-dashboard.test.tsx` | PASS / UNKNOWN cuando falta evidencia |
| PS-MOD-12 | Equivalencias, homologaciones, sustituciones y excepciones | `modules.student_records.models`, audit ledger and recognition services | `test_student_history.py`, `test_degree_audit.py`, `test_academic_overview.py` | PASS |
| PS-MOD-13 | Importadores de historia y fuentes | `modules.imports.application`, private storage, governance source fetch | `test_curriculum_ingestion.py`, `test_student_history.py`, `test_security_hardening.py` | PASS |
| PS-MOD-14 | Backoffice editorial/normativo | `modules.governance`, `governance-backoffice.tsx` | `test_governance_backoffice.py`, component/E2E | PASS |
| PS-MOD-15 | Revisión y publicación | proposal state machine, immutable revisions, publication impact | `test_governance_backoffice.py`, `test_publication_impact.py`, ADR-0021 | PASS |
| PS-MOD-16 | Notificaciones y alertas | `modules.notifications`, outbox/dispatcher, `notification-center.tsx` | `test_notifications.py`, `notification-center.test.tsx`, E2E notifications | PASS |
| PS-MOD-17 | Analítica estudiantil | `modules.analytics.application.student_analytics` and frontend dashboard | `test_analytics.py`, `analytics-dashboard.test.tsx`, E2E analytics | PASS |
| PS-MOD-18 | Analítica institucional | privacy-thresholded aggregates/export in `modules.analytics` | `test_analytics.py` (role, threshold, no PII), API contract | PASS |
| PS-MOD-19 | Autenticación, autorización y auditoría | `modules.identity`, secure sessions, RBAC, append-only `AuditEvent` | `test_identity_security.py`, `test_security_hardening.py`, `test_student_history.py` | PASS |
| PS-MOD-20 | Observabilidad | `modules.observability` logs, metrics, tracing, health endpoints | `test_observability.py`, `test_health.py`, `docs/ops/*` | PASS |
| PS-MOD-21 | Backups y DR | `scripts/backup_postgres.py`, `restore_drill.py`, production Compose/runbooks | static deployment checks; CI restore job; local live drill BLOCKED by Docker sandbox | BLOCKED_EXTERNAL |
| PS-MOD-22 | CI/CD y dependencias | `.github/workflows/production-gates.yml`, `release-images.yml`, lockfiles | workflow inspection, `verify_deployment.py`, dependency audit recorded | PASS / CI runtime pending |
| PS-MOD-23 | Documentación pública e interna | `docs/`, ADRs, ops/security runbooks, generated OpenAPI | `scripts/check_openapi.py`, generated-client check, docs clone-clean procedure | PASS |
| PS-MOD-24 | Multi-programa, multi-sede, multiinstitución | `modules.institutions.models` and foreign-key-scoped revisions/enrollments | `test_domain_foundation.py`, factories, `test_structure.py`, `test_analytics.py` | PASS |
| PS-MOD-25 | Localización/i18n preparada | `apps/web/lib/i18n/messages.ts`, locale-aware notification preferences | `observability.test.ts`, `notification-center.test.tsx`, TypeScript check recorded | PASS |

## Malla curricular

| ID | Requisito | Implementación/evidencia | Prueba | Estado |
| --- | --- | --- | --- | --- |
| PS-MAP-01 | Tarjeta muestra código, nombre y créditos | `CurriculumCourseCard`, map DTO | `curriculum-map.test.tsx`, E2E curriculum | PASS |
| PS-MAP-02 | Tarjeta muestra componente, agrupación y obligatoriedad | map membership projection and card metadata | `test_curriculum_map.py`, component test | PASS |
| PS-MAP-03 | Estado personal y elegibilidad | `personal_status`, `eligibility`, overview/read model | `test_curriculum_map.py`, `test_academic_overview.py` | PASS / NO_HISTORY explicit |
| PS-MAP-04 | Oferta del período y bloqueo explicable | offering summaries + requirement explanations | `test_curriculum_map.py`, `test_offerings.py`, E2E detail | PASS |
| PS-MAP-05 | Número de desbloqueos y aporte de progreso | graph/map projection fields and audit progress | `test_dependency_graph.py`, `test_curriculum_map.py` | PASS |
| PS-MAP-06 | Evidencia normativa navegable | evidence snapshot/hash/locator payloads and source links | `test_curriculum_ingestion.py`, `test_academic_overview.py`, governance tests | PASS |
| PS-MAP-07 | Hover/focus contextual y ficha de detalle | accessible course cards + `CourseDetailPanel` | component and accessibility E2E | PASS |
| PS-MAP-08 | Ancestros, descendientes y rutas mínimas | graph focus projection and textual alternative | graph tests, E2E focus/path | PASS |
| PS-MAP-09 | Filtros y vistas suggested/depth/custom | map URL state and filter controls | `curriculum-map.test.tsx`, E2E filters | PASS |
| PS-MAP-10 | Exportar/imprimir y compartir sin historia privada | print route; URL state carries curriculum filters only | E2E print link and `url-state.test.ts` | PASS |

## Auditoría de grado

| ID | Requisito | Implementación | Prueba | Estado |
| --- | --- | --- | --- | --- |
| PS-AUD-01 | Créditos aprobados | audit credit ledger | `test_degree_audit.py`, `test_degree_audit_service.py` | PASS |
| PS-AUD-02 | Créditos aplicados | deterministic bucket assignment ledger | `test_degree_audit.py` (no double count) | PASS |
| PS-AUD-03 | Exceso/no aplicado | ledger diagnostics and applied/unapplied payload | `test_degree_audit.py` | PASS |
| PS-AUD-04 | Progreso por componente/agrupación | overview read model | `test_academic_overview.py`, academic dashboard test | PASS |
| PS-AUD-05 | Obligatorias faltantes y optativas | requirement status projection | `test_degree_audit.py`, `test_academic_overview.py` | PASS |
| PS-AUD-06 | Requisitos no crediticios | external requirement status and evidence | `test_academic_overview.py` | PASS / UNKNOWN by design |
| PS-AUD-07 | Inconsistencias | validation diagnostics and audit issues | `test_degree_audit.py`, service tests | PASS |
| PS-AUD-08 | UNKNOWN explícito | epistemic statuses and explanation objects | `test_rule_engine.py`, `test_degree_audit.py`, `test_academic_overview.py` | PASS |
| PS-AUD-09 | Próximos desbloqueos | map/audit unlock projection | `test_academic_overview.py`, `test_dependency_graph.py` | PASS |
| PS-AUD-10 | Explicación verificable | rule trace, evidence locator and snapshot hash | golden/property/contract tests | PASS |

## Planificador y optimización

| ID | Requisito | Implementación | Prueba | Estado |
| --- | --- | --- | --- | --- |
| PS-PLAN-01 | Múltiples escenarios | scenario model, duplicate/update/delete ownership guards | `test_planning.py`, planner component/E2E | PASS |
| PS-PLAN-02 | Drag/drop y alternativa de teclado | dnd-kit board plus `Mover a` selector | `planner-board.test.tsx`, accessibility E2E | PASS |
| PS-PLAN-03 | Períodos futuros y límites de créditos | term/course validators | `test_planning.py`, `test_optimization.py` | PASS |
| PS-PLAN-04 | Conflictos de horario | pure schedule overlap evaluator | `test_offerings.py`, `test_planning.py`, E2E | PASS |
| PS-PLAN-05 | Preferencias de día/modalidad/carga | scenario preferences DTO and validation | `test_planning.py`, API contract | PASS |
| PS-PLAN-06 | Curso/fecha objetivo | planner objective fields and comparison view | `test_planning.py`, E2E planner | PASS |
| PS-PLAN-07 | Incertidumbre de oferta | offering confidence/status and optimizer diagnostics | `test_offerings.py`, `test_optimization.py` | PASS / UNKNOWN explicit |
| PS-OPT-01 | Minimizar períodos | CP-SAT objective | `test_optimization.py` | PASS |
| PS-OPT-02 | Minimizar bloqueos y maximizar desbloqueos | solver objective/diagnostic terms | `test_optimization.py`, `test_performance.py` | PASS |
| PS-OPT-03 | Equilibrar créditos y huecos | solver workload/schedule constraints | `test_optimization.py` | PASS |
| PS-OPT-04 | Preferir cursos requeridos y oferta frecuente | candidate scoring/constraints | `test_optimization.py` | PASS |
| PS-OPT-05 | Explicar soluciones | optimization result explanations and constraints | `test_optimization_api.py`, E2E optimizer | PASS |
| PS-OPT-06 | `OPTIMAL` | CP-SAT status mapping | `test_optimization.py` | PASS |
| PS-OPT-07 | `FEASIBLE` | incumbent mapping and explanation | `test_optimization.py` | PASS |
| PS-OPT-08 | `INFEASIBLE` y `UNKNOWN/TIME_LIMIT` | explicit termination/status/diagnostics and capacity gate | `test_optimization.py`, `test_performance.py` | PASS |

## Gobernanza, límites y éxito

| ID | Requisito | Implementación/evidencia | Prueba | Estado |
| --- | --- | --- | --- | --- |
| PS-GOV-01 | Flujo `DISCOVERED → SNAPSHOT → EXTRACTED → DRAFT → VALIDATED → IN_REVIEW → APPROVED → PUBLISHED` | governance proposal state machine and immutable revision model | governance/publication tests + E2E | PASS |
| PS-GOV-02 | LLM no publica ni verifica por sí solo | candidate queue, evidence gate, human confirmation, second role | `test_governance_backoffice.py`, `test_publication_impact.py`, ADR-0020/0021 | PASS |
| PS-GOV-03 | Evidencia y hash por regla | evidence snapshots, locators, SHA-256 | ingestion/security/governance tests | PASS; academic source snapshot pending |
| PS-OUT-01 | No se construye SIA, matrícula oficial ni certificados oficiales | no production route/model claims authority; integration boundary documented | scope review and API route inventory | PASS |
| PS-OUT-02 | Puntos de integración futuros sin simular autorización | bounded contexts and external requirement status | architecture docs and API contract | PASS |
| PS-SUCCESS-01 | El usuario responde dónde está, qué falta, qué puede cursar, qué abre un curso, oferta, plan y por qué | dashboard → map → audit → graph → offerings → planner → optimizer flow | `smoke.spec.ts` full critical journey 50/50 recorded; runtime rerun pending | PASS / runtime rerun pending |

## Criterios transversales y gaps

- El snapshot normativo oficial archivado del plan 2514 no está presente en el
  repositorio; por constitución del proyecto, cualquier regla que no pueda
  probarse contra esa fuente permanece `UNKNOWN` o
  `INFERRED_PENDING_REVIEW`. La matriz no convierte fixtures en evidencia
  normativa.
- Los archivos globales `docs/SPEC.md`, `docs/REQUIREMENTS.md` y
  `docs/ACCEPTANCE.md` no existen. La auditoría utiliza sus equivalentes
  disponibles: `docs/00_PRODUCT_SCOPE.md`, `docs/34_NON_FUNCTIONAL_REQUIREMENTS.md`,
  `docs/41_ACCEPTANCE_GATES_MATRIX.md`, `docs/acceptance/DOMAIN_ACCEPTANCE.md`
  y los documentos por bounded context.
- Los reviewers especializados exigidos por los prompts no están expuestos en
  esta sesión. Se ejecutó revisión manual read-only de arquitectura, código,
  currículo, seguridad y UX y se registró la limitación en el estado; no se
  inventó un sign-off de subagente.
- El restore drill contra PostgreSQL, el build/scan local de imágenes y el
  smoke del Compose requieren acceso a Docker Engine. El sandbox administrado
  deniega `docker.exe` y `docker_engine`; la CI tiene jobs reproducibles para
  esos gates, pero esta evidencia local queda `BLOCKED_EXTERNAL` hasta poder
  ejecutar el runtime.

## Comandos de reproducción

```powershell
python scripts/verify.py
python scripts/scan_secrets.py
python scripts/sast.py
python scripts/verify_deployment.py
pnpm test
pnpm lint
pnpm typecheck
pnpm build
pnpm e2e
```

Los resultados concretos de cada ejecución se conservan en `.codex/STATUS.md`
y `docs/state/SESSION_LOG.md`; ningún gate no ejecutado se presenta como
verde.
