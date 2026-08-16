---
name: regression-debug
description: Diagnóstico de regresiones sin parches ciegos: reproduce, minimiza, identifica causa raíz, añade test y verifica no romper invariantes.
---

# Regression debug

1. Reproduce.
2. Congela caso como test.
3. `git bisect`/diff si útil.
4. Identifica capa que viola el contrato.
5. Corrige causa raíz, no síntoma.
6. Ejecuta suite afectada + global.
7. Documenta si revela invariant faltante.
