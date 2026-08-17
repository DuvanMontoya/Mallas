# 26 — Accesibilidad

Objetivo WCAG 2.2 AA.

Casos específicos:
- el grafo tiene alternativa textual/listado;
- cada arista seleccionada se describe;
- CourseCard usable con teclado;
- drag/drop tiene alternativa por botones/menú;
- status no depende de color;
- tooltips no son único canal de información;
- focus no se pierde al abrir panel;
- contrastes verificados;
- reduced motion;
- lectores de pantalla reciben progreso y requisitos.

Tests:
- `axe-core` automatizado en `tests/foundation.test.tsx` y
  `tests/design-system.test.tsx`, sin violaciones en la base del shell y
  componentes presentacionales;
- Playwright desktop/mobile verifica que el skip link recibe foco por teclado y
  que el auth shell es navegable;
- manual NVDA/VoiceOver al menos en releases importantes.

El shell usa landmarks únicos (una navegación de escritorio y otra etiquetada
para móvil), `aria-current` en la ruta activa, focus-visible, `details/summary`
para popovers sin perder teclado y una alternativa textual para el componente
de grafo. `prefers-reduced-motion` desactiva animaciones de orientación.
## Verificación P22 — 2026-08-16

Se añadió una suite Playwright con `axe-core 4.13.0` para las páginas críticas y dos proyectos (Desktop Chrome y Pixel 7). El gate automatizado quedó en 20/20 ejecuciones sin ninguna violación axe; la suite E2E completa quedó en 50/50.

La navegación ahora gestiona el foco del menú móvil (entrada al primer control, `Escape` y retorno al disparador), devuelve el foco a la tarjeta al cerrar una ficha curricular y enfoca/anuncia el título del foco contextual del grafo. El grafo conserva una lista textual accesible y el canvas no expone nombres ARIA inválidos en sus handles. El planificador mantiene el selector `Mover a` como alternativa completa al drag/drop y lo cubre con teclado real.

Se verificaron viewport móvil, zoom equivalente a 200%, `prefers-reduced-motion`, skip link, recorrido estudiante y editor → revisor → publicación. El contraste claro se corrigió al cambiar `--text-muted` a `#5a6d61` (5.53:1 sobre blanco); el detalle de ratios y la lista manual NVDA/VoiceOver están en [`docs/ops/ACCESSIBILITY_MANUAL_CHECKS.md`](ops/ACCESSIBILITY_MANUAL_CHECKS.md).

La verificación con lectores de pantalla nativos y dispositivos físicos queda documentada como paso de release; no se marca como ejecutada desde el entorno headless compartido.
