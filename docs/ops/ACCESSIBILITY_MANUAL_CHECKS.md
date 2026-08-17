# Comprobaciones manuales de accesibilidad

## Alcance y evidencia automatizada

Esta lista acompaña P22 — Accesibilidad y E2E cross-device. La evidencia ejecutable registrada el 2026-08-16 es:

- `axe-core 4.13.0` inyectado en `/`, `/audit`, `/analytics`, `/curriculum`, `/graph?selected=1000003`, `/planner`, `/offerings?term=2026-2S`, `/history`, `/sources` y `/login?next=/audit`: 20/20 ejecuciones desktop/mobile sin ninguna violación.
- Playwright `1.62.1`: 50/50 E2E en los proyectos Desktop Chrome y Pixel 7.
- Las pruebas cubren skip link, foco del menú móvil, Escape y restauración de foco, selección curricular, foco contextual del grafo, alternativa textual del grafo, selector `Mover a` del planificador, viewport móvil, zoom equivalente a 200%, reduced motion, recorrido estudiante y workflow editor → revisor → publicación.
- Contraste automatizado con axe no reportó violaciones bloqueantes en las páginas críticas.

## Auditoría de contraste de tokens

Los ratios se calcularon con la fórmula WCAG 2 para los tokens usados como texto normal. El token claro corregido `--text-muted: #5a6d61` alcanza 5.53:1 sobre `#ffffff` y 5.13:1 sobre `#f4f7f5`; el valor anterior `#6f8177` alcanzaba sólo 4.13:1 y fue retirado. Otros pares representativos del tema claro: `--text-body #42564c` sobre blanco 7.87:1, `--accent-700 #26704f` 5.98:1, `--focus #1b7a50` 5.32:1, `--status-passed #20734e` 5.80:1, `--status-eligible #2f6c9f` 5.58:1, `--status-blocked #a34545` 6.01:1 y `--status-unknown #765c9e` 5.53:1.

En tema oscuro se verificaron los tokens contra `--surface-0 #17231d`: `--text-muted #91a79a` 6.33:1, `--text-body #c1d1c7` 10.21:1, `--accent-700 #9be0bc` 10.65:1, `--focus #a4e8c1` 11.50:1 y los tonos de estado entre 8.09:1 y 9.93:1. Los estados también se expresan con texto, borde o icono; nunca dependen sólo del color.

## Lista manual previa a release

Estas comprobaciones requieren un navegador de usuario y un lector de pantalla instalados; no se simulan como `PASS` por el hecho de que axe pase.

### Teclado y foco

- [ ] Con `Tab`, `Shift+Tab`, `Enter`, `Space`, flechas y `Escape`, recorrer el dashboard, malla, auditoría, grafo, planificador, oferta, historia y fuentes sin quedar atrapado.
- [ ] Activar el skip link; verificar que el foco queda en `#main-content` y que el indicador es visible.
- [ ] En viewport móvil, abrir `Menú` con teclado, verificar que el foco entra en el primer enlace, cerrar con `Escape` y verificar que vuelve al botón.
- [ ] Abrir una ficha de curso desde una tarjeta; verificar que el foco llega al título de la ficha. Cerrar y verificar que vuelve a la tarjeta que la abrió.
- [ ] En el grafo, confirmar que cambiar el foco anuncia el código/nombre y que la lista textual se puede usar sin tocar el canvas.
- [ ] En el planificador, mover un curso sólo con el selector `Mover a`; verificar que no es necesario arrastrar.

### Lector de pantalla

- [ ] NVDA + Firefox/Chrome en Windows: comprobar landmarks, encabezados, nombres de botones, tablas, estados y mensajes `aria-live`.
- [ ] VoiceOver + Safari en macOS/iOS: repetir dashboard, ficha curricular, grafo textual, selector del planificador y menú móvil.
- [ ] Confirmar que `UNKNOWN`, `BLOCKED`, `PASSED` y `IN_PROGRESS` se anuncian como texto y no sólo como color o punto.
- [ ] Confirmar que el grafo anuncia relaciones directas, condiciones y rutas mediante la alternativa textual.
- [ ] Confirmar que el contador de filtros y los resultados de mutaciones del planificador se anuncian sin perder el foco.

### Zoom, reflow y movimiento

- [ ] Navegador al 200% a 1280×720 equivalente a 640 CSS px: no debe aparecer scroll horizontal para leer o accionar el planificador, la malla o la auditoría.
- [ ] Aumentar texto al 200% sin ocultar controles ni truncar nombres de cursos, evidencia o problemas.
- [ ] Preferencia `prefers-reduced-motion: reduce`: confirmar que no hay shimmer/spin/transiciones perceptibles necesarias para entender el estado.
- [ ] Comprobar que el grafo visual no es el único canal de información y que el contenido textual sigue disponible con estilos desactivados.

### Evidencia de ejecución manual

La ejecución headless y el entorno compartido no incluyen NVDA, VoiceOver ni un dispositivo físico. El responsable de release debe completar las casillas anteriores en un entorno de usuario y adjuntar fecha, navegador, lector de pantalla, viewport, incidencias y resultado antes de publicar una revisión curricular o una versión de producción.
