---
name: curriculum-change
description: Flujo seguro para incorporar o modificar normas, asignaturas, agrupaciones o requisitos con snapshots, evidencia, diff, validación y revisión.
---

# Curriculum change

1. Identifica fuente oficial y vigencia.
2. Captura snapshot inmutable + SHA-256.
3. Registra documento y relaciones normativas.
4. Extrae candidatos como DRAFT.
5. Vincula evidencia por regla.
6. Conserva UNKNOWN.
7. Construye semantic diff contra revisión vigente.
8. Ejecuta invariantes y cycle checks.
9. Ejecuta golden audits/impact analysis.
10. `curriculum-auditor`.
11. Corrige sólo con evidencia.
12. Crea ChangeProposal.
13. Nunca auto-publish.
14. Publicación por reviewer autorizado.
15. Nueva revisión inmutable.
