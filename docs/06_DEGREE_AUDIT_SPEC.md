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

## Implementación P04

El núcleo ejecutable vive en `apps/api/domain/audit/engine.py` y no importa
Django, ORM, red ni proveedores externos. `AuditInput` representa la entrada
portable; `AuditContext` normaliza intentos aprobados, cursos en progreso,
reconocimientos, excepciones y advertencias de intentos duplicados; y
`AuditResult` conserva el resultado completo con árbol de requisitos, ledger,
explicaciones localizables, `remaining_requirements` y `next_unlocks`.

`CreditLedger` selecciona determinísticamente un único intento aprobado por
curso, aplica cada curso como máximo una vez y registra por separado créditos
ganados, aplicados y no aplicados. Un curso de cuatro créditos puede cerrar un
bucket de tres créditos, pero el crédito sobrante permanece como excedente. Un
bucket `FREE_ELECTIVE` sólo recibe cursos sin bucket elegible o cursos
electivos cuyos buckets explícitos ya están completos; esto está modelado como
una política curricular abierta, no como una reasignación general de
excedentes. Homologaciones pueden llevar sus propios créditos reconocidos y
las excepciones aprobadas quedan en el resultado como grupos/cursos exentos.

`modules.audit.application.services` prepara snapshots desde la revisión y la
historia persistidas, ejecuta el motor en una transacción y persiste
`DegreeAuditRun`, `DegreeAuditResult` y `CreditAllocation`, incluyendo
fingerprints de historia/excepciones, hash de revisión, versión del motor,
snapshot de entrada y hash de resultado. La ausencia o ambigüedad de un
requisito externo de grado conserva `UNKNOWN`; en particular, B1 no se suma a
los 141 créditos.

La cobertura ejecutable está en `tests/test_degree_audit.py`,
`tests/test_degree_audit_service.py` y
`data/fixtures/golden_degree_audit_cases.json`. Incluye golden cases del plan
2514, no doble conteo, curso de 4/3 créditos, plan completo, requisito externo
desconocido, homologación, excepción, hash reproducible, Hypothesis y
persistencia PostgreSQL.
