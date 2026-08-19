# P100 — Walkthrough de aceptación del workspace curricular

## Naturaleza y límites

Evaluación experta basada en roles, ejecutada sobre el prototipo interactivo de
P100 el 2026-08-19. No participaron estudiantes ni asesores reales; por tanto,
este documento no demuestra los porcentajes de comprensión de
`docs/42_CURRICULUM_WORKSPACE_SPEC.md` §10. Esa investigación es gate de P108.

Referencia visual evaluada:
`curriculum-workspace.html` en el directorio de visualizaciones de la tarea.

## Roles y tareas

| Rol modelado | Tarea | Ruta observable | Resultado |
|---|---|---|---|
| estudiante nuevo | entender qué hacer sin historia | malla inmediata → estados `NOT_ASSESSED` definidos en spec → onboarding no bloqueante | PASS de contrato; implementación en P104 |
| estudiante activo | reconocer aprobado, en curso, elegible y bloqueado | señal textual + borde + nombre accesible con ejes independientes | PASS en prototipo |
| estudiante activo | saber qué falta en un banco | tarjeta compartida `20 / 36` → detalle | PASS; las dos ocurrencias comparten target y progreso |
| estudiante activo | comprobar por qué está bloqueado | Inferencia estadística → detalle → `falta Probabilidad` | PASS en prototipo |
| estudiante planificador | distinguir plan vigente de escenario | control de escenario deshabilitado hasta crear uno | PASS; no se simula estado inexistente |
| asesor | distinguir documento, norma y estado personal | alternar `Aislar capa fuente — esquema` | PASS del mecanismo; el contenido está rotulado como wireframe y no como transcripción fiel |
| asesor | verificar lengua/nivelación | franja inferior separa transcripción literal y requisito externo | PASS; `Inglés VI` se conserva y su mapeo sigue `UNKNOWN` |

## Evidencia de interacción y responsive

| Comprobación | Evidencia | Resultado |
|---|---|---|
| desktop | inspección en Chrome; ocho columnas dentro de `.scroll` | PASS |
| 320 px | override de viewport 320 × 900; índice horizontal y secciones verticales | PASS |
| tablet | breakpoint 600–1023 px con dos columnas lógicas y paneo contenido | PASS estructural |
| overflow | el paneo desktop pertenece al contenedor; en móvil la grilla es de una columna | PASS estructural |
| teclado | nodos son botones; apertura enfoca Cerrar; Escape cierra y retorna al disparador | PASS de implementación del prototipo |
| foco móvil | drawer `dialog` modal, backdrop, fondo `inert`, ciclo de Tab y restauración de scroll | PASS de implementación del prototipo |
| estado accesible | nombres naturales en español, causa/progreso del banco repetido, `aria-expanded`, `aria-controls`, `progressbar`, grupos y contador live | PASS estructural |
| procedencia en detalle | afirmaciones separadas como capa fuente, normativa, personal y derivada | PASS en prototipo |
| modo fuente | oculta capas normativa, personal y derivada; búsqueda y nombre accesible usan sólo el corpus esquemático visible | PASS del aislamiento; no prueba fidelidad del PDF |
| Escape móvil | después de Escape no existe diálogo visible, vuelve navegación/malla al árbol accesible y el curso disparador recupera foco | PASS en Chrome 320 × 900 |
| cambio de modo con detalle abierto | conserva selección y reemplaza la lista por afirmaciones/evidencias del modo esquemático, sin texto de “transcripción fiel” | PASS en Chrome desktop |

## Hallazgos corregidos durante el walkthrough

1. Se separaron completitud, elegibilidad, oferta y planificación.
2. El modo fuente pasó de ocultar tarjetas completas a aislar campos por capa;
   además se rotuló como esquema porque P100 no ingiere coordenadas fieles.
3. El banco repetido ahora comparte `target_id`, objetivo y progreso.
4. Se eliminaron estados de escenario ficticios.
5. Se añadió índice móvil, menú completo, foco visible y retorno de foco.
6. Se añadieron ocho columnas para probar escala y paneo contenido.
7. El progreso aclara que créditos aplicados no equivalen a graduación.
8. Se eliminó el controlador interactivo legacy; una sola función de cierre
   restaura drawer, backdrop, `inert`, `aria-hidden`, foco y scroll.

## Trabajo que permanece abierto

- pruebas con participantes reales y medición de §10: P108;
- lector de pantalla manual y zoom 400 % sobre la implementación real: P104/P108;
- equivalencia visual y de comportamiento en la aplicación, no sólo prototipo:
  P104/P105.
