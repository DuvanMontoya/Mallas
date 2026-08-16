# Compatibilidad de configuración codex

Las páginas oficiales actuales muestran sintaxis `permission` para la línea V1 y documentación separada V2 donde cambia a una lista `permissions` y nombres de acciones distintos.

Por eso:

1. antes de iniciar, ejecute `codex --version`;
2. consulte documentación oficial de esa versión;
3. valide `codex.json`;
4. si está en V2, migre la configuración mediante un cambio dedicado y documentado;
5. no mezcle V1 y V2 silenciosamente.

El contenido semántico que debe conservarse:
- lectura permitida;
- edición permitida para build;
- reviewers sin edición;
- `git push` denegado;
- acciones destructivas requieren aprobación;
- skills permitidas;
- subagentes permitidos;
- web permitido donde se requiera verificación documental.
