# Riesgos vivos

| Riesgo | Severidad | Mitigación |
|---|---|---|
| Interpretar una celda ambigua como requisito oficial | Critical | estado UNKNOWN + revisión humana |
| Mezclar malla sugerida con norma | High | `CurriculumLayout` separado |
| Doble conteo de créditos | High | CreditAllocation explícito + property tests |
| LLM publica cambios incorrectos | Critical | workflow sin auto-publish |
| Dependencias framework cambian | Medium | version policy + official docs |
| Oferta académica desactualizada | High | source timestamp + freshness |
| Historia PDF extraída mal | High | preview/confirmation/idempotencia |
| Sobrearquitectura | Medium | monolito modular, ADR gates |
| Regla duplicada en frontend | High | backend authority + contract tests |
