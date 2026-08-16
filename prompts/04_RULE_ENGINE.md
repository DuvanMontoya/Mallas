# P03 — Motor de reglas

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/05_RULE_ENGINE_SPEC.md`.
4. Lee `schemas/requirement.schema.json`.
4. Lee `data/fixtures/golden_rule_cases.json`.

## Skills obligatorias
- carga `feature-delivery`

## Objetivo

Implementar un AST versionado, puro, trivalente y explicable para prerrequisitos/correquisitos/thresholds sin ORM, red ni LLM.

## Entregables obligatorios

1. Definir tipos Python exhaustivos/discriminados para todos los nodos mínimos.
2. Parser/serializer canónico desde JSON.
3. Hash estable del AST.
4. Evaluator puro con `SATISFIED/UNSATISFIED/UNKNOWN/NOT_APPLICABLE`.
5. Semántica ALL/ANY con UNKNOWN formalmente testeada.
6. COURSE_PASSED, credits group/component, total credits, percentage exacta, group completed, external, corequisite.
7. Explanation tree estructurado con message keys/facts/evidence refs.
8. Canonical validation y errores de schema.
9. Property-based tests: determinismo, round trip, logical identities seguras.
10. Golden cases del plan 2514.
11. Cycle-analysis utilities para graph de requisitos directos.
12. Benchmarks básicos.

## Gates de aceptación

- [ ] ningún import django en núcleo evaluator
- [ ] 112 no satisface 80% y 113 sí para 141
- [ ] ANY/ALL/UNKNOWN correctos
- [ ] roundtrip AST conserva semántica/hash
- [ ] golden cases verdes
- [ ] Hypothesis suite verde
- [ ] no float en créditos/porcentajes

## Revisión

- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `curriculum-auditor` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
