# 22 — Analítica

## Estudiante

- créditos/requisitos restantes;
- evolución de avance;
- cursos críticos;
- bloqueos;
- escenarios comparados.

## Institucional

Sólo datos autorizados/agregados:
- distribución de avance;
- cursos cuello de botella;
- demanda potencial por período;
- rutas frecuentes;
- tiempo a grado;
- requisitos con mayor rezago.

No construir «predicciones de fracaso» opacas ni perfiles sensibles sin gobernanza específica.

## Eventos

Product analytics con IDs seudónimos y minimización de datos.

## Fuente

Distinguir métrica calculada de dato oficial.

## Implementación verificable

La API expone cuatro operaciones de lectura/exportación:

- `GET /api/v1/analytics/definitions`: catálogo público de definiciones, fuente y estado epistemológico.
- `GET /api/v1/analytics/student`: métricas privadas del estudiante autenticado, o de una matrícula que el estudiante, asesor autorizado o administrador pueda consultar.
- `GET /api/v1/analytics/institutional`: vista agregada para roles `ANALYST` o `ADMIN` con alcance institucional/programa explícito.
- `GET /api/v1/analytics/institutional/export?format=json|csv`: exportación agregada; cada uso crea un `AuditEvent` con alcance, formato y umbral de celda.

La vista estudiantil usa exclusivamente el último `DegreeAuditResult` persistido que corresponde a una `CurriculumRevision` `PUBLISHED`. Si no existe, responde `NO_PERSISTED_PUBLISHED_AUDIT`; no ejecuta una auditoría ni crea datos como efecto lateral de una lectura. Las series históricas se forman con los `DegreeAuditRun` persistidos, de más antiguo a más reciente, e incluyen fecha de corte, versión del motor, hash de resultado y cantidad de `UNKNOWN`.

El catálogo de métricas que devuelve la API es la fuente funcional de definiciones. En particular:

| Métrica | Derivación | Estado | Caveat |
| --- | --- | --- | --- |
| `credits.applied` | `DegreeAuditResult.payload.overall.applied_credits` | `DERIVED` | No equivale a créditos aprobados ni certifica grado. |
| `credits.progress_percent` | créditos aplicados / requeridos, truncado a entero | `DERIVED` | Se limita a 0–100 para presentación. |
| `requirements.remaining` | requisitos cuyo resultado no es `SATISFIED` ni `NOT_APPLICABLE` | `DERIVED` | `UNKNOWN` permanece visible y no se convierte en falso. |
| `courses.bottleneck` | curso propietario de requisitos `UNSATISFIED` o `UNKNOWN` | `DERIVED` | No es una predicción de fracaso. |
| `demand.potential` | unión de estudiantes distintos con curso planeado y/o elegible | `DERIVED` | No confirma oferta ni matrícula; la elegibilidad sin período se etiqueta `NO_TERM_ASSIGNED`. |
| `time_to_degree.observed` | términos entre admisión y último término con intento en matrículas `COMPLETED` | `DERIVED` | La fecha oficial de grado es `UNKNOWN` porque no existe ese hecho en el modelo. |

La vista institucional no devuelve nombre, correo, número de estudiante, UUID de matrícula ni filas individuales. Los conteos se calculan sobre estudiantes/matrículas distintas dentro del alcance solicitado. El umbral mínimo por defecto es `ANALYTICS_MIN_CELL_SIZE=5` y el cliente no puede reducirlo; toda celda inferior queda con `cell_status=SUPPRESSED` y `count=null`. Si la población completa queda bajo el umbral, se omiten todos los desgloses.

Los `route_key` de rutas frecuentes son HMAC truncados con `ANALYTICS_PSEUDONYMIZATION_KEY`; las secuencias sólo se muestran cuando la celda supera el umbral. Los agregados institucionales no producen perfiles individuales, scoring de riesgo, clasificación sensible ni inferencias de éxito/fracaso. El frontend muestra definiciones, fecha de corte, estado `UNKNOWN` y las advertencias metodológicas junto a los valores.

El endpoint institucional exige alcance explícito. Una asignación de analista limitada a programa no puede consultar toda la institución omitiendo `program_id`; una asignación institucional sí puede consultar programas de la institución. Los roles `REVIEWER` no adquieren acceso analítico automáticamente: su permiso editorial no se interpreta como permiso de explotación de datos.
