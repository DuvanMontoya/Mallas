# ANTI-MVP COMPLETENESS AUDIT

Tu misión es encontrar todo lo que haya sido reducido, simulado, aplazado o declarado «suficiente» sin cumplir `docs/00_PRODUCT_SCOPE.md`.

No implementes primero. Audita.

## 1. Construye matriz de trazabilidad

Para cada capacidad del PRODUCT_SCOPE:
- status: COMPLETE / PARTIAL / MISSING / BLOCKED_EXTERNAL;
- rutas de código;
- endpoints;
- pantallas;
- tests;
- docs;
- evidencia de funcionamiento.

`PARTIAL` no cuenta como terminado.

## 2. Busca señales de MVP oculto

Busca en repo:
- TODO/FIXME/HACK;
- `pass`;
- NotImplemented;
- hardcoded plan/course conditions;
- mock data fuera de tests;
- fake API;
- disabled tests;
- `skip`;
- xfail;
- botones sin acción;
- rutas placeholder;
- comentarios «future/later/v2/MVP»;
- empty handlers;
- optimistic UI sin persistencia;
- auth bypass;
- `any`/type ignores injustificados;
- rules in frontend;
- missing mobile states;
- no evidence;
- no UNKNOWN.

## 3. Verifica módulos completos

Curriculum versioning, source governance, rules, audit, student history, malla, graph, offerings, schedules, planner, optimizer, backoffice, publication, impact, notifications, analytics, security, observability, accessibility, deployment, backup/restore.

## 4. Corrige

Crea worklist ordenado por severidad/dependencia. Implementa todos los gaps que no requieran una dependencia externa genuina.

Para `BLOCKED_EXTERNAL`, exige:
- interfaz completa;
- UX honesta;
- adapter;
- test;
- observabilidad;
- docs;
- no falsa afirmación.

## 5. Gate

No declares producto completo hasta que:
- no haya PARTIAL/MISSING;
- `python scripts/check_no_todos.py` esté clasificado/resuelto;
- `python scripts/verify.py` pase;
- reviewers no tengan High/Critical;
- E2E/restore/security/accessibility estén verdes.
