# 24 — Matriz de lógica de negocio

| Caso | Regla |
|---|---|
| Curso aprobado | Satisface `COURSE_PASSED` si el intento es reconocible por la revisión/equivalencias |
| Curso perdido | No aporta créditos |
| Curso cancelado | No aporta |
| Curso homologado | Aporta según reconocimiento oficial |
| Curso repetido | Evitar duplicar créditos; política de nota separada |
| Curso de 4 cr para grupo min 3 | Grupo puede completarse; ledger registra excedente no reasignado automáticamente |
| Prerrequisito ANY | Basta una alternativa |
| Prerrequisito ALL | Todas |
| Correquisito | Puede estar aprobado previamente o planificado/inscrito simultáneamente según contexto |
| 80% plan 141 | mínimo 113 créditos si la norma usa créditos aprobados totales |
| Grupo completado | Cumple mínimos + obligatorias + reglas específicas |
| Curso no ofertado | Puede ser elegible pero no ofertado |
| Curso ofertado y bloqueado | Se muestra oferta, pero estado académico bloqueado |
| Requisito ambiguo | `UNKNOWN`; no declarar elegible/no elegible |
| Norma posterior | nueva revisión, no mutar publicada |
| Excepción individual | afecta auditoría individual, no plan global |
| Doble membresía | no doble conteo salvo política explícita |
| Libre elección | ledger independiente |
| Requisito B1 | requisito de grado no crediticio, no añadir a 141 créditos |
| Layout semestral | no altera reglas |
