# Production gates

Antes de declarar producción lista deben existir evidencias de:

- clone limpio reproducible;
- migración desde DB vacía;
- tests completos verdes;
- E2E de journeys críticos;
- accesibilidad automatizada + revisión manual;
- threat model y remediación de High/Critical;
- dependency/secret scanning;
- observabilidad en entorno desplegado;
- backup real y restore probado;
- rollback probado;
- load/performance baseline;
- currículo publicado con provenance;
- documentación/runbooks vigentes;
- auditoría anti-MVP `prompts/98_ANTI_MVP_COMPLETENESS_AUDIT.md` sin omisiones bloqueantes.
