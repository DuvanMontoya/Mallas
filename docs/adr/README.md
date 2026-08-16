# Architecture Decision Records (ADR)

Los ADR capturan decisiones que no deben depender de la memoria del agente.

## Regla

- Una decisión arquitectónica significativa nueva crea un ADR nuevo.
- No se reescribe retroactivamente un ADR aceptado para fingir que siempre se decidió lo nuevo.
- Si cambia una decisión, el ADR posterior referencia y **supersede** al anterior.
- Cada ADR debe contener contexto, decisión, alternativas descartadas, consecuencias, riesgos y condiciones para revisarla.

## Estados

`PROPOSED`, `ACCEPTED`, `SUPERSEDED`, `REJECTED`.
