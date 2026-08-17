# 07 — Versionado curricular y temporalidad

## Problema

El Acuerdo 496/2023 permite revisar anualmente la oferta de optativas. Además, normas institucionales pueden modificar requisitos sin reemplazar el documento base.

Por eso `plan_2514` no es un JSON editable eterno.

## Modelo

`CurriculumPlan(2514)` tiene N `CurriculumRevision`.

Estados:
- `DRAFT`
- `IN_REVIEW`
- `APPROVED`
- `PUBLISHED`
- `SUPERSEDED`
- `RETIRED`

Publicación crea un snapshot inmutable.

La publicación es una transición transaccional. El servicio bloquea la
propuesta, la revisión candidata y la revisión actualmente publicada del plan;
valida la base que la propuesta declara, congela el hash de contenido y sólo
entonces marca la candidata como `PUBLISHED`. Si existía una revisión publicada,
ésta pasa a `SUPERSEDED` y la nueva conserva su relación `supersedes`. El
recibo, el `PublicationEvent`, sus impactos y las solicitudes de notificación
se escriben en la misma transacción. Un fallo de validación no crea recibo,
evento ni notificación.

Una revisión publicada y su evento de publicación no se editan. Una corrección
o un rollback funcional se expresa como una nueva revisión con nueva evidencia,
no mediante la mutación de una publicación histórica.

## Fechas

Separar:
- publicación de norma;
- entrada en vigencia;
- vigencia de revisión;
- captura de fuente;
- fecha de auditoría.

## Cohortes/reingresos

No asumir que la revisión más nueva aplica automáticamente a todo estudiante.

El `ProgramEnrollment` debe conservar:
- plan asignado;
- revisión base;
- eventos de transición;
- decisiones administrativas.

Si no se puede determinar la revisión aplicable, mostrar `NEEDS_REVIEW`.

La publicación no cambia automáticamente `revision_basis` de las matrículas.
Cada matrícula que usaba la revisión sustituida queda en un `PublicationImpact`
con la auditoría previa, su `result_hash`, los cambios semánticos y un trabajo
de recomputación que requiere decisión explícita sobre la revisión aplicable.
Así se identifican los estudiantes afectados sin reescribir su historia ni
presentar una nueva conclusión como si fuera retroactiva.

Las auditorías históricas conservan la revisión, el hash de revisión, la
entrada, la versión del motor y el hash de resultado con los que fueron
generadas. Por tanto, una auditoría anterior sigue siendo explicable aunque el
plan tenga una revisión publicada más nueva.

## Diff semántico

Comparar:
- cursos agregados/retirados;
- créditos modificados;
- obligatoriedad;
- membresía;
- requisitos;
- mínimos de grupos;
- total del plan;
- requisitos de grado;
- vigencia.

El diff debe ignorar cambios puramente visuales.
