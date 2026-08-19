# Plan de completitud de producto y experiencia curricular

**Fecha:** 2026-08-18  
**Estado:** plan propuesto para ejecución por fases; ninguna fase está terminada.  
**Objetivo:** convertir la implementación actual en una plataforma de navegación
curricular para todos los pregrados incluidos en cada universo institucional de
release, con identidad estudiantil completa, asignación automática de plan y una
malla visual como superficie principal.

## 1. Veredicto ejecutivo

La base técnica no es un prototipo: ya existen currículo versionado, motor de
reglas, auditoría, historia, oferta, planificación y seguridad. Sin embargo, la
experiencia de producto todavía transmite un alcance menor por cuatro fallas
estructurales:

1. sólo existe un currículo normativo real, por lo que la capacidad
   multiprograma es arquitectónica pero no visible ni operable a escala;
2. el alta de estudiante modela la identidad como un `display_name`, omite fecha
   de nacimiento y obliga a seleccionar manualmente detalles curriculares que el
   sistema debería resolver;
3. el inicio estudiantil resume decisiones, pero la malla no ocupa todavía el
   centro de la experiencia;
4. la malla actual ordena principalmente por profundidad de prerrequisitos y
   separa bancos de elección, en vez de poder conservar una composición visual
   de fuente y enriquecerla con capas personales claramente diferenciadas.

La corrección no consiste en añadir más texto ni más pantallas. El núcleo debe
ser una malla visual, personal y explicable; los detalles extensos viven en
paneles contextuales.

## 2. Evidencia y lectura del PDF aportado

El PDF `Mallas-Curriculares-Pregrado-Estadistica.pdf` es una referencia aportada
por el usuario, de una sola página, 1920x1080, sin etiquetas explícitas de
semestre. Su SHA-256 observado es
`dfa8d192635817d2c103bef6ec9a05fa26519428d023f1a49eed9a18d4b67e55`.
Todavía no está archivado en el sistema de fuentes ni tiene URL, fecha de
captura o procedencia verificadas; por tanto se clasifica
`USER_PROVIDED_REFERENCE`, no como publicación oficial ni norma vigente.

Consecuencias de diseño:

- la geometría y los textos son evidencia verificable de lo que contiene el
  archivo aportado, no de su oficialidad, vigencia o aplicabilidad normativa;
- la posición horizontal no demuestra por sí sola un semestre normativo;
- tarjetas como `Núcleo Estadístico`, `Aplicación estadística` o
  `Complementación estadística` parecen rótulos de agrupación y tienen varias
  ocurrencias visuales; su semántica exacta permanece por verificar;
- `Inglés I`, `Inglés II`, `Inglés III` y la tarjeta rotulada `Inglés VI` deben
  conservarse como transcripción `VERIFIED` respecto del archivo; su mapeo a
  cursos, requisito o posible errata permanece `UNKNOWN`;
- el PDF no muestra libre elección ni expresa B1. Esos datos proceden de otras
  fuentes y sólo pueden añadirse como overlays con evidencia propia;
- los 28 créditos de libre elección sí están verificados por el Acuerdo 496,
  pero el catálogo exhaustivo y la oferta por período son dominios separados;
- el requisito de lengua extranjera se mostrará con su estado epistemológico
  real. Sólo se denominará B1 verificado cuando exista un snapshot institucional
  archivado y aplicable a la cohorte/revisión.

## 3. Producto objetivo

### 3.1 Alcance

La arquitectura soportará cualquier pregrado que tenga:

- institución, sede, facultad y programa;
- uno o más planes;
- revisiones temporales del plan;
- fuentes oficiales archivadas;
- reglas y grupos validados;
- una o más composiciones visuales versionadas.

Cada campaña de incorporación define un universo cerrado desde un inventario
oficial de institución, sedes y programas. “Todos los pregrados” significa
todos los programas oficialmente listados dentro de ese universo, no sólo los
que ya tienen datos convenientes. Un release parcial se rotula como piloto o
cobertura parcial y nunca como cobertura completa.

