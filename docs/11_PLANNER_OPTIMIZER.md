# 11 — Planificador y optimizador

## Escenario

Un escenario es independiente de la historia real. No altera auditoría oficial hasta que un curso se convierte en intento real.

La implementación persistente usa `PlanScenario` (ownership por
`ProgramEnrollment`, estado, versión y compartir explícito), `PlannedCourse`
(curso-versión por término, sección opcional, prioridad, origen, notas y
lock), `PlanningPreference` (límites, disponibilidad y preferencias), y
`ScenarioAuditProjection` (huellas, versión del motor, resultado, `UNKNOWN` y
payload proyectado). Duplicar, renombrar, archivar y comparar son operaciones
de aplicación; no se copian ni mutan intentos oficiales.

## Validación incremental

Al mover un curso a un término:
- evaluar prerrequisitos contra historia + términos anteriores;
- evaluar correquisitos contra mismo término;
- comprobar límite de créditos;
- oferta conocida;
- conflicto de sección si hay grupo;
- mostrar warnings, no perder el cambio silenciosamente.

La validación ejecutable está en `apps/api/domain/planning/validator.py` y no
depende del ORM. La API devuelve el estado por curso, las razones exactas y
warnings de prerrequisito, correquisito, oferta, créditos, días no disponibles
y horarios. Si falta evidencia se conserva `UNKNOWN`; la ausencia de una fila
de oferta no se interpreta como cancelación.

La pantalla `/planner` ofrece drag/drop mediante `@dnd-kit/core` y, para cada
tarjeta, un selector «Mover a» completamente operable con teclado, además de
botones para bloquear, desbloquear y retirar. La vista compartida se activa
por opt-in y sólo devuelve cursos, términos y una declaración de privacidad.

Las mutaciones usan OpenAPI, CSRF y `If-Match`; un conflicto de versión
devuelve `409 STALE_RESOURCE` para que el usuario recargue antes de sobrescribir
trabajo ajeno.

## Modelo CP-SAT

Variables de ejemplo:
`x[c,t] ∈ {0,1}` si curso c está planificado en t.

Restricciones:
- cada curso máximo una vez salvo repeat policy;
- prerequisite ordering;
- corequisite same/earlier;
- required group coverage;
- credit bounds;
- term offering;
- schedule conflicts;
- target completion;
- locked choices del usuario.

Objetivos lexicográficos:
1. satisfacer todos los requisitos;
2. minimizar último término;
3. minimizar cursos de oferta incierta/infrecuente;
4. balancear créditos;
5. preferencias.

No mezclar objetivos con pesos mágicos sin documentar escala.

La implementación actual está en `apps/api/domain/optimization/` y recibe un
`OptimizationInput` serializable, independiente de Django. El adaptador de
aplicación construye ese snapshot a partir de la revisión publicada, la
historia académica, el escenario, la oferta disponible y las secciones
seleccionadas; el solver nunca consulta el ORM durante la evaluación.

El modelo usa `x[curso, período]` para la selección temporal y variables de
asignación `y[curso, período, grupo]` para evitar doble conteo. Las
restricciones duras implementadas son: obligatoriedad, cobertura de créditos
por grupo, una sola aparición por curso, créditos objetivo, mínimos/máximos
por período, prerrequisitos `ALL`/`ANY`/`NOT` y reglas de cursos aprobados o en
curso, correquisitos en el mismo período o anteriores, oferta conocida,
elecciones bloqueadas y conflictos de horario de secciones. Las reglas de
grado externas, nota mínima, componente porcentual u otra evidencia que el
snapshot no pueda representar producen `UNKNOWN`, nunca una elegibilidad
inventada.

El primer nivel —satisfacer las restricciones duras— no se codifica con un
peso: una solución que las viola no es factible. Después se resuelven cuatro
objetivos en pasadas CP-SAT separadas y se fija el óptimo de cada pasada antes
de continuar: `last_term`, `unknown_offerings`, `credit_balance` y
`preference_penalty`. Así la prioridad es lexicográfica y auditable, sin
dependencia de escalas arbitrarias. `ALLOW_UNKNOWN` conserva una suposición
explícita y la penaliza en el segundo nivel; `REQUIRE_OFFERED` descarta la
oferta desconocida.

Las ejecuciones persistidas son `OptimizationRun`: guardan el snapshot de
entrada, `input_hash`, versión del solver, `output_hash`, objetivos, solución,
explicación, límite temporal y marcas de inicio/cancelación/completitud. La
interfaz de jobs actual es un ejecutor desacoplado del dominio; un proveedor
persistente puede sustituirlo sin cambiar `OptimizationInput` ni el solver.
Los estados operativos `QUEUED`/`RUNNING` se separan de los resultados
`OPTIMAL`, `FEASIBLE`, `INFEASIBLE` y `UNKNOWN`. Cancelar solicita la parada al
callback de CP-SAT y deja una explicación reproducible.

## Explicabilidad

Cada solución muestra:
- por qué se incluyó cada curso;
- qué requisito satisface;
- qué desbloquea;
- restricciones activas;
- supuestos de oferta;
- estatus del solver.

La API expone `POST /api/v1/scenarios/{scenario_id}/optimization-runs`,
`GET /api/v1/scenarios/{scenario_id}/optimization-runs`,
`GET /api/v1/optimization-runs/{run_id}` y
`POST /api/v1/optimization-runs/{run_id}/cancel`. `/planner` presenta el
estado, hashes, versión, diferencias de cursos añadidos/movidos/retirados,
conflictos y supuestos; iniciar una ejecución nunca muta `CourseAttempt` ni
el escenario.
