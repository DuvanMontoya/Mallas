# RESUME — continuar sin contexto conversacional previo

No me pidas que repita el proyecto. El repositorio contiene la memoria.

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md`.
3. Lee `docs/state/ROADMAP_STATUS.json`.
4. Lee `docs/state/OPEN_DECISIONS.md`.
5. Lee `docs/state/RISKS.md`.
6. Lee las últimas entradas de `docs/state/SESSION_LOG.md`.
7. Ejecuta `git status`, `git diff`, `git log --oneline -20`.
8. Ejecuta `python scripts/verify.py`.
9. Si hay trabajo incompleto/roto del turno anterior, termínalo primero.
10. Identifica el primer item del roadmap `pending`/`in_progress` cuyas dependencias estén `done`.
11. Abre el prompt indicado por ese item.
12. Carga Skills requeridas.
13. Continúa implementando, probando, revisando y actualizando estado.

No vuelvas a crear arquitectura desde cero.
No reemplaces decisiones documentadas sin ADR.
No conviertas el alcance en MVP.
No declares completado algo sólo porque el contexto anterior se perdió.

Si el roadmap marca P25/P26 terminados, ejecuta `98_ANTI_MVP_COMPLETENESS_AUDIT.md` antes de afirmar finalización.