Estadística 2514 seguirá siendo el primer currículo real completo, pero no habrá
copy, rutas, defaults, fixtures de producción ni decisiones de dominio que
supongan que es el único programa.

### 3.2 Promesa al estudiante

Al entrar, el estudiante debe ver su malla completa. Los objetivos de
comprensión se validan como tareas separadas, no como una lista simultánea:

- identificar el estado principal de una tarjeta en 10 segundos;
- localizar el faltante principal en 20 segundos;
- abrir la causa de un bloqueo en 30 segundos;
- reconocer lo aprobado, en curso, elegible, bloqueado y planeado;
- cuánto ha completado en cada componente y banco;
- qué cursos o requisitos desbloquea una tarjeta;
- qué requisito no crediticio le falta;
- qué información sigue sin verificarse.

## 4. Identidad y alta de estudiante

### 4.1 Datos canónicos

Separar autenticación, identidad personal e identidad académica.

`User` conserva acceso y seguridad:

- correo;
- contraseña/IdP;
- estado de verificación;
- roles.

Crear `PersonProfile` uno-a-uno con `User` para identidad personal, sin
sobrecargar `StudentProfile`, que seguirá siendo identidad académica. Conserva:

- primer nombre;
- segundo nombre y otros nombres, opcional;
- primer apellido;
- segundo apellido, opcional;
- nombre preferido, opcional;
- fecha de nacimiento, sólo cuando exista propósito institucional y política de
  minimización/retención que la justifiquen;
- nombre de visualización derivado y normalizado;
- metadatos de procedencia y última verificación.

No persistir `edad`: cambia con el tiempo. Se calcula desde `fecha_de_nacimiento`
en la zona horaria institucional y sólo se expone a roles autorizados cuando sea
necesario. La fecha de nacimiento es PII y requiere propósito, control de acceso,
auditoría y política de retención.

`StudentProfile` conserva identidad académica:

- institución;
- número estudiantil;
- estado del perfil;
- canales/preferencias pertinentes.

`ProgramEnrollment` conserva la vinculación curricular:

- programa;
- plan;
- revisión base;
- período/fecha de admisión;
- cohorte;
- estado;
- causa y evidencia si requiere revisión.

### 4.2 Flujo administrativo

El formulario se convierte en un flujo guiado:

1. **Persona:** nombres y apellidos separados, fecha de nacimiento y nombre
   preferido opcional.
2. **Acceso:** correo, método de activación y rol estudiantil.
3. **Identidad académica:** institución y número estudiantil.
4. **Pregrado:** sede, facultad y programa mediante selectores dependientes.
5. **Ingreso:** período o fecha de admisión.
6. **Resolución automática:** el backend determina plan y revisión aplicable.
7. **Confirmación:** resumen legible del programa, plan, revisión, créditos y
   fuente; creación atómica.

El operador no elige normalmente una revisión. Si hay cero o varias revisiones
aplicables, el alta queda `NEEDS_REVIEW`. Un override exige permiso, evidencia,
justificación y evento de auditoría.

### 4.3 Onboarding del estudiante

La primera sesión ofrece un checklist reanudable, sin duplicar el alta
administrativa ni bloquear la malla cuando la asignación ya está resuelta:

- confirmación de nombre preferido y datos permitidos;
- explicación visual del programa y revisión asignados;
- carga/importación o registro guiado de historia, opcional para entrar y
  necesaria sólo para personalizar estados;
- elección de período actual;
- preferencias iniciales de planificación;
- recorrido interactivo no modal de la leyenda, omitible y reutilizable.

## 5. Selección automática de currículo

Crear un servicio de aplicación único `CurriculumAssignmentService`:

- recibe institución, programa y fecha/período de admisión;
- valida el scope institución-sede-facultad-programa;
- obtiene el plan elegible mediante una `CurriculumAssignmentPolicy`
  versionada: scope, rango temporal/cohorte, condiciones de transición o
  reingreso, prioridad, evidencia, estado epistemológico y hash;
- resuelve exactamente una revisión cuya vigencia cubra el ingreso;
- devuelve `RESOLVED`, `NEEDS_REVIEW` o `UNKNOWN`, nunca la primera fila por
  ordenamiento;
