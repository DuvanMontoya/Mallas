# ADR-0015 — Read model de malla curricular interactiva

**Estado:** ACCEPTED

## Contexto

La malla necesita combinar una revisión curricular versionada, componentes y
agrupaciones, reglas de requisitos, evidencia, dependencias y —cuando existe
autorización— estado personal y oferta por período. La posición de una tarjeta
en una pantalla no es una regla académica y no debe convertirse en una
suposición de semestre. La UI tampoco puede resolver el AST ni consultar
directamente el ORM para decidir elegibilidad.

## Decisión

Se publica `GET /api/v1/curriculum-map` como read model del bounded context
`curriculum`, implementado por
`modules.curriculum.application.map.build_curriculum_map`.

El servicio selecciona una revisión explícita o la revisión más reciente
disponible, conserva su estado epistemológico/publicación, carga la política de
layouts del plan desde un archivo versionado, proyecta componentes,
agrupaciones, membresías, requisitos, AST, procedencia y cursos, y deriva de
forma determinista los niveles de dependencias y relaciones directas. La
oferta sólo se agrega cuando se selecciona el período. Estados personales sólo
se agregan para una matrícula autorizada; sin matrícula el estado es
`NOT_ASSESSED` y un hecho no verificable permanece `UNKNOWN`.

El frontend consume el cliente generado, filtra y selecciona para la vista,
persiste preferencias en URL/local storage y muestra la ficha de curso. No
calcula elegibilidad, graduación, créditos aplicados, oferta ni requisitos.
`dependency-depth` y `component-lanes` son vistas disponibles en P10. Las
vistas `suggested-path` y `user-scenario` permanecen explícitamente pendientes
de los bounded contexts de planificación/escenarios hasta que exista su estado
persistido.

## Alternativas descartadas

- Crear una tabla JSON monolítica de la malla: perdería la separación entre
  `CourseVersion`, `PlanMembership`, reglas, evidencia y oferta.
- Hacer que Next calcule elegibilidad o profundidades normativas: duplicaría el
  motor y permitiría decisiones no auditables.
- Etiquetar las columnas como semestres: introduciría una regla académica sin
  fuente oficial.
- Mostrar todas las aristas en la malla principal: produce ruido visual y no
  escala; el grafo completo queda en su propia vista.

## Consecuencias

- La malla puede representar estados incompletos sin inventar hechos y puede
  cachear el read model mediante `ETag`.
- La ficha de curso tiene trazabilidad suficiente para abrir requisitos,
  evidencia, auditoría y grafo.
- Las preferencias de vista no son datos académicos ni alteran la revisión.
- La selección de una matrícula queda protegida por ownership/RBAC y no se
  mezcla accidentalmente con una lectura pública.

## Riesgos y revisión

- El read model crecerá cuando se publiquen planificador, escenarios y grafo;
  esos módulos deben extender el contrato mediante cambios versionados, no por
  campos improvisados desde el frontend.
- La política de layouts debe revisarse cuando aparezca una fuente normativa
  que describa posiciones oficiales. En ese caso se crea una nueva revisión o
  un ADR posterior con la evidencia correspondiente.
