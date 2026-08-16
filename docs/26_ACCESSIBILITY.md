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