- conserva el conjunto de candidatos, razón, fuentes y huellas usadas;
- es idempotente y testeable sin depender del formulario;
- es la única ruta usada por alta administrativa, onboarding, importaciones y
  futuras integraciones.

Sólo políticas `VERIFIED` y revisiones publicadas o históricas inmutables
(`PUBLISHED`/`SUPERSEDED`, y `RETIRED` únicamente cuando la política lo permita)
pueden producir `RESOLVED`. `DRAFT`, `IN_REVIEW` y solapamientos sin regla única
producen `NEEDS_REVIEW`/`UNKNOWN`.

La elección del pregrado debe cambiar de inmediato el catálogo visible. La
malla personal sólo se habilita cuando existe una revisión resuelta; antes se
puede abrir la malla pública con una advertencia clara.

## 6. Modelo de composición visual

Implementar `CurriculumLayout` separado de `CurriculumRevision` y limitado a
plantillas públicas/versionadas:

- revisión curricular a la que presenta;
- clase: `SOURCE_FAITHFUL_LAYOUT` o `DEPENDENCY_DERIVED_LAYOUT`;
- versión, estado, locale y viewport de referencia;
- fuente/evidencia y estado epistemológico;
- ciclo de vida, hash, supersession e inmutabilidad propios;
- etiqueta pública que indique si es transcripción de fuente o derivada;
- nodos y posiciones versionados.

`PlanScenario` sigue siendo privado y pertenece a planning. `Mi escenario` se
renderiza como overlay sobre una plantilla pública; nunca se publica ni se
persiste como `CurriculumLayout`.

El read model compuesto `WorkspaceNode` admite:

- `COURSE`: asignatura concreta;
- `CHOICE_POOL`: agrupación optativa;
- `FREE_ELECTIVE_POOL`: libre elección;
- `EXTERNAL_REQUIREMENT`: requisito de lengua u otro requisito no crediticio;
- `MILESTONE`: práctica, trabajo de grado u otro hito;
- `ANNOTATION`: rótulo visual respaldado por fuente.

Un `SOURCE_FAITHFUL_LAYOUT` sólo contiene las ocurrencias presentes en su
fuente. Los tipos ausentes, como libre elección en este PDF, pueden aparecer en
el `WorkspaceNode` del overlay personal sin mutar la transcripción.

Separar `LayoutNodeOccurrence` de su objetivo curricular. Varias ocurrencias
pueden apuntar al mismo grupo sin crear requisitos ni progreso duplicados. Los
targets usan FKs tipadas nullable y un `CHECK` de exactamente un objetivo
compatible por tipo; además validan pertenencia a la misma revisión. No usar
`GenericForeignKey` sin integridad de base de datos.

Cada ocurrencia conserva coordenadas normalizadas, orden, tamaño y lane, pero la
geometría no entra al motor académico. `slot_count`, créditos por ocurrencia y
semestre permanecen `UNKNOWN` salvo evidencia específica.

Para el PDF aportado se crea, sólo después de archivarlo y revisar su
procedencia, un `SOURCE_FAITHFUL_LAYOUT` que reproduzca únicamente su jerarquía,
texto, ocurrencias, proporción y secuencia. Las columnas quedan sin título
público; internamente se identifican `source_column_01...N`. Libre elección,
requisito de lengua, progreso, oferta y planificación son overlays con
procedencia independiente. La vista personal por períodos se deriva del
planificador y sí usa nombres de períodos reales.

## 7. La malla como pantalla principal

### 7.1 Inicio autenticado

La nueva arquitectura de información estudiantil define `Inicio = Mi malla`.
`/` carga la malla personal y `/curriculum` redirige a la URL canónica
conservando filtros/deep links. El destino `Resumen` desaparece de la navegación
principal; sus indicadores pasan a la franja contextual. Roles editoriales
mantienen su inicio administrativo separado.

Encima de la malla aparece una barra de divulgación progresiva:

