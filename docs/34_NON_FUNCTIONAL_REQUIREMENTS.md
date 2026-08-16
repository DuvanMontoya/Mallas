# 34 — Requisitos no funcionales

## Confiabilidad académica
- 100% de reglas publicadas con evidencia.
- auditoría reproducible por revisión + snapshot de historia.
- ningún `UNKNOWN` se convierte implícitamente en `false` o `true`.

## Disponibilidad y degradación
- lectura de malla/auditoría debe poder seguir funcionando si el servicio de optimización o notificaciones falla;
- fallos de fuentes externas no destruyen el último snapshot verificado;
- operaciones idempotentes donde se reintentan imports/publicaciones.

## Rendimiento objetivo inicial
Los presupuestos exactos se fijarán tras medir infraestructura, pero CI debe contener pruebas que eviten regresiones claras. La malla y auditoría deben sentirse inmediatas en datasets de tamaño universitario; el optimizador debe tener timeout y devolver solución incumbente/diagnóstico cuando corresponda.

## Accesibilidad
WCAG 2.2 AA, teclado completo, lectores de pantalla, contraste y no depender sólo de color.

## Compatibilidad
Desktop y móvil modernos. Progressive enhancement donde aplique.

## Mantenibilidad
- typechecks y tests obligatorios;
- OpenAPI generado;
- decisiones registradas en ADR;
- dependencias actualizadas por proceso controlado.
