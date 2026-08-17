# Auditoría final del proyecto — 2026-08-17

## Veredicto

**Estado: `NOT_READY` / Goal abierto.**

La implementación cubre el alcance funcional y los controles estáticos
identificados en la documentación, pero no es verificable declarar el sistema
listo para producción desde esta estación. Persisten gates `BLOCKED_EXTERNAL`
que pueden resolverse en el repositorio y en un runner autorizado: Python
3.14/Django/uv, Node/pnpm y `node_modules`, Docker/PostgreSQL, acceso al
registry/red, revisión normativa humana y pruebas manuales de accesibilidad.

No se convirtió ninguno de esos bloqueos en `PASS` por inspección, no se
publicó una regla curricular inferida, no se mutó una revisión `PUBLISHED`, y
no se degradaron aserciones para hacer pasar una prueba.

## Documentos de autoridad revisados

La revisión se hizo contra los índices canónicos y sus documentos enlazados:

- `docs/SPEC.md`: alcance, dominio, contratos, seguridad, operación,
  accesibilidad, analítica, backoffice, eventos y arquitectura.
- `docs/REQUIREMENTS.md`: requisitos funcionales, no funcionales, operación,
  procedencia y matriz de trazabilidad.
- `docs/ACCEPTANCE.md`: gates, orden reproducible, requisitos de evidencia y
  criterio `READY`.
- `docs/00_PRODUCT_SCOPE.md`, `docs/33_FULL_FEATURE_CATALOG.md` y
  `docs/34_NON_FUNCTIONAL_REQUIREMENTS.md`.
- `docs/41_ACCEPTANCE_GATES_MATRIX.md`,
  `docs/acceptance/DOMAIN_ACCEPTANCE.md` y
  `docs/acceptance/PRODUCTION_GATES.md`.
- `docs/audit/P25_TRACEABILITY_MATRIX.md`,
  `docs/audit/P25_SYSTEM_AUDIT.md` y
  `docs/audit/ANTI_MVP_AUDIT_2026-08-17.md`.

## Matriz final de gates

