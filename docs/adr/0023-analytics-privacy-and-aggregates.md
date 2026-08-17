# ADR-0023 — Analítica derivada, agregada y con celdas pequeñas

- Estado: aceptado
- Fecha: 2026-08-16
- Área: analytics, privacy, security

## Contexto

El producto necesita mostrar avance estudiantil, tendencias, cuellos de botella, demanda potencial y vistas institucionales. La base contiene historia académica individual, escenarios privados y resultados de auditoría reproducibles. Una analítica que copie filas individuales o mezcle predicciones opacas rompería minimización, autorización y trazabilidad.

## Decisión

1. Las métricas estudiantiles se derivan de `DegreeAuditResult` y `DegreeAuditRun` persistidos sobre revisiones `PUBLISHED`. Una lectura no recalcula ni persiste auditorías.
2. Las métricas institucionales se sirven únicamente a `ANALYST`/`ADMIN` con alcance explícito de institución y, opcionalmente, programa. Se calcula en memoria sobre agregados de estudiantes distintos y no se devuelve ningún identificador individual.
3. El umbral de celda se configura con `ANALYTICS_MIN_CELL_SIZE` y tiene mínimo operativo 2; el valor de despliegue predeterminado es 5. Una celda menor devuelve `count=null`, `cell_status=SUPPRESSED`; una población completa menor al umbral no recibe desgloses.
4. Las exportaciones sólo contienen el mismo conjunto agregado que la consulta, en JSON o CSV. Cada exportación queda en `AuditEvent`; el CSV usa `Content-Disposition`, `Cache-Control: no-store` y `X-Content-Type-Options: nosniff`.
5. Los catálogos de definiciones acompañan tanto a la API como a la UI. Cada métrica declara fuente, estado epistemológico y caveat. No se implementa scoring individual de riesgo ni predicción de fracaso.
6. Las rutas frecuentes usan HMAC con una clave de servidor y no exponen matrícula/estudiante; la clave se configura separadamente con `ANALYTICS_PSEUDONYMIZATION_KEY` y en ausencia hereda la clave secreta de Django.

## Alternativas descartadas

- Exportar filas por estudiante con pseudónimo: permite reidentificación por combinación de curso, período y cohorte; queda fuera de esta primera capacidad.
- Entrenar un modelo de riesgo: no existe gobernanza, consentimiento ni evidencia de que una predicción sea normativa; además, no es necesaria para responder las preguntas de navegación curricular.
- Construir métricas desde el frontend: duplicaría reglas y rompería el contrato de que el backend es la única autoridad académica.

## Consecuencias

- Los datos de baja frecuencia pueden aparecer como `SUPPRESSED`, incluso a usuarios con rol autorizado; es una garantía deliberada.
- El tiempo oficial a grado permanece `UNKNOWN` hasta que exista una fuente normativa/administrativa de fecha de grado. La plataforma sólo muestra duración observada derivada de términos académicos.
- La exportación institucional está diseñada para análisis agregado; cualquier necesidad de cohortes individuales requiere una nueva decisión de gobernanza, threat review y contrato explícito.
