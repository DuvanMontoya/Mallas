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
