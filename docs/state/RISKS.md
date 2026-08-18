# Riesgos vivos

| Riesgo | Severidad | Mitigación |
|---|---|---|
| Interpretar una celda ambigua como requisito oficial | Critical | estado UNKNOWN + revisión humana |
| Mezclar malla sugerida con norma | High | `CurriculumLayout` separado |
| Doble conteo de créditos | High | CreditAllocation explícito + property tests |
| LLM publica cambios incorrectos | Critical | workflow sin auto-publish |
| Dependencias framework cambian | Medium | version policy + official docs |
| Oferta académica desactualizada | High | source timestamp + freshness |
| Historia PDF extraída mal | High | preview/confirmation/idempotencia |
| Sobrearquitectura | Medium | monolito modular, ADR gates |
| Regla duplicada en frontend | High | backend authority + contract tests |

## Riesgos operativos añadidos — 2026-08-17

| Riesgo | Severidad | Mitigación / evidencia |
|---|---|---|
| Docker CLI/socket no accesible en la estación de ejecución | Critical para release | P24 documenta el bloqueo; repetir build, scan, backup, restore y smoke en runner autorizado; no marcar P24 `done` antes del resultado |
| Python 3.14/venv/uv inaccesibles y runtime bundled sin Django | Critical para gates backend | Ejecutar `scripts/verify.py`, migraciones y tests en runner Python 3.14 real; no confundir `py_compile` 3.12 con validación Django |
| Archivos existentes de `node_modules` bloqueados con `EPERM` | High para release frontend | Reparar instalación/ACL o reinstalar con pnpm en runner autorizado; repetir lint, typecheck, Vitest, build, E2E y axe |
| Registry npm/red no disponible | High para mantenimiento | Resolver versión Next y lockfile con acceso al registry; no editar lockfile a mano ni aplicar downgrade ciego |
| Source watch remoto no puede confirmar fuentes | High para procedencia | Mantener `UNKNOWN`/`ERROR`, archivar snapshots oficiales y ejecutar watcher en red autorizada; nunca autopublicar |
| Fuentes normativas remotas sin archivo íntegro | Critical para publicación curricular | Revisión humana y archivo/evidencia verificable; no mutar `PUBLISHED` ni convertir observaciones en reglas |
| Reviewers especializados, screen reader y dispositivo físico no expuestos | Medium/High para sign-off | Completar revisión independiente y checklist manual antes de release; conservar auditoría manual como evidencia parcial |
| Estado `.codex/STATUS.md` no editable por ACL de la sesión | Medium para continuidad | Usar `docs/state/CURRENT_STATE.md`, `SESSION_LOG.md`, `ROADMAP_STATUS.json` e informes auditables; actualizar `.codex/STATUS.md` en una sesión con permiso |

## Riesgos revisados — 2026-08-17 11:56

| Riesgo | Severidad | Mitigación / evidencia |
|---|---|---|
| Mutación masiva de filas hijas después de publicar una revisión | High | Guards de modelo, signal M2M y triggers PostgreSQL en curriculum/rules; falta ejecutar migraciones y pruebas en PostgreSQL real |
| Cruce de institución/programa por `QuerySet.update()` o import masivo | High | Triggers de scope en curriculum/offerings/student_records y `full_clean()` en rutas normales; falta ejecutar migration graph y pruebas de DB |
| Credencial de PostgreSQL visible en argumentos de procesos contenedorizados | High | Backup/restore usan env files temporales 0600 y tests/helpers aseguran que el password no aparece en `argv` |
| Cleanup de restore no confirmado | High | `_drop_drill_database()` convierte fallo de DROP en `RestoreError`; restore drill real sigue bloqueado sin Docker/PostgreSQL |
| Acción de CI mutable por tag | Medium | Todos los `uses:` del workflow están pinneados a SHA completo; `scripts/check_action_pins.py` integrado al verify |
| Verificación completa de cambios nueva | Critical para cierre | SAST, Django, suite, migraciones, lint/typecheck/build/E2E y Compose siguen sin ejecutarse por restricciones del runner; no se declara READY |

## Riesgos revisados — 2026-08-17 13:08

Los bloqueos locales de Python/Node descritos arriba quedaron superados en esta
continuación: el verificador canónico, Django, migraciones, Ruff, mypy, ESLint,
TypeScript y las suites backend/frontend pasan. Docker/Compose y el restore
drill continúan pendientes y por ello P24/P25 permanecen `in_progress`.

| Riesgo | Severidad | Mitigación / evidencia |
|---|---|---|
| PDF malicioso agota CPU/memoria durante importación síncrona | Medium | 10 MiB/200 páginas y validación de tipo ya existen; mover parsing a proceso/job con timeout y memoria acotada |
| Columnas arbitrarias/PII persisten en `raw_payload` y vuelven por API | Medium | Implementar allowlist/redacción, clasificación y política de retención; mantener APIs privadas `no-store` |
| Historia paginada por offset cambia durante inserciones concurrentes | Medium | Sustituir recuperación completa por cursor estable o snapshot/ETag |
| Latencia alta y timeout en estrés contra servidores de desarrollo | Medium para experiencia / High para release | Repetir carga contra build production-like con PostgreSQL, métricas y presupuesto p95; no extrapolar el resultado dev |
| Importación muestra enums/JSON técnico y el error de batch puede ser poco accionable | Medium | Localizar etiquetas, resumir por fila/campo, conservar JSON en disclosure y mostrar correlation id/reintento |
| Confirmación o anulación mediante estado obsoleto | Mitigado | `If-Match` en confirmación, locks batch→candidate y `ANNULLED` rechazado por create/update genéricos; pruebas focalizadas y verify PASS |

## Riesgos revisados — 2026-08-17 17:30

| Riesgo | Estado | Mitigación / evidencia |
|---|---|---|
| PDF malicioso agota CPU/memoria | Mitigado en aplicación | Proceso hijo, timeout, memoria acotada y fallo cerrado; queda verificar límites del contenedor en Compose |
| PII arbitraria en `raw_payload` | Mitigado | Allowlist, longitudes acotadas, purga inmediata al aplicar y expiración operable de previews |
| Historia cambia durante paginación | Mitigado | Cursor firmado con snapshot y keyset estable; frontend sigue `next_cursor` |
| Períodos de otra institución aparecen en planificación | Mitigado | Endpoint autorizado por matrícula y scope institución/campus; filtros incompatibles fallan cerrados |
| Trigger PostgreSQL compartido accede a columnas inexistentes | Mitigado | Migración `offerings.0004` separa funciones por tabla; prueba PostgreSQL de importación pasa |
