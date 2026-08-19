# P100 — Inventario de supuestos Estadística / 2514

## Alcance reproducible

```bash
rg -n 'Estadística|Estadistico|2514|141 créditos|plan_2514' \
  apps/api apps/web packages scripts data/layouts
```

## Clasificación

La búsqueda devuelve **87 hits en 27 archivos**. Todos se clasifican abajo; los
dos hits de `uv.lock` son coincidencias accidentales dentro de hashes/URLs y no
son supuestos de producto.

| Ubicación (hits) | Clase | Disposición | Fase |
|---|---|---|---|
| `apps/api/modules/curriculum/api.py` (2) | defaults públicos `plan_code="2514"` | hacer obligatorio el contexto o resolverlo desde matrícula/selector; nunca elegir 2514 implícitamente | P102/P104 |
| `apps/api/modules/curriculum/application/map.py` (1) | default de producción 2514 | retirar default; consumir revisión/layout resueltos | P103/P104 |
| `apps/api/modules/curriculum/application/graph.py` (1) | default de producción 2514 | retirar default; consumir revisión resuelta | P102/P106 |
| `apps/api/modules/imports/application/services.py` (6) | ruta y fallbacks de importación 2514/Estadística | separar adaptador explícito por manifiesto; ningún fallback silencioso | P106 |
| `apps/api/modules/identity/management/commands/bootstrap_local_admin.py` (1) | bootstrap condicionado a 2514 | resolver cualquier revisión publicada o aceptar parámetro explícito | P102/P106 |
| `apps/web/app/page.tsx` (3) | copy/default de producción | derivar programa/plan del read model y convertir `/` en `Mi malla` | P104 |
| `apps/web/components/curriculum-map.tsx` (1) | copy de producción `Estadística` | usar `map.revision.program_name` | P104 |
| `data/layouts/plan_2514_layout_policy.json` (1) | layout legacy específico | migrar a `CurriculumLayout`; conservar sólo como entrada de migración trazada | P103 |
| `scripts/benchmark_performance.py` (5) | benchmark operativo fijado a 2514 | parametrizar plan/revisión y añadir caso de plan grande/segundo programa | P106/P108 |
| `scripts/benchmark_rules.py` (1) | golden de rendimiento | mantener 2514 como caso explícito y parametrizar catálogo de golden cases | P106 |
| `scripts/validate_curriculum.py` (1) | verificador fijado al baseline 2514 | aceptar manifiesto/ruta y ejecutar todos los currículos de la campaña | P106/P107 |
| `apps/api/tests/test_rule_engine.py` (3) | golden 2514 | permitido como golden nombrado; añadir golden alterno | P106 |
| `apps/api/tests/test_curriculum_ingestion.py` (3) | ingestión real 2514 | permitido; añadir manifiesto/segundo programa | P106 |
| `apps/api/tests/test_dependency_graph_api.py` (2) | fixture 2514 | permitido; añadir contexto alterno y test sin default | P106 |
| `apps/api/tests/test_degree_audit.py` (2) | golden 2514 | permitido; añadir segundo currículo | P106 |
| `apps/api/tests/test_curriculum_map.py` (2) | fixture 2514 | permitido; probar selector requerido y segundo programa | P103/P106 |
| `apps/api/tests/test_identity_security.py` (1) | aserción de fixture local | reemplazar por revisión publicada creada por factory, sin código especial | P102 |
| `apps/api/tests/factories.py` (1) | factory con código 2514 | generar códigos neutrales por defecto; conservar factory golden separada | P101/P106 |
| `apps/api/tests/test_observability.py` (2) | ID sintético que contiene 2514 | renombrar para evitar falso positivo del gate | P100 cleanup |
| `apps/api/uv.lock` (2) | coincidencia accidental en hashes/URLs | permitido; excluir lockfiles del gate semántico sin modificar lock | permanente |
| `apps/web/tests/student-administration-workspace.test.tsx` (5) | fixture 2514 | permitido; añadir alta de otro programa y asignación automática | P102/P106 |
| `apps/web/tests/governance-backoffice.test.tsx` (3) | fixture 2514 | permitido; añadir programa alterno | P106 |
| `apps/web/tests/analytics-dashboard.test.tsx` (1) | fixture 2514 | permitido; parametrizar programa | P106 |
| `apps/web/tests/api.test.ts` (2) | solicitud/fixture 2514 | añadir caso sin default y contexto alterno | P102/P106 |
| `apps/web/tests/e2e/fixture-server.mjs` (12) | servidor fixture 2514 | conservar persona Estadística y añadir catálogo/estudiante alterno | P106 |
| `apps/web/tests/e2e/fixtures/student-academic-overview.json` (9) | fixture 2514 | permitido; añadir overview alterno | P106 |
| `apps/web/tests/e2e/fixtures/curriculum-map.json` (6), `dependency-graph.json` (6), `scenarios.json` (2) | fixtures 2514 | permitidos; añadir equivalentes del segundo programa | P106 |

Fuera de esos 87 hits, `data/curricula/unal/bogota/estadistica/2514/**` es una
fuente curricular real y permitida como dato versionado; no es un default de
producto.

## Gate

El comando debe seguir devolviendo 87 hits hasta que las fases indicadas los
reduzcan. Después de P106, cualquier hit en código de producción debe ser un
adaptador de ingestión explícito o una etiqueta derivada de datos. Los hits
permitidos en fuentes, tests, lockfiles y documentación histórica quedan
clasificados por este inventario; cualquier archivo nuevo bloquea el gate hasta
ser añadido con owner, disposición y fase.
