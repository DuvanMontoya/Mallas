# 42 — Curriculum Workspace: especificación de producto y UX

## Estado

Especificación de P100 para implementar `Inicio = Mi malla`. Define
presentación e interacción; no crea reglas académicas ni convierte geometría en
norma.

## 1. Arquitectura de información

### Estudiante autenticado

1. `Mi malla` — inicio y workspace principal.
2. `Planificar` — escenarios y optimización.
3. `Historia` — hechos académicos e importación.
4. `Oferta` — secciones, horarios y conflictos.
5. `Dependencias` — grafo completo como herramienta secundaria.
6. `Auditoría` — explicación exhaustiva, accesible desde el drawer y navegación
   secundaria.

`Resumen` deja de ser un destino. Sus métricas viven en la franja de la malla.
`/` es la URL canónica estudiantil; `/curriculum` redirige conservando `mode`,
`selected`, `q`, `status`, `component`, `group` y `term`.

### Público

La portada pública permite seleccionar institución, sede, facultad, programa,
plan y revisión. Después abre la misma malla sin estado personal.

### Roles editoriales

Mantienen inicio administrativo propio. Una cuenta que también sea estudiante
puede cambiar de espacio explícitamente, sin mezclar navegación editorial y
personal.

## 2. Capas y procedencia

El workspace compone capas que nunca pierden su etiqueta:

| Capa | Autoridad | Contenido |
|---|---|---|
| `SOURCE_TRANSCRIPTION` | archivo archivado | texto, ocurrencias, coordenadas y anotaciones presentes en la pieza |
| `NORMATIVE_OVERLAY` | revisión curricular y requisitos con evidencia | cursos, grupos, créditos, obligatoriedad, requisitos externos reviewables y milestones; cada hecho transporta estado epistemológico, evidencia y vigencia |
| `PERSONAL_OVERLAY` | historia, auditoría, oferta y escenario autorizados | aprobado, en curso, elegible, bloqueado, planeado, progreso y oferta |
| `DEPENDENCY_DERIVED` | proyección determinista del AST | profundidad, dependencias, desbloqueos y rutas |

Una vista puede combinar capas, pero el drawer indica la procedencia de cada
afirmación. El modo `Transcripción de fuente` oculta elementos no presentes en
la pieza seleccionada.

## 3. Estructura del workspace

```text
┌ navegación: Mi malla | Planificar | Historia | Oferta ┐
├ programa · plan · revisión             70 / 141       ┤
├ buscar                         [Mi avance] [Fuente]    ┤
├ estado rápido / Más filtros / período si aplica       ┤
├────────────────────────────────────────────────────────┤
│ columna de fuente 01 │ 02 │ 03 │ ...                  │
│ [curso]              │ [curso] │ [banco]              │
│ [curso]              │ [curso] │ [misma ocurrencia]   │
├────────────────────────────────────────────────────────┤
│ Nivelación de la pieza | requisito externo separado   │
└────────────────────────────────────────────────────────┘
                                      drawer contextual →
```

La barra superior muestra sólo:

- identidad curricular;
- progreso aplicado/total con advertencia de que no equivale a graduación;
- búsqueda;
- modo activo.

Período y oferta aparecen únicamente cuando hay contexto temporal. Los filtros
secundarios viven bajo `Más filtros`.

## 4. Tipos y estados

Cinco ejes independientes:

### Tipo

- `COURSE`;
- `CHOICE_POOL`;
- `FREE_ELECTIVE_POOL`;
- `EXTERNAL_REQUIREMENT`;
- `MILESTONE`;
- `ANNOTATION`.

### Completitud/progreso

- `NOT_ASSESSED`;
- `NOT_STARTED`;
- `IN_PROGRESS`;
- `SATISFIED`;
- `UNKNOWN`.

### Elegibilidad

- `NOT_ASSESSED`;
- `ELIGIBLE`;
- `BLOCKED`;
- `UNKNOWN`;
- `NOT_APPLICABLE`.

### Oferta

- `OFFERED`;
- `NOT_REPORTED`;
- `NOT_OFFERED`;
- `UNKNOWN`;
- `NOT_APPLICABLE`.

### Planificación

- `PLANNED`;
- `NOT_PLANNED`;
- `NOT_APPLICABLE`.

Un curso puede estar simultáneamente `NOT_STARTED`, `ELIGIBLE`, `OFFERED` y
`PLANNED`. El read model conserva todos los ejes. Una política visual derivada
elige una señal primaria sin borrar las demás. El nombre accesible las compone,
por ejemplo: `Probabilidad, curso, no iniciado, elegible, ofertado, planeado,
4 créditos`.

## 5. Ocurrencias y bancos

`LayoutNodeOccurrence` representa una posición. Varias ocurrencias pueden
apuntar al mismo `RequirementGroup`; nunca crean créditos ni requisitos
adicionales.

