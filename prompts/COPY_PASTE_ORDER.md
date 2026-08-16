# Orden exacto para copiar y pegar

## Caso normal — recomendado

**Sólo copie primero:** `00_MASTER_AUTONOMOUS_BUILD.md`.

Ese prompt obliga al agente a leer el repositorio y ejecutar el ROADMAP completo. No necesita copiar 26 prompts en una sola sesión.

## Si la sesión se corta
Copie `99_RESUME_AUTONOMOUS.md` en una sesión nueva.

## Si desea controlar cada fase manualmente
Copie, en orden, 01 → 26. No avance si el prompt anterior dejó gates rojos.

## Auditorías extraordinarias
- fuente académica cambió: `90_CURRICULUM_SOURCE_REAUDIT.md`
- actualizar dependencias: `91_DEPENDENCY_UPGRADE.md`
- pulido UX: `92_UI_POLISH_AND_COGNITIVE_AUDIT.md`
- bug: `93_BUG_FIX_PROTOCOL.md`
- nuevo programa: `94_ADD_NEW_PROGRAM.md`
- incidente: `95_PRODUCTION_INCIDENT.md`
- detectar recortes disfrazados de «después»: `98_ANTI_MVP_COMPLETENESS_AUDIT.md`
