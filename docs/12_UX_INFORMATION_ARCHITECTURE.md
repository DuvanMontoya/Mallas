# 12 — UX e information architecture

## Navegación principal

1. Mi malla / Inicio
2. Planificador y escenarios
3. Historia
4. Oferta
5. Dependencias
6. Auditoría detallada
7. Perfil/preferencias

`/` es el inicio estudiantil y muestra directamente la malla personalizada.
`Resumen` deja de ser un destino separado: sus métricas viven en la franja
contextual de la malla. La especificación completa del rebaseline está en
`docs/42_CURRICULUM_WORKSPACE_SPEC.md`.

## Planificador de escenarios

`/planner` deja claro desde el encabezado que planear no altera la historia
real. El escenario activo, su versión, warnings, auditoría proyectada y
procedencia están visibles en la misma superficie. El usuario puede crear,
duplicar, renombrar, archivar y seleccionar escenarios; compartir está
apagado por defecto y la vista compartida omite matrícula, estudiante,
historial y auditoría personal.

Cada término es una columna derivada del período académico. Una tarjeta se
puede arrastrar con puntero o teclado; el selector «Mover a» es la alternativa
obligatoria para quien no usa drag/drop. Los controles de lock y retiro tienen
nombres accesibles y no dependen sólo del color. Las advertencias muestran
prerrequisitos/correquisitos, oferta, créditos, disponibilidad y conflictos de
horario con el detalle recibido del backend.

La comparación resume cursos añadidos, retirados, movidos y sin cambio. No se
presenta como recomendación automática: es una diferencia entre dos
escenarios versionados.

## Optimización explicable

El panel «Optimiza este escenario» vive debajo de la auditoría proyectada y
mantiene la separación entre propuesta y hechos reales. El usuario inicia una
ejecución, ve si está en cola o corriendo y puede cancelarla. Al terminar, el
panel muestra `OPTIMAL`, `FEASIBLE`, `INFEASIBLE` o `UNKNOWN`, además de la
versión del solver y las huellas de entrada/salida.

Para una solución factible, la comparación se divide en añadidos, movidos y
retirados, y después enumera decisiones y supuestos. Para una solución
infeasible se muestran conflictos; para `UNKNOWN` se explica que no existe una
solución demostrable o que falta evidencia. La interfaz no presenta una ruta
como matrícula aprobada, no muta intentos y conserva el texto de oferta
desconocida como supuesto explícito. El panel es usable con teclado, anuncia
el resultado mediante región viva y conserva una vista de una columna en
móvil.

Roles editoriales obtienen:
10. Fuentes
11. Revisiones
12. Propuestas
13. Publicaciones
14. Analítica

## Franja contextual de Mi malla

La implementación anterior usaba un dashboard separado; P104 lo retira. La
franja superior de `Mi malla` conserva sólo:
- avance total;
- búsqueda;
- modo de presentación;
- período sólo cuando se consulta oferta.

No presentar un «% graduado» engañoso calculado sólo por créditos.

La implementación actual usa `GET /api/v1/academic-overview`; P104 lo integra en
el futuro read model `student-curriculum-workspace`. El drawer y la auditoría
detallada muestran aprobados/aplicados/sin aplicar, progreso por componente y
agrupación, obligatorias faltantes, próximos desbloqueos, cursos elegibles y
bloqueados, requisitos externos, advertencias y `UNKNOWN`. El porcentaje de
créditos se recibe del backend y siempre se acompaña por el estado global de la
auditoría y la explicación de sus límites.

Los estados `NO_HISTORY` e `INCOMPLETE` son visibles y accionables en la malla: el primero
invita a cargar historia sin presentar ceros como progreso; el segundo expone
cada hecho o requisito no verificable. Cursos, agrupaciones, requisitos,
advertencias y evidencia conservan deep links para compartir el contexto sin
copiar reglas al cliente.

## Malla principal

Desktop:
- columnas por layout;
- tarjetas compactas;
- sticky encabezados;
- panel lateral de detalle;
- enfoque contextual.

