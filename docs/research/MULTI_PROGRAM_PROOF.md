# P94 — Prueba de arquitectura multiprograma

**Fecha:** 2026-08-17  
**Estado:** `SYNTHETIC_ARCHITECTURE_PROOF`; no se publica un segundo currículo normativo.

## Qué se demostró

`apps/api/tests/test_multi_program_architecture.py` registra en la misma base de
prueba dos árboles independientes:

- Universidad/sede/facultad/programa/plan/revisión de Estadística;
- Universidad/sede/facultad/programa/plan/revisión sintéticos de Computer Science.

Ambos usan exactamente los mismos modelos relacionales, el mismo motor Python
puro y el mismo AST compuesto `ALL` con `COURSE_PASSED` +
`CREDITS_IN_GROUP`. El test verifica que las revisiones, instituciones, cursos y
requisitos no se cruzan, y que parseo, serialización y evaluación dan el mismo
resultado para ambos programas.

No se añadió un nodo AST. La norma sintética no requiere una semántica nueva;
los nodos existentes ya expresan la condición. Tampoco se añadieron branding,
`if program == ...`, datos normativos reales ni una migración.

## Fuentes y límites epistemológicos

Este milestone prueba estructura y aislamiento, no afirma que Computer Science
sea un programa oficial de la institución. No existe en este checkout una fuente
oficial archivada autorizada para incorporar ese currículo, por lo que el árbol
es sólo un fixture de arquitectura y no puede pasar a `PUBLISHED` ni aparecer en
la oferta de producto.

## Verificación requerida

- `test_institutions_and_programs_are_isolated_without_engine_forks`: verifica
  topología y no contaminación entre revisiones.
- `test_same_ast_round_trip_and_evaluation_apply_to_both_programs`: verifica
  equivalencia AST y determinismo del evaluator sin ORM.
- Las invariantes genéricas de dominio y el suite completo deben ejecutarse con
  Python 3.14/Django accesibles antes de cerrar el milestone como `done`.

Los reviewers `curriculum-auditor` y `architecture-reviewer` no están expuestos
en este entorno; se efectuó una revisión manual read-only y se dejó el estado
pendiente por la ejecución bloqueada de la suite.