| Área | Evidencia | Estado actual | Cierre requerido |
|---|---|---|---|
| Alcance y bounded contexts | Gate anti-MVP: 200 archivos, 14 contextos, 0 señales | `PASS_STATIC` | Rerun dinámico completo |
| Dominio y reglas | Invariantes locales: `courses=102`, `memberships=97`, `requirements=73`; golden/property tests históricos | `PASS_HISTORICAL` / `BLOCKED_CURRENT` | Ejecutar suite Django/Python 3.14 y confirmar golden cases actuales |
| Currículo/procedencia | Baseline 2514-AC496-2023, snapshot P90, estados epistemológicos y no-publicación | `UNKNOWN_REVIEW_REQUIRED` | Archivar evidencia normativa íntegra y revisión curricular humana; resolver B1 sin inferir |
| Auditoría de grado | Backend histórico 131 passed/1 skip y trazabilidad documentada | `PASS_HISTORICAL` / `BLOCKED_CURRENT` | Rerun con DB real y verificar no doble conteo/explicaciones |
| API/OpenAPI | Breaking diff PASS; artefacto OpenAPI actualizado | `PASS_STATIC` / cliente bloqueado | Ejecutar freshness/generación con `openapi-typescript` instalado y verificar contract tests |
| Frontend unit/type/lint/build | Vitest histórico 33/33, lint/typecheck/build históricos PASS | `BLOCKED_EXTERNAL` | Reparar `node_modules`/pnpm y repetir todos los comandos |
| E2E y responsive | Playwright histórico 50/50 desktop/mobile | `PASS_HISTORICAL` / `BLOCKED_CURRENT` | Rerun post-cambios con browser y fixture/API actuales |
| Accesibilidad automatizada | axe histórico 20/20 sin violaciones; bundle audit correcto: 19 chunks/2446.3 KiB | `PASS_HISTORICAL` / manual pendiente | Lector NVDA/VoiceOver, teclado, zoom y dispositivo físico |
| Importaciones | Validación, idempotencia, quarantine y hardening documentados; tests históricos | `PASS_HISTORICAL` / `BLOCKED_CURRENT` | Rerun parser/history/storage con Python 3.14 y archivos de prueba |
| Optimización/planning/offering | Servicios, contratos y tests implementados en P01–P21 | `PASS_HISTORICAL` / `BLOCKED_CURRENT` | Ejecutar tests CP-SAT, planner, offerings y conflictos con DB real |
| Seguridad | Secret scan PASS; `pip-audit`/`pnpm audit` históricos PASS; hardening P23 documentado | `PARTIAL` | SAST bajo Python 3.14, container scan e integración de seguridad |
| Base de datos/migraciones | Invariantes y scripts estáticos PASS | `BLOCKED_EXTERNAL` | Ejecutar `manage.py check`, migration graph/state, migraciones y restore PostgreSQL |
| Deploy | Dockerfiles/Compose/digests/healthchecks/no-root verificados estáticamente | `PASS_STATIC` / `BLOCKED_EXTERNAL` | Build, scan, startup, readiness y smoke reales |
| Backup/DR | Scripts y runbooks P24/P95 presentes | `BLOCKED_EXTERNAL` | Backup, restore drill, checksum, RPO/RTO y rollback ejecutados |
| Observabilidad/notificaciones | Boundaries, métricas, traces, outbox y workflows implementados | `PASS_HISTORICAL` / `BLOCKED_CURRENT` | Rerun de tests y verificación con servicios levantados |
| Multi-programa | Test sintético de aislamiento/AST y documento de prueba; `py_compile` PASS | `BLOCKED_EXTERNAL` | Ejecutar Django/PostgreSQL; no inventar un segundo programa oficial |
| Mantenimiento/source watch | Offline PASS con 4 `UNKNOWN`; remoto `ERROR` por red | `BLOCKED_EXTERNAL` | Ejecutar remote watcher y comandos Django en runner autorizado |
| CI/CD/dependencias | Workflows, Renovate y baseline presentes; versión Next requiere resolver registry | `PARTIAL` | Resolver lockfile oficial, gates de CI y revisión de advisory |
| Runbooks/incidentes | Runbook P95 y documentos de operación presentes | `PASS_DOCUMENTAL` | Game day y restore drill |

## Resultado de comandos finales

Pasaron en esta sesión:

- `python scripts/verify_deployment.py`.
- `python scripts/verify_state_recovery.py` — 27 fases `done`, 8 `in_progress`,
  sin errores estructurales.
- `python scripts/anti_mvp_audit.py` — 200 archivos, 14 contextos, 0 issues.
- `python scripts/verify_docs_clone_clean.py`.
- `python scripts/update_technology_baseline.py --check`.
- `python scripts/source_freshness.py --offline` — cuatro `UNKNOWN` explícitos.
- `python scripts/scan_secrets.py`.
- `git diff --check` — sin errores de whitespace; sólo advertencias de
  conversión de fin de línea de Git en Windows.
- `node scripts/audit-bundle.mjs` desde `apps/web`.
- `scripts/check_no_todos.py`: PASS después de corregir su alcance de recorrido;
  `files_scanned=525`, `functional_hits=0`, `TODO_RELEASE_GATE=PASS`; las
  referencias no funcionales quedan clasificadas y no bloquean el gate.

Se ejecutaron y terminaron con bloqueo/fallo reproducible:

- `python scripts/sast.py`: el Python bundled es 3.12 y no puede parsear seis
  archivos válidos para el requisito Python 3.14; esto requiere rerun con el
  intérprete correcto.
- `python scripts/verify.py`: llega a todos los gates y termina `FAIL` porque
  conserva esos bloqueos; además `uv` no puede iniciarse, el cliente generado
  no puede abrir `openapi-typescript`, y pnpm no puede abrir binarios bajo
  `node_modules` por `EPERM`.