La malla consume `GET /api/v1/curriculum-map`. El selector de layout conserva
la etiqueta y descripción entregadas por la política de la revisión. Para el
plan 2514, `dependency-depth` muestra niveles derivados de dependencias y
`component-lanes` agrupa por componente/agrupación; ninguno es un semestre
oficial. `suggested-path` y `user-scenario` sólo se presentan como ruta o plan
cuando existe el estado correspondiente del planificador. Si todavía no
existe, la interfaz lo dice explícitamente y muestra el nivel de dependencias
como referencia, sin inventar una recomendación.

La selección de una tarjeta resalta únicamente la asignatura, sus dependencias
directas y sus desbloqueos directos. Las relaciones completas se reservan para
la vista de grafo. Los filtros de componente, agrupación, estado personal,
créditos, oferta y texto son estado de vista: no modifican la elegibilidad
resuelta por el backend.

Mobile:
- lista/roadmap vertical;
- filtros;
- drawer de detalle;
- no miniaturizar 9 columnas.

En móvil las columnas se convierten en un roadmap vertical de una sola columna
y el panel de detalle permanece navegable con teclado; no se reduce la malla
desktop hasta hacer ilegibles las tarjetas.

## Estados visuales

Usar icono + texto/tooltip + patrón/outline; color sólo como señal redundante.

## Panel curso

- metadata;
- estado;
- cuenta para;
- requisito para cursarlo;
- requisito exacto no satisfecho;
- desbloqueos directos;
- desbloqueos indirectos;
- oferta;
- evidencia;
- acciones: agregar a escenario, comparar, abrir grafo.

La ficha de la malla muestra además el nivel de dependencias derivado, la
agrupación a la que cuenta y el estado de oferta del período seleccionado. La
ficha no convierte la posición visual en una regla ni ejecuta el AST en el
navegador.

En la fase de dashboard, el panel de curso ya recibe del read model su
elegibilidad y las razones exactas. Las acciones de escenario, oferta y grafo
se habilitan en sus bounded contexts posteriores; no se simulan localmente.

## Accesibilidad

WCAG 2.2 AA:
- navegación completa por teclado;
- focus visible;
- ARIA correcto;
- contraste;
- reduced motion;
- zoom 200%;
- nombres accesibles para nodos/aristas;
- alternativa textual para grafos.

## Vista de dependencias

`/graph` consume `GET /api/v1/dependency-graph` y vive como una vista propia,
separada de la malla principal. El backend proyecta el AST normativo como un
grafo semántico: los cursos son nodos `COURSE` y las condiciones `ALL`, `ANY`,
umbrales, equivalencias, requisitos externos y `UNKNOWN` son nodos
`CONDITION`. Una condición nunca se reemplaza por una flecha curso→curso que
oculte su lógica.

La vista muestra relaciones directas y, al seleccionar un curso, calcula
ancestros, descendientes, desbloqueos y rutas cortas transitivas. React Flow y
ELK sólo presentan esa proyección; no permiten arrastrar nodos ni editar reglas.
Los filtros son de vista y el panel conserva links a la malla y a la evidencia.
La alternativa textual enumera cursos, entradas y salidas con texto, estados y
acciones de teclado, sin depender de color, posición o canvas. Los ciclos se
exponen como incidencias de gobernanza con su recorrido y severidad.

## Oferta y horarios

`/offerings` es una vista propia para explorar grupos por período. Su primera
jerarquía responde, en este orden, qué término se está consultando, qué fuente
y fecha respaldan el dato, si el grupo está ofertado, si la persona es
elegible y si el horario seleccionado se puede combinar. Los estados de oferta,
elegibilidad y agenda usan texto, icono y borde; nunca sólo color.

Cada tarjeta muestra la frescura (`fresca`, `antigua` o `desconocida`), una
advertencia cuando la capacidad no es tiempo real y las reuniones en una
`ScheduleGrid` legible en móvil. El usuario puede seleccionar grupos para
compararlos; el backend devuelve los conflictos recurrentes exactos y la
interfaz conserva la alternativa textual. La pantalla informa, pero no
inscribe y no convierte una oferta en autorización académica.