- programa, plan y revisión;
- progreso crediticio aplicado/total;
- búsqueda siempre visible;
- período sólo cuando se consulta oferta;
- filtros secundarios bajo `Más filtros`;
- historia y planificación en navegación contextual.

La auditoría completa, evidencia y analítica quedan disponibles en paneles o
rutas secundarias, no compiten con la malla en el primer viewport.

### 7.2 Tarjeta visual

Cada tarjeta muestra el estado primario y máximo dos señales secundarias:

- nombre y código;
- créditos o `sin créditos`;
- estado con icono, texto corto, borde y patrón;
- hasta dos de: obligatoriedad/banco, oferta o progreso. El resto vive en el
  drawer.

Definir tres ejes ortogonales, combinados en el nombre accesible:

- tipo: curso, banco, libre elección, requisito externo o milestone;
- progreso: no iniciado, en curso, satisfecho, bloqueado, elegible, por
  verificar o no evaluado;
- oferta/planificación: ofertado, planeado, no reportado o no aplicable.

El color es redundante. Aprobado puede tener check y textura tenue; en curso,
anillo/progreso; planeado, marcador de calendario; bloqueado, candado; unknown,
signo de interrogación y borde discontinuo.

### 7.3 Interacción

- hover/focus: resalta requisitos directos y desbloqueos directos;
- click/tap: abre drawer con explicación, evidencia, oferta y acciones;
- doble acción explícita, no doble click: abrir grafo completo;
- filtros rápidos por estado, componente, banco, créditos y oferta;
- selector de período para cambiar oferta sin cambiar elegibilidad;
- modos `Transcripción de fuente`, `Mi avance`, `Mi escenario` y
  `Dependencias`, cada uno con procedencia visible;
- ningún modo dibuja todas las flechas simultáneamente;
- búsqueda centra el nodo sin ocultar su columna ni banco.

### 7.4 Bancos de elección y libre elección

Cuando una fuente y la revisión vinculen un rótulo a una agrupación, sus
ocurrencias visuales apuntan al mismo banco. El progreso se calcula una vez y se
presenta como agregado compartido, no como obligación repetida. El overlay
personal muestra:

- créditos exigidos, aplicados y restantes;
- cursos elegidos/aprobados/en curso/planeados;
- cantidad de opciones elegibles y ofertadas;
- acción `Explorar opciones` que abre un drawer filtrado;
- advertencia si el catálogo es temporal o incompleto.

Libre elección aparece en `Mi avance` con `28 créditos requeridos`, pero no en
la transcripción fiel de este PDF porque la pieza no la contiene. Dentro
del bloque sólo se muestran selecciones reales del estudiante y una acción para
explorar catálogo/oferta autorizados. No se presupone que cualquier curso
cuenta: el backend conserva la política de aplicación y el ledger sin doble
conteo.

### 7.5 Inglés y otros requisitos externos

Mantener dos lanes o capas independientes:

- `Nivelación mostrada en la pieza visual`, sin efecto académico hasta que su
  mapeo esté verificado;
- `Requisitos externos de grado`, recibidos del motor con evidencia y estado
  epistemológico propios;
- sólo muestra B1 como verificado cuando exista snapshot aplicable;
- distingue `curso de nivelación`, `prueba`, `exención` y `requisito cumplido`;
- no suma esos nodos al progreso de 141 créditos.

`source_label = "Inglés VI"` es `VERIFIED` respecto del archivo aportado;
`normalized_requirement/course_mapping = null` permanece `UNKNOWN`; la hipótesis
`Inglés IV` sólo puede existir como propuesta `INFERRED_PENDING_REVIEW`.

### 7.6 Responsive

Desktop conserva la composición horizontal y permite paneo contenido con
encabezados/lane labels sticky. Tablet reduce densidad y abre detalle en drawer.
Móvil transforma columnas en secciones por `source_column` o agrupación del modo
activo, conserva el orden de lectura y marca ocurrencias repetidas del mismo
banco. Incluye índice `Ir a columna/componente`, encabezados sticky, retorno de
foco y restauración de scroll al cerrar el drawer. Se prueba a 320 px, zoom
200/400 %, ambas orientaciones y táctil sin depender de hover.

