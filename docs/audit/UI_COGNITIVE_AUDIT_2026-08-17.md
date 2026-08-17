# P92 — Auditoría UX/UI y cognitiva

**Fecha:** 2026-08-17  
**Alcance:** dashboard, malla, grafo, auditoría, oferta, planner y backoffice editorial.  
**Reglas de dominio:** no se modificaron.

## Veredicto

La estructura de interacción y el lenguaje visible implementan las distinciones
críticas del producto: aprobado/aplicado, elegible, ofertado, planeado,
bloqueado y desconocido. Los bloqueos se acompañan de explicación y evidencia;
la superficie de grafo tiene una alternativa textual; planner ofrece selector de
movimiento además de drag/drop; la disponibilidad de oferta se separa de la
eligibilidad y de la capacidad reportada.

El resultado de la auditoría de comportamiento es **históricamente verificado
por P22/P23**, pero la repetición completa en esta ejecución está
`BLOCKED_EXTERNAL`: no se puede iniciar un servidor Next porque los enlaces de
dependencias existentes devuelven `EPERM`, el standalone generado apunta a esos
enlaces y no permite leer `next/package.json`, y no hay API fixture activa.
No se presenta una verificación runtime bloqueada como PASS actual.

## Recorrido cognitivo

| Flujo | Pregunta del usuario | Evidencia en implementación | Resultado |
|---|---|---|---|
| Dashboard | ¿Qué hago primero? | Hero con “Abrir auditoría”, “Explorar la malla” y tres tarjetas de primer paso | PASS por fixture histórica; jerarquía clara |
| Dashboard/auditoría | ¿Qué he aprobado y cuánto aplica? | Métricas separan créditos aplicados, progreso y requisito externo B1; microcopy advierte que el porcentaje no equivale a graduación | PASS |
| Malla | ¿Qué me falta y de dónde sale? | Agrupaciones, estados, filtros, ficha de curso y `EvidencePopover`; layout visual rotulado como no normativo | PASS |
| Grafo | ¿Qué abre cada curso y por qué está bloqueado? | Resaltado contextual, panel de foco, relaciones `ALL/ANY/threshold`, lista textual y anuncio live | PASS |
| Oferta | ¿Puedo cursarlo ahora y está ofertado? | Badges separados para estado académico, frescura, capacidad no reportada y conflictos de horario | PASS |
| Planner | ¿Qué ruta puedo probar sin cambiar mi historia? | Escenarios privados, drag/drop y combobox de alternativa, optimización con comparación | PASS |
| Backoffice | ¿Puedo publicar una regla sin evidencia? | Diff, AST, evidence links, validación, confirmación explícita y estados editoriales | PASS; publicación no es automática |

## Accesibilidad y responsive

La inspección de código confirma:

- skip link hacia `#main-content` y restauración de foco del menú móvil;
- `:focus-visible` con contraste y grosor visible;
- nombres accesibles para controles, tablas con `caption` y `scope`, `aria-live`
  en cambios de contexto y `aria-hidden` sólo para decoración;
- alternativa textual navegable para React Flow;
- selector de movimiento accesible para planner en móvil;
- mensajes explícitos para `UNKNOWN`, estados no evaluados, ausencia de oferta,
  errores y datos no reportados;
- `@media (prefers-reduced-motion: reduce)` que elimina animaciones y scroll
  suave;
- grids responsive, overflow controlado y prueba de zoom del 200 % en la suite;
- estados con texto y badges, no sólo color.

La suite Playwright/axe de P22/P23 recorrió 10 rutas críticas en desktop y
móvil: **50/50 pruebas E2E PASS** y **20/20 comprobaciones axe PASS**, además de
keyboard, foco, reduced motion y 200 % zoom. La prueba de screen reader real
(NVDA/VoiceOver/TalkBack) no está disponible en este entorno; axe y semántica
HTML no sustituyen esa prueba manual.

## Microcopy y observaciones editoriales

La UI mantiene las frases de decisión en español y deja nombres técnicos (AST,
semantic diff, `UNKNOWN`) donde sirven como identificadores editoriales. La
principal deuda de pulido es homogeneizar algunos encabezados internos en inglés
del backoffice (`Source Inbox`, `Publication event`, `Rule inspector`) si la
audiencia editorial final no es bilingüe. No se cambia automáticamente porque
la decisión es editorial y no afecta la corrección ni la semántica de dominio;
queda como mejora de copy de prioridad baja.

No se identificaron estados codificados únicamente por color, interacción sin
alternativa de teclado ni una flecha de grafo usada como autoridad normativa.

## Mediciones ejecutadas en esta sesión

- Auditoría de bundle sobre el build existente: **PASS**, 19 chunks, 2446.3 KiB
  agregados; React Flow/ELK están cargados dinámicamente por ruta.
- Inspección estática de rutas, componentes, CSS de foco/reduced-motion y suites
  E2E: **PASS**.
- Inicio del standalone existente: **BLOQUEADO** por `Cannot find module 'next'`
  después de `EPERM` al leer el `node_modules` enlazado.
- Inicio de API fixture + Playwright + axe en esta ejecución: **BLOQUEADO** por
  la misma cadena de permisos; se conservan los resultados ejecutados en P22/P23
  sin reetiquetarlos como actuales.
- UX reviewer especializado: no está expuesto en este entorno; se hizo revisión
  manual equivalente y se registró la limitación.

## Criterio de cierre P92

El diseño no requiere una corrección de código detectable por esta auditoría.
P92 permanece **pendiente de repetición runtime** hasta recuperar acceso a las
dependencias frontend y ejecutar el recorrido fixture completo, axe, teclado,
zoom y reduced motion en el mismo checkout.