Una ocurrencia repetida anuncia:
`Otra ubicación visual de Núcleo Estadístico; comparte el mismo progreso`.

El progreso del banco se calcula una vez en backend. Cada representación recibe
el mismo `target_id`, `progress`, `required_credits` y `applied_credits`.

Libre elección es un overlay normativo/personal de 28 créditos para el plan
2514. No se muestra en la transcripción fiel del PDF aportado porque no aparece
en esa pieza.

## 6. Requisito de lengua y nivelación

Se muestran dos regiones independientes:

- `Nivelación mostrada en la pieza`: conserva literalmente Inglés I, II, III y
  VI, sin efecto académico mientras el mapeo sea `UNKNOWN`;
- `Requisito externo de lengua`: llega del motor con cero créditos y su propia
  evidencia. No se denomina B1 `VERIFIED` sin snapshot institucional aplicable.

Ningún curso de nivelación satisface automáticamente el requisito externo.

## 7. Interacción

- hover y focus resaltan dependencias y desbloqueos directos;
- click, Enter o Espacio abren el drawer;
- Escape cierra y devuelve el foco al disparador;
- el drawer modal atrapa foco sólo en móvil; en desktop funciona como panel
  complementario no modal;
- búsqueda centra sin destruir el contexto;
- cambiar de modo conserva selección cuando el target existe y explica cuando
  la capa lo oculta;
- filtros actualizan la URL sin alterar elegibilidad;
- el grafo completo se abre mediante una acción explícita.

## 8. Responsive

### Desktop, >= 1024 px

- composición horizontal de fuente;
- paneo contenido, nunca overflow del documento;
- labels/lane headers sticky;
- drawer lateral de 360–440 px.

### Tablet, 600–1023 px

- dos columnas lógicas cuando quepan;
- detalle en drawer superpuesto;
- acciones secundarias bajo disclosure.

### Móvil, 320–599 px

- índice `Ir a columna/componente`;
- secciones verticales por `source_column` o agrupación del modo activo;
- orden de lectura: columna, y dentro de ella coordenada vertical y orden de
  fuente;
- ocurrencias repetidas permanecen identificadas;
- restauración de foco y scroll al cerrar detalle;
- no depende de hover ni miniaturiza la malla desktop.

## 9. Onboarding no bloqueante

Después de resolver programa/plan/revisión se muestra la malla inmediatamente.
Sin historia, los cursos quedan `NOT_ASSESSED` y un checklist ofrece:

- confirmar datos personales permitidos;
- importar o registrar historia;
- seleccionar período;
- crear escenario;
- abrir tour no modal.

El usuario puede omitir y reanudar cada paso.

## 10. Criterios de comprensión

Prueba moderada o no moderada con estudiantes del universo objetivo:

- >= 90 % identifica el estado de una tarjeta en <= 10 s;
- >= 90 % localiza su faltante principal en <= 20 s;
- >= 90 % abre la causa de bloqueo en <= 30 s;
- 100 % distingue transcripción de fuente, norma y recomendación personal en
  los casos críticos;
- cero participantes interpreta 100 % de créditos como graduación automática;
- cero participantes interpreta una ocurrencia repetida como créditos dobles.

Estos umbrales son criterios de investigación con participantes reales y se
cierran en P108. En P100 se ejecuta un *cognitive walkthrough* basado en roles
de estudiante y asesor para detectar fallas obvias del contrato antes de
implementar; no se presenta ese ejercicio como evidencia humana ni como
cumplimiento estadístico de los umbrales.

## 11. Accesibilidad por fase

- P100: orden de lectura, nombres y flujos de foco en wireframe;
- P103: semántica de layout/ocurrencias y alternativa textual;
- P104: teclado, Escape, retorno de foco, 200/400 %, reduced motion y 320 px;
- P105: lector de pantalla manual para bancos y requisitos externos;
- P108: aceptación WCAG 2.2 AA integral en dispositivo y navegador reales.

## 12. Gate P100

P100 puede cerrar cuando:

- esta especificación y la matriz de evidencia están trazadas desde el roadmap;
- el prototipo interactivo representa desktop y reflow móvil;
- el walkthrough cognitivo basado en roles de estudiante y asesor documenta
  tareas, rutas esperadas, resultados y hallazgos; queda rotulado como
  evaluación experta, no como prueba con participantes;
- el walkthrough de teclado demuestra apertura, Escape, retorno de foco, índice
  móvil y ausencia de overflow documental a 320 CSS px;
- arquitectura, currículo y UX no reportan Critical/High abiertos;
- el scope canónico declara multiprograma;
- ninguna columna se denomina semestre/momento sin evidencia;
- libre elección y requisito de lengua aparecen como overlays independientes.

La validación de los umbrales de §10 con participantes reales es obligatoria
en P108 y no puede sustituirse por personas simuladas.
El zoom real a 400 % se verifica sobre la implementación en P104/P108; P100 no
lo declara ejecutado sobre el wireframe.
