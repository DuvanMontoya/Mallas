# 05 — Especificación del motor de reglas

## Resultado trivalente ampliado

No basta `True/False`.

Cada nodo retorna:

```json
{
  "status": "SATISFIED | UNSATISFIED | UNKNOWN | NOT_APPLICABLE",
  "progress": {"current": 0, "required": 0, "unit": "credits|courses|ratio|boolean"},
  "children": [],
  "evidence": [],
  "explanation_key": "...",
  "facts_used": []
}
```

## AST mínimo

- `ALL`
- `ANY`
- `NOT` sólo si una norma realmente lo requiere
- `COURSE_PASSED`
- `COURSE_IN_PROGRESS`
- `COURSE_PASSED_OR_IN_PROGRESS`
- `CREDITS_IN_GROUP`
- `CREDITS_IN_COMPONENT`
- `TOTAL_CREDITS`
- `PERCENTAGE_OF_PLAN`
- `GROUP_COMPLETED`
- `MANDATORY_COURSES_COMPLETED`
- `MINIMUM_GRADE`
- `EXTERNAL_REQUIREMENT`
- `EQUIVALENT_COURSE_PASSED`
- `COREQUISITE`
- `UNKNOWN`

## Semántica

### ALL
- SATISFIED si todos SATISFIED;
- UNSATISFIED si al menos uno UNSATISFIED y ninguno convierte la decisión en desconocida relevante;
- UNKNOWN cuando no puede determinarse por información incierta.
La semántica exacta debe documentarse/testearse para combinaciones UNKNOWN.

### ANY
SATISFIED si uno satisface. Si ninguno satisface y al menos uno es UNKNOWN → UNKNOWN.

### Créditos
Usar enteros. Nunca float.

### Porcentajes
Representar como fracción exacta:
`approved * denominator >= total * numerator`.

Para 80% de 141:
`5 * approved >= 4 * 141`, mínimo entero 113.

## Contexto del evaluador

```python
AuditContext(
    revision=...,
    passed_courses=...,
    in_progress_courses=...,
    earned_credits=...,
    allocated_credits=...,
    group_facts=...,
    external_requirements=...,
    recognitions=...,
    exceptions=...,
)
```

El evaluador no hace queries.

## Explicación

Cada resultado debe generar una explicación estructurada y localizable, no texto arbitrario del LLM.

Ejemplo:
`requires_all(course:2016369, credits_in_group:PROGRAMACION>=3)`.

La UI traduce:
«Requiere aprobar Muestreo Estadístico y completar al menos 3 créditos de Programación».

## Propiedades

- determinismo;
- pureza;
- serialización round-trip;
- no dependencia temporal implícita;
- no acceso a red;
- no acceso DB;
- no LLM;
- explicación estable;
- hash canónico del AST.

## Implementación P03

El núcleo ejecutable vive en `apps/api/domain/rules/` y no importa Django, ORM,
red ni LLM. `ast.py` define el AST discriminado versionado (`1.0.0`), parser
estricto, serializer canónico y hash; `evaluator.py` recibe únicamente un
`AuditContext` inmutable de hechos y devuelve un árbol `EvaluationResult` con
estado, progreso, claves de explicación, hechos y evidencias; `graph.py` hace
análisis de dependencias directas y ciclos.

La serialización persistible de un AST incluye `schema_version` y `rule`.
Los AST de los baselines históricos pueden conservarse en su forma de nodo
original, pero sus `Requirement` persistidos registran `ast_schema_version` y
`ast_hash`. Los porcentajes se comparan como enteros (`approved * denominator
>= total * numerator`) y el umbral mínimo de 4/5 de 141 se calcula mediante
división entera exacta.

La semántica de composición es Kleene fuerte: en `ALL`, `UNSATISFIED` domina a
`UNKNOWN`; si no hay un falso pero falta un hecho, el resultado es `UNKNOWN`.
En `ANY`, `SATISFIED` domina; si no hay un verdadero y existe un desconocido,
el resultado es `UNKNOWN`. `NOT_APPLICABLE` sólo aparece cuando el contexto lo
marca explícitamente.
