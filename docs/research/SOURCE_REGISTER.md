# Registro de fuentes — snapshot de investigación 2026-08-08

## UNAL

1. Plan de Estudios — Estadística, Facultad de Ciencias, Bogotá  
   https://ciencias.bogota.unal.edu.co/estudiar_en_la_facultad/pregrados/estadistica/plan_de_estudios/  
   Uso: identidad del programa, 9 semestres, 141 créditos.

2. Preguntas Frecuentes — Área Curricular de Estadística  
   https://ciencias.bogota.unal.edu.co/areas_curriculares/estadistica/preguntas_frecuentes/  
   Uso: referencia institucional actual al Acuerdo 496/2023.

3. Prueba de Inglés Pregrado — Dirección Nacional de Admisiones  
   https://admisiones.unal.edu.co/otras-pruebas/prueba-de-ingles-pregrado/  
   Uso: nivel B1 y requisito de grado, además de referencias al Acuerdo 029/2024 y Circular 02/2024.

4. Acuerdo 496 de 2023 — copia local aportada por el usuario  
   `sources/unal/estadistica/ACUERDO_496_2023_PLAN_2514_ESTADISTICA.pdf`  
   SHA-256: `9253909e4208304dd0eb141b5c388956d0008bafe4e7b9033f2aabd5225e8bad`

## Frameworks y tooling

5. Django 6.1 dev release notes  
   https://docs.djangoproject.com/en/dev/releases/6.1/

6. Django 6.0.8 release notes  
   https://docs.djangoproject.com/en/6.0/releases/6.0.8/

7. Next.js releases/blog  
   https://nextjs.org/blog/

8. NPM Next versions  
   https://www.npmjs.com/package/next?activeTab=versions

9. codex Rules / AGENTS.md  
   https://codex.ai/docs/rules/

10. codex Skills  
    https://codex.ai/docs/skills

11. codex Agents  
    https://codex.ai/docs/agents/

12. codex Permissions  
    https://codex.ai/docs/permissions/

13. codex Providers / gpt  
    https://codex.ai/docs/providers/

14. gpt model details  
    https://api-docs.gpt.com/quick_start/pricing

15. gpt coding-agent integration  
    https://api-docs.gpt.com/guides/coding_agents

16. React Flow  
    https://reactflow.dev/

17. OR-Tools CP-SAT  
    https://developers.google.com/optimization/cp/cp_solver

## Política

Este registro es descubrimiento y baseline, no reemplaza la obligación del agente de volver a consultar documentación oficial antes de cualquier cambio version-sensitive.

## Oferta académica temporal y horarios — investigación 2026-08-16

18. Buscador público de cursos del SIA — Universidad Nacional de Colombia
    https://siabog.unal.edu.co/academia/apoyo-administrativo/
    Uso: punto de referencia oficial para consultar programación académica
    pública por curso, plan y período. La aplicación conserva una referencia de
    fuente y una captura autorizada; no automatiza navegación autenticada ni
    ejecuta scraping privado.

19. Preguntas frecuentes del SIA
    https://siabog.unal.edu.co/academia/libre-acceso/faq.do
    Uso: confirma que la información oficial de programación se consulta en el
    buscador de cursos del SIA, que las unidades académicas actualizan los
    datos, y que el acceso público al enlace es una superficie institucional.

20. Manual del buscador público de cursos del SIA
    https://siabog.unal.edu.co/academia/libre-acceso/manuales/539019aa08a39d44dc7c45e1a888f821.pdf
    Uso: evidencia de las capacidades públicas de búsqueda por curso, plan y
    horario. Se usa para diseñar el adaptador, no como autorización para
    automatizar una sesión privada.

21. Calendario académico — Sede Bogotá
    https://bogota.unal.edu.co/la-sede/calendario-academico
    Uso: fechas oficiales de períodos y programación académica de la sede.
    Es una fuente de calendario del término, no una fuente suficiente para
    afirmar que un grupo concreto tiene cupos o que se encuentra ofertado.

22. Instructivo de inscripción — DNINFOA
    https://dninfoa.unal.edu.co/docs/instructivo_inscripcion.pdf
    Uso: delimita que la inscripción es una operación del SIA. El navegador
    curricular sólo informa oferta, elegibilidad y conflictos; no inscribe ni
    simula una operación autenticada de inscripción.

### Límite de acceso y frescura

La investigación no autoriza scraping de superficies autenticadas ni el uso de
credenciales del usuario. El adaptador implementado acepta únicamente un
payload normalizado archivado y autorizado, calcula su SHA-256, conserva
`retrieved_at` y lo vincula a `SourceSnapshot`. Sin una bandera explícita de la
fuente, capacidad y matrícula permanecen `UNKNOWN`; la interfaz nunca afirma
disponibilidad en tiempo real. Las lecturas se etiquetan `FRESH`, `STALE` o
`UNKNOWN` según la edad de la captura.

## Reauditoría normativa P90 — 2026-08-17

Se consultaron nuevamente las fuentes oficiales del plan 2514, la FAQ del Área
Curricular, el índice de Sistema Legal, la página institucional de requisito de
inglés y la convocatoria oficial 2026-2 de práctica. La comparación no produjo
un cambio semántico confirmado frente a `2514-AC496-2023`; por tanto, la revisión
local no fue mutada. El detalle, los estados epistemológicos y los límites del
archivado están en [`docs/research/reaudits/2026-08-17-plan-2514.md`](reaudits/2026-08-17-plan-2514.md)
y en su manifiesto [`2026-08-17-plan-2514-snapshots.json`](reaudits/2026-08-17-plan-2514-snapshots.json).

La consulta remota se conserva como `REMOTE_REFERENCE_ONLY` porque en este
entorno no fue posible guardar los bytes completos de las páginas/PDF. No se
inventan hashes. El Acuerdo 496 local permanece como la evidencia archivada y
con hash registrada arriba; cualquier promoción futura requiere archivado
autorizado y revisión humana. La búsqueda en el índice oficial no encontró una
norma posterior identificable, pero esa observación no demuestra que no exista
una norma no indexada o no accesible.
