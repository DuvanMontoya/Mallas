# P93 — Revisión de bugs y regresiones

**Fecha:** 2026-08-17  
**Estado:** `NO_ACTIVE_REPRODUCIBLE_BUG`

## Resultado

No existe en el estado documentado ni en la inspección del checkout un bug
abierto, reproducible y atribuible al producto que pueda corregirse dentro de
este milestone. Por esa razón no se inventó una reproducción ni se hizo un
cambio de código sin una causa raíz. Las referencias a “bug”, `TODO`, `skip` o
“regression” encontradas pertenecen a documentación histórica, nombres de
datos/cursos, guards de verificación o skips explícitos por infraestructura de
PostgreSQL, no a un defecto funcional abierto.

## Protocolo aplicado

1. Leí el protocolo P93 y el estado del repositorio.
2. Busqué señales de bugs, regresiones, `TODO/FIXME/HACK`, `NotImplementedError`,
   xfail y skips fuera de caches/dependencias.
3. Revisé el resultado histórico de las suites focalizadas y globales de P22/P23:
   backend 131 passed + 1 skip PostgreSQL-only esperado, frontend 33 passed,
   E2E 50/50 desktop/mobile y axe 20/20.
4. Verifiqué que el único skip esperado está documentado y que no se usa para
   ocultar un fallo del dominio.
5. No se encontró una reproducción mínima que pudiera convertirse honestamente
   en un test rojo; por tanto, no hay causa raíz ni capa de reparación que
   seleccionar.

## Inventario de regresión disponible

La cobertura existente ya contiene regresiones para las áreas con mayor riesgo:

- exactitud de créditos, asignación sin doble conteo y porcentajes racionales;
- `UNKNOWN`, `ALL/ANY`, ciclos y equivalencia AST/serialización;
- inmutabilidad de revisiones publicadas, evidencia y publicación con concurrencia;
- autenticación, ownership/IDOR, rate limiting, SSRF, almacenamiento y audit log;
- API OpenAPI, ETags, paginación, idempotencia y errores correlacionables;
- mapa, grafo semántico/textual, foco contextual y filtros;
- oferta, frescura, capacidad no reportada, elegibilidad y conflictos de horario;
- planner privado, movimiento accesible, optimización y límites de jobs;
- governance diff/preview/publicación, notificaciones y recomputación;
- analytics con minimización, supresión y rutas pseudonimizadas;
- keyboard, axe, reduced motion, zoom, mobile y recorrido estudiante.

## Limitaciones de esta ejecución

La repetición actual de la suite no pudo completarse porque el Python 3.14 del
proyecto y los ejecutables externos están protegidos por el entorno administrado;
el Node/pnpm puede leer parte del build existente, pero falla con `EPERM` sobre
`node_modules`, y Docker no es accesible. Esto es una limitación de verificación,
no evidencia de ausencia de bugs. Los resultados históricos se conservan como
resultados históricos y no se etiquetan como una ejecución nueva.

El reviewer especializado `regression-debug` no está expuesto. Se realizó la
revisión manual equivalente y se deja la limitación explícita.

## Cierre P93

P93 no requiere reparación de código. Queda **sin bug activo conocido**, con la
repetición de la suite global pendiente hasta disponer de los runtimes y
permisos necesarios.
