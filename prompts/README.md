# Prompts — orden de uso

## Uso normal

1. Pegue `00_MASTER_AUTONOMOUS_BUILD.md`.
2. Deje que el agente avance por `docs/state/ROADMAP_STATUS.json`.
3. Cuando una sesión termine por límite/contexto/interrupción, abra una nueva sesión y pegue `99_RESUME_AUTONOMOUS.md`.
4. Use prompts 01–26 sólo para:
   - obligar a rehacer/auditar una fase;
   - avanzar manualmente si el agente maestro se detuvo;
   - aislar una fase problemática.

## Regla

No pegue todos los prompts a la vez. Cada prompt manda leer el repositorio, por lo que repetirlos sólo consume contexto.

## Si el agente dice «ya está listo» demasiado pronto

Pegue:
- `25_FULL_SYSTEM_AUDIT.md`;
- luego `98_ANTI_MVP_COMPLETENESS_AUDIT.md`.

## Si cambia de modelo

No hace falta volver a explicar el proyecto. Pegue `99_RESUME_AUTONOMOUS.md`.