## 8. De un programa a todos los pregrados

### 8.1 Catálogo público

Añadir una portada pública neutral:

- buscar institución, sede, facultad y pregrado;
- distinguir programas `DISPONIBLE`, `EN VALIDACIÓN`, `SIN FUENTE` y
  `DESACTUALIZADO`;
- explorar la revisión vigente o histórica sin cuenta;
- no mostrar programas sintéticos como oferta real.

### 8.2 Fábrica de incorporación curricular

Cada pregrado pasa por el mismo pipeline:

1. descubrir y registrar fuentes oficiales;
2. archivar bytes y SHA-256;
3. extraer candidatos sin autoridad;
4. validar identidad, créditos, grupos y reglas;
5. construir golden cases;
6. crear layout visual con evidencia;
7. revisión curricular humana;
8. publicar revisión inmutable;
9. ejecutar smoke público, alta y malla personal;
10. activar el programa en el catálogo.

La expansión se hace mediante `CoverageCampaign`: inventario oficial cerrado,
snapshot/hash, institución, sedes, fecha de corte y programas esperados. Se
ejecuta por lotes de facultad/sede con matriz pública. Un programa sin evidencia
permanece `SIN_FUENTE`/`EN_VALIDACIÓN` y bloquea la declaración de cobertura
completa del universo, aunque no se publiquen reglas inventadas.

### 8.3 Neutralidad de producto

Eliminar del producto cualquier supuesto de Estadística:

- títulos y breadcrumbs hardcoded;
- plan 2514 como default global;
- componentes o colores específicos sin configuración;
- fixtures de producción usados como catálogo;
- layouts ubicados por `plan_code` en archivos locales no versionados por el
  modelo;
- textos que afirmen 141 créditos fuera del read model de la revisión.

## 9. Cambios de API, datos y migración

### 9.1 Backend

- migración de identidad estructurada, con backfill conservador desde
  `display_name` a `legacy_display_name`; no dividir nombres automáticamente;
- campos nuevos quedan `UNKNOWN`/vacíos hasta confirmación humana;
- endpoint de alta v2 con DTOs separados de persona, acceso e inscripción;
- endpoint de resolución curricular y preview antes de crear;
- CRUD/versionado/publicación de layouts con evidencia;
- read model `student-curriculum-workspace` que compone layout, auditoría,
  historia, oferta y escenario sin ejecutar reglas en frontend;
- catálogo público de programas y cobertura;
- OpenAPI regenerado y política de compatibilidad/deprecación para v1.

### 9.2 Frontend

- wizard administrativo y onboarding estudiantil;
- componente `CurriculumWorkspace` como superficie principal;
- renderer de nodos por tipo, no un renderer sólo de cursos;
- drawer único de contexto y acciones;
- modos de vista respaldados por layouts reales;
- estado de URL para período, modo, filtros y selección;
- virtualización sólo si el perfil de programas grandes lo exige.

### 9.3 Migración de datos

- no mutar revisiones `PUBLISHED`;
- archivar primero el PDF aportado con procedencia autorizada y después importar
  una transcripción fiel como artefacto nuevo relacionado;
- conservar el layout derivado actual como `DEPENDENCY_DERIVED`;
- no partir nombres existentes por heurística: pedir confirmación o importación
  autorizada;
- recalcular read models y caches sin recalcular reglas en el cliente;
- plan de rollback de migración y prueba de restauración.

## 10. Plan de ejecución y gates

### P100 — Rebaselining de producto y criterios visuales

- convertir este documento en requisitos y journeys trazables;
- inventario de hardcodes de Estadística/2514;
- especificación visual y de estados con wireframes desktop/tablet/móvil;
- matriz de evidencia del PDF.
- nueva IA `Inicio = Mi malla`, capas de procedencia, taxonomía de cinco ejes y
  algoritmo responsive;
- wireframes con orden de foco, teclado, zoom, reduced motion y nombres
  accesibles desde el inicio;
- criterios y umbrales de comprensión para validar con participantes reales en
  P108; P100 usa walkthrough cognitivo basado en roles sin presentarlo como
  investigación humana.

