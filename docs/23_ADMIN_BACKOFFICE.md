# 23 — Backoffice curricular

## Pantallas

- Source Inbox
- Documents
- Snapshots
- Extraction candidates
- Semantic diff
- Draft revision
- Rule inspector
- Evidence viewer
- Validation results
- Review queue
- Publication
- Revision history
- Impact analysis

## Rule inspector

Debe mostrar AST legible + representación visual + evidencia.

## Diff

Ejemplo:
- `course added`
- `course removed`
- `credits 3 → 4`
- `requirement changed`
- `mandatory → elective`
- `group min 3 → 4`

## Impact analysis

Antes de publicar:
- auditorías afectadas;
- estudiantes cuyo estado podría cambiar;
- reglas desconocidas nuevas;
- ciclos;
- totals inconsistent.

La publicación requiere confirmación explícita.
