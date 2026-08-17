# ADR-0019 — Ejecuciones CP-SAT reproducibles y explicables

**Estado:** ACCEPTED

## Contexto

El planificador necesita proponer una periodización sin convertir la interfaz
en una segunda autoridad académica. La solución debe respetar hechos conocidos,
señalar evidencia ausente y ser reproducible a partir de una revisión,
historia, escenario y oferta concretos. Una función con pesos mezclados no
permite demostrar qué prioridad ganó ni explicar una solución infeasible.

## Decisión

Se adopta OR-Tools CP-SAT sobre un modelo puro Python. La frontera Django
construye un `OptimizationInput` canónico y lo persiste como snapshot antes de
encolar el trabajo. El solver sólo recibe ese DTO y produce un
`OptimizationResult`; no importa modelos, sesiones ni servicios HTTP.

El modelo usa variables booleanas `x(course, term)` y variables `y(course,
term, group)` para cobertura y no doble conteo. Las restricciones duras cubren
selección única, cursos obligatorios, grupos y créditos, límites por período,
prerrequisitos, correquisitos, oferta, elecciones bloqueadas y conflictos de
horario de secciones. Un hecho desconocido no se rellena: `ALLOW_UNKNOWN` lo
conserva como supuesto penalizable y `REQUIRE_OFFERED` lo excluye. Reglas que
no tienen representación segura en el snapshot terminan en `UNKNOWN`.

La prioridad se implementa mediante pasadas lexicográficas independientes:

1. `last_term`;
2. `unknown_offerings`;
3. `credit_balance`;
4. `preference_penalty`.

Después de cada pasada se agrega una restricción que fija el valor óptimo y se
resuelve la siguiente. La satisfacción de restricciones duras es condición de
factibilidad, no un peso. Esto evita que un peso “grande” permita violar una
regla normativa para mejorar una preferencia.

Las ejecuciones se guardan en `OptimizationRun` con `input_snapshot`,
`input_hash`, `output_hash`, `solver_version`, objetivos, solución,
explicación, límite y marcas de inicio/cancelación/completitud. El trabajo se
desacopla mediante una interfaz de jobs; el ejecutor local actual es
intercambiable y el dominio no depende de Celery, RQ u otro proveedor.
`stop_search()` se invoca mediante callback al cancelar. Los estados
operativos son `QUEUED` y `RUNNING`; los resultados son `OPTIMAL`, `FEASIBLE`,
`INFEASIBLE` y `UNKNOWN`.

La UI sólo compara la solución con el escenario y enumera razones, conflictos
y supuestos. Aplicar una propuesta sigue siendo una mutación explícita del
planificador, con sus controles de concurrencia y auditoría; una ejecución no
crea ni modifica `CourseAttempt`.

## Consecuencias

- El mismo snapshot y semilla producen hashes y selección deterministas en el
  entorno soportado.
- Las soluciones limitadas en tiempo se distinguen de las óptimas y no se
  presentan como prueba de graduación.
- La explicación puede identificar elecciones bloqueadas, oferta desconocida,
  secciones conflictivas y restricciones inviables sin inventar una causa
  académica cuando CP-SAT sólo entrega inviabilidad global.
- La persistencia añade datos de ejecución, pero permite auditoría y
  reproducibilidad cuando cambian la base o la oferta posterior.

## Alternativas rechazadas

- Pesos combinados: dificultan la prueba de prioridad y son frágiles frente a
  cambios de escala.
- Solver dentro del frontend: permitiría falsificar elegibilidad y duplicaría
  reglas.
- Modificar automáticamente el escenario o los intentos: rompe la separación
  entre propuesta, plan y hechos académicos.
- Interpretar ausencia de oferta futura como `NOT_OFFERED`: contradice el
  contrato epistemológico del producto.