**Gate:** prototipo navegable sometido a walkthrough basado en roles de
estudiante y asesor, y validado por UX reviewer y curriculum auditor; ninguna
posición se presenta como semestre oficial sin evidencia. La validación humana
con estudiantes y asesores permanece obligatoria en P108.

### P101 — Identidad estructurada y privacidad

- modelo, migración segura, administración, API y tests;
- ADR de `PersonProfile` 1:1 con `User`, ownership y acceso campo a campo;
- fecha de nacimiento protegida y edad derivada;
- búsqueda por campos normalizados y nombre completo derivado;
- actualización/rectificación auditable.

**Gate:** migración reversible, sin pérdida de `display_name`, IDOR/privacy
tests, audit log y export/delete policy actualizados.

### P102 — Resolución automática y onboarding

- `CurriculumAssignmentService`;
- `CurriculumAssignmentPolicy` versionada, evidenciada y testeada para planes,
  reingresos y transiciones;
- wizard de alta y preview;
- onboarding de primera sesión;
- manejo de cero/múltiples revisiones.

**Gate:** elegir pregrado + ingreso asigna exactamente el plan correcto o
`NEEDS_REVIEW`; nunca elige silenciosamente la primera revisión.

### P103 — Layout curricular versionado

- modelos, migraciones, governance, evidencia e inmutabilidad;
- archivado/procedencia autorizada e importer de transcripción fiel;
- ocurrencias separadas de targets, FKs tipadas y constraints de scope;
- soporte semántico/accesible para todos los tipos de nodo y capas;
- preservación del layout derivado actual.

**Gate:** round-trip exacto, layout publicado inmutable, ocurrencias repetidas
sin duplicar créditos/requisitos, screenshot golden, orden lógico accesible y
curriculum auditor sin hallazgos Critical/High.

### P104 — Workspace visual base

- `/` centrado en la malla;
- renderer visual, resumen compacto, estados y drawer;
- hover/focus contextual, filtros y modos;
- desktop/tablet/móvil/impresión;
- renderers honestos para curso, banco, libre elección, requisito externo y
  milestone, aunque los exploradores avanzados lleguen en P105;
- teclado, foco, Escape, retorno de foco, zoom, reduced motion y nombres
  accesibles como gate de esta fase.

**Gate:** `Inicio = Mi malla`, todos los tipos estructurales son navegables y no
hay un dashboard competidor; no se declara todavía completo “qué falta” hasta
cerrar P105.

### P105 — Experiencia curricular completa

- bancos con progreso y selecciones reales;
- explorador de opciones conectado a oferta/planificador;
- transcripción de nivelación separada de requisitos externos;
- resolución de cualquier mapeo de inglés sólo con fuente normativa o catálogo
  institucional archivado;
- normalización gobernada del estado raw no constitucional
  `VERIFIED_AT_INSTITUTION_LEVEL` a un estado permitido, sin mutar una revisión
  publicada ni elevar B1 antes de archivar su evidencia;
- pruebas de lector de pantalla para bancos y requisitos externos.

**Gate:** los journeys “dónde estoy”, “qué falta”, “qué puedo cursar” y “qué
abre esto” se completan desde la malla; suma exacta, cero doble conteo, requisito
de lengua fuera de 141 créditos, estado epistemológico visible y golden 2514.

### P106 — Operación multiprograma real

- catálogo público neutral;
- herramientas de incorporación masiva y cobertura;
- publicar al menos un segundo pregrado sólo con fuentes archivadas y revisión
  humana;
- aislamiento institución/programa/layout/oferta/historia.

**Gate:** dos programas reales recorren alta, asignación, malla, auditoría,
historia y planificación con el mismo motor y sin ramas por código. Este gate
demuestra genericidad, no cobertura total.

### P107 — Cobertura de todos los pregrados del universo de release

- crear y aprobar `CoverageCampaign` desde inventario oficial archivado;
- ejecutar la fábrica por todos los programas de la institución/sedes incluidas;
- publicar sólo revisiones verificadas y conservar estados explícitos para los
  bloqueados por fuente o revisión;