- `pnpm --dir apps/web lint`, `typecheck`, `test -- --run`, `build` y `e2e`:
  bloqueados por `EPERM` en ESLint, TypeScript, Vitest, Next y Playwright.
- `pnpm --dir packages/api-client verify`: bloqueado porque falta el paquete
  accesible `openapi-typescript` en su instalación local.
- Inicio standalone: `Cannot find module 'next'`.
- API `uv run --frozen python manage.py check`: el runtime/UV no puede
  inicializar su cache/venv en esta estación.
- Recuperación de runtime: `uv --cache-dir .uv-cache python install 3.14
  --install-dir .uv-python` falló con `WinError 10013` al descargar desde
  GitHub/releases.astral.sh; no se instaló Python alternativo.
- Instalación pnpm aislada offline: bloqueada por ausencia de metadata local
  de `@testing-library/react`; no se modificaron manifests ni lockfiles.
- Docker `version` y `compose config`: el ejecutable no está disponible en
  PATH y el binario absoluto probado está bloqueado por ACL.

## Correcciones aplicadas durante la auditoría

- Se añadieron los tres índices canónicos que faltaban al comienzo de la
  revisión sin duplicar reglas académicas.
- Se hizo que `scripts/verify.py` informe `BLOCKED` cuando no puede ejecutar
  `uv`, en lugar de terminar con una excepción opaca.
- Se corrigió `db_maintenance._analyze()` para cambiar a autocommit antes de
  abrir el cursor de PostgreSQL para `VACUUM (ANALYZE)` y restaurar el modo
  anterior siempre.
- Se actualizaron `CURRENT_STATE.md`, `SESSION_LOG.md`, `RISKS.md`,
  `OPEN_DECISIONS.md` y `ROADMAP_STATUS.json` con evidencia, bloqueos y
  comandos exactos de reanudación.
- Se corrigió `scripts/check_no_todos.py` para podar stores/caches de
  dependencias, reportar errores de lectura y clasificar explícitamente hits
  funcionales frente a documentación/metadatos; se integró al verificador
  canónico y terminó en PASS.

## Decisión final

El repositorio queda en un estado de implementación avanzada, auditable y
honesto, pero **no se declara conforme ni terminado**. El criterio de
`docs/ACCEPTANCE.md` prohíbe `READY` mientras existan `UNKNOWN` publicables o
`BLOCKED_EXTERNAL` sin evidencia reproducible. La siguiente sesión debe cerrar
los gates operativos enumerados y volver a ejecutar la matriz completa; sólo
entonces puede evaluarse `update_goal(status="complete")`.

## Correcciones posteriores a la auditoría especializada — 2026-08-17 11:56

Se resolvieron dentro del repositorio los hallazgos que no requerían un
servicio externo:

- La inmutabilidad de una revisión publicada ahora cubre grupos, memberships,
  requisitos y enlaces de evidencia, tanto en modelo/señal como en triggers
  PostgreSQL; también se añadieron triggers de aislamiento entre institución,
  sede, programa, plan, curso, término, matrícula y course attempt.
- La autorización editorial aplica scope por institución/programa en inbox,
  documentos, snapshots y propuestas; `RoleAssignment` no se puede editar
  desde Django admin; la barrera MFA privilegiada falla cerrada y se propaga
  explícitamente en Compose de producción.
- Backup/restore eliminan contraseñas de `argv`, hacen fallar cleanup no
  confirmado y validan tablas críticas; los workflows usan SHA completos y el
  nuevo `check_action_pins.py` está integrado al verificador canónico.
- SSRF rechaza también rangos no globales; la UI corrigió foco de
  notificaciones, alternativa textual de condiciones y live-region ruidoso.

La clasificación no cambia: **`NOT_READY`**. Estas reparaciones todavía
requieren ejecutar en un runner compatible Django/3.14, PostgreSQL, Node/pnpm,
Docker/Compose y navegador; la suite histórica no sustituye ese rerun. La
auditoría curricular remota sigue sin bytes normativos íntegros y por tanto no
se publicó ninguna inferencia.
