# 06 — Auditoría de grado

## Input

- curriculum revision;
- student academic history;
- recognitions/equivalences;
- individual exceptions;
- external graduation facts;
- optional audit date.

## Output principal

```text
overall:
  status
  required_credits
  earned_credits
  applied_credits
  unapplied_credits

components[]
  required
  applied
  remaining

groups[]
  required
  applied
  remaining
  mandatory_missing[]
  options_available[]

graduation_requirements[]
unknowns[]
warnings[]
next_unlocks[]
```

## Allocation

El sistema debe resolver asignación de créditos sin doble conteo.

Casos:
- curso de 4 créditos en agrupación que requiere 3;
- curso potencialmente elegible en más de un bucket;
- homologación;
- curso con cambio de créditos entre versiones;
- libre elección;
- excedentes.

Primero implementar un asignador determinista basado en reglas explícitas. Si aparecen asignaciones múltiples con objetivos conflictivos, modelar un problema de matching/ILP y conservar explicación.

Nunca «mover» automáticamente un crédito excedente a otra agrupación sin norma.

## Auditoría parcial

Un estudiante puede no tener historia completa. Resultado debe advertir `UNKNOWN` donde la falta de información afecta conclusión.

## Reproducibilidad

Guardar:
- input fingerprints;
- revision hash;
- engine version;
- result hash.

Un audit viejo debe poder explicarse incluso si existe una revisión nueva.