- no anunciar cobertura completa mientras un programa del inventario no esté
  `DISPONIBLE`.

**Gate:** 100 % de programas del universo cerrado tienen currículo publicado y
malla aceptada; cualquier excepción reduce el release a piloto/cobertura parcial.

### P108 — Pulido integral y aceptación

- investigación con estudiantes;
- pruebas cognitivas, teclado, lector de pantalla, zoom y dispositivo físico;
- rendimiento con planes grandes;
- estados vacíos/error/offline/fuente vencida;
- telemetría de éxito sin exponer historia académica.

**Gate:** criterios WCAG 2.2 AA, presupuestos de rendimiento, E2E por rol y
programa, y cero hallazgos Critical/High de arquitectura, código, currículo,
seguridad y UX.

### P109 — Release production-like

- PostgreSQL, migraciones desde limpio y desde datos actuales;
- imágenes, Compose, carga, backup/restore y rollback;
- OpenAPI/cliente, SAST, dependencias y observabilidad;
- piloto controlado por facultad antes de apertura general.

**Gate:** se repite la auditoría completa P24/P25 después de P108 y todos los
production gates se ejecutan en el mismo commit; no se usa evidencia histórica
para declarar `READY`.

## 11. Estrategia de pruebas

- unitarias: nombres derivados, edad, resolución temporal, tipos de nodo;
- propiedades: determinismo, no doble conteo, layout no altera auditoría;
- migraciones: perfiles legacy, reversibilidad y published immutability;
- contrato: OpenAPI y cliente generado;
- golden curricular: 2514 completo, libre elección y requisito de lengua con su
  estado epistemológico real;
- integración: alta -> asignación -> historia -> malla;
- E2E: anónimo, estudiante nuevo, estudiante avanzado, admin y asesor;
- visual regression: transcripción fiel y overlays desktop, tablet, móvil e
  impresión;
- accesibilidad: axe + teclado + lector de pantalla manual;
- seguridad: PII, roles, enumeración, IDOR/BOLA, exports y audit log;
- rendimiento: primer render, selección de tarjeta, filtro y drawer en planes
  grandes.

## 12. Métricas de éxito

- porcentaje de altas resueltas sin intervención y porcentaje `NEEDS_REVIEW`;
- tiempo hasta identificar siguiente acción desde login;
- tasa de estudiantes que entienden aprobado/en curso/elegible/bloqueado en una
  prueba sin ayuda;
- tiempo para localizar un requisito y su evidencia;
- porcentaje de mallas publicadas con layout de fuente verificado;
- cobertura de pregrados por sede/facultad y frescura de fuentes;
- errores de asignación curricular: objetivo cero;
- discrepancias de auditoría y doble conteo: objetivo cero;
- éxito de journeys críticos por teclado y móvil.

## 13. Decisiones que no deben resolverse por intuición

- si las columnas del PDF son semestres normativos;
- si `Inglés VI` debe ser `Inglés IV`;
- política normativa de aplicación a libre elección, catálogo candidato y
  oferta efectiva por período, tratados por separado;
- qué revisión aplica cuando rangos temporales se solapan o faltan;
- qué otros datos personales son necesarios además de los solicitados;
- cuál es el universo institucional cerrado de la primera `CoverageCampaign`.

Hasta obtener evidencia, estos casos permanecen `UNKNOWN` o
`INFERRED_PENDING_REVIEW` y la UI lo comunica sin bloquear la exploración
pública que sí tenga respaldo.

## 14. Orden exacto de inicio

1. Aprobar este rebaselining y cerrar las decisiones abiertas del PDF.
2. Diseñar y validar el wireframe de la malla principal.
3. Implementar P101 y P102 antes de depender de perfiles nuevos.
4. Implementar P103 antes de rediseñar definitivamente el renderer.
5. Implementar P104 y P105 como un flujo vertical completo.
6. Incorporar un segundo programa real mediante P106.
7. Completar el universo de release en P107.
8. Ejecutar P108 y P109 sin reducir gates.
