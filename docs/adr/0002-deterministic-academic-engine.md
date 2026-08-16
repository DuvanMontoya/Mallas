# ADR-0002 — El motor académico es determinista y no usa LLM

**Estado:** ACCEPTED

## Decisión
Elegibilidad, auditoría de grado, asignación de créditos y desbloqueos se calculan mediante un motor Python puro a partir de una revisión curricular versionada y una historia académica normalizada.

## Invariantes
- mismo input => mismo output;
- aritmética exacta para créditos/porcentajes;
- cada resultado es explicable;
- `UNKNOWN` se propaga explícitamente;
- ningún LLM participa en una decisión autoritativa.

Los LLM sólo pueden asistir en extracción/clasificación de fuentes y generar candidatos sujetos a validación y revisión.
