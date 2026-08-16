# AGENTS.md — Constitución del proyecto

## 0. Mandato

Construyes un **producto completo de producción**, no un MVP, demo, proof of concept ni prototipo. El objetivo es una plataforma confiable de navegación curricular, auditoría de grado, planificación y optimización académica.

La primera implementación cubre Estadística de la Universidad Nacional de Colombia, Sede Bogotá, plan 2514; la arquitectura debe admitir más programas, planes, sedes e instituciones sin reescribir el motor.

No reduzcas el alcance para «entregar rápido». Avanza en orden de dependencias, pero conserva y ejecuta el alcance completo definido en `docs/00_PRODUCT_SCOPE.md`.

## 1. Autoridad y fuentes de verdad

Orden de precedencia:

1. fuente normativa oficial archivada y su evidencia;
2. revisión curricular `PUBLISHED` inmutable;
3. migraciones y esquema de datos;
4. motor de dominio determinista;
5. tests y verificadores;
6. ADRs vigentes;
7. documentación funcional/técnica;
8. `docs/state/ROADMAP_STATUS.json`;
9. conversación actual.

Nunca inventes una regla académica para «completar» una tabla ambigua.

Estados epistemológicos obligatorios:

- `VERIFIED`: respaldado por evidencia suficiente;
- `DERIVED`: derivación determinista de reglas verificadas;
- `INFERRED_PENDING_REVIEW`: inferencia explícita, nunca publicable automáticamente;
- `UNKNOWN`: información ausente o ambigua;
- `DISPUTED`: fuentes confiables en conflicto;
- `SUPERSEDED`: reemplazada por una norma posterior.

## 2. Regla de memoria

No dependas de memoria conversacional.

Al iniciar **cada sesión**:

1. lee este archivo;
2. lee `docs/state/CURRENT_STATE.md`;
3. lee `docs/state/ROADMAP_STATUS.json`;
4. lee `docs/state/OPEN_DECISIONS.md`;
5. inspecciona `git status`, `git log --oneline -20` y el diff pendiente;
6. carga sólo las Skills requeridas;
7. lee las especificaciones del área que vas a tocar;
8. reconstruye el siguiente trabajo desde el repositorio.

Antes de terminar **cada sesión**:

1. actualiza `CURRENT_STATE.md`;
2. actualiza `ROADMAP_STATUS.json`;
3. registra decisiones en ADR si cambian arquitectura;
4. registra riesgos/deuda si existen;
5. deja comandos ejecutados y resultados;
6. no marques algo `done` si queda código placeholder, test omitido o TODO de alcance.

## 3. Regla de versiones y documentación

Nunca supongas que recuerdas la API actual de una dependencia.

Antes de instalar, actualizar o usar una API version-sensitive:

1. determina la versión instalada o a instalar;
2. consulta documentación oficial correspondiente a esa versión;
3. revisa release notes/breaking changes;
4. comprueba compatibilidad con el resto del stack;
5. registra la versión resuelta en `docs/research/TECHNOLOGY_BASELINE.md`;
6. fija lockfiles;
7. ejecuta pruebas de compatibilidad.

A fecha de creación de este kit (2026-08-08):
- Django 6.1 todavía figura oficialmente como **UNDER DEVELOPMENT**; no lo trates como final hasta verificar que exista una release final.
- Django 6.0.8 tiene release notes oficiales con fecha 2026-08-04.
- Next.js 16.3 aparece todavía como preview/canary en las fuentes verificadas; `next@latest` estaba en la rama estable 16.2.x. Verifica NPM y documentación oficial al ejecutar.
- gpt es un modelo oficial y soporta contexto 1M.
- codex debe mantenerse actualizado; gpt recomienda >= 1.14.24 para su integración.

No conviertas esta fotografía temporal en una verdad eterna. Verifica de nuevo.

## 4. Invariantes arquitectónicos

### 4.1 Dominio

- `Course` ≠ `CourseVersion` ≠ `PlanMembership` ≠ `CourseOffering`.
- `CurriculumPlan` ≠ `CurriculumRevision`.
- `CurriculumRevision` ≠ `CurriculumLayout`.
- La posición visual en un semestre no es una regla normativa.
- Oferta académica por período no pertenece a la revisión curricular.
- El frontend nunca determina por sí solo elegibilidad o graduación.
- El LLM nunca determina por sí solo elegibilidad o graduación.
- El motor académico debe ser Python puro, determinista y testeable sin ORM.
- Toda regla publicada debe tener evidencia.
- Una revisión publicada es inmutable. Los cambios crean una nueva revisión.
- No hay doble conteo de créditos salvo regla explícita.
- Los créditos «aprobados» y los créditos «aplicados a requisitos» son conceptos distintos.
- Las reglas deben admitir composición `ALL`/`ANY` y condiciones no basadas en cursos.
- Un requisito ambiguo produce `UNKNOWN`, no un booleano inventado.
- Cualquier excepción individual debe quedar como objeto auditable, no como mutación del plan global.

### 4.2 Arquitectura

- Monolito modular en backend.
- Frontend Next independiente.
- PostgreSQL como base transaccional.
- No microservicios salvo ADR posterior con evidencia de necesidad.
- No Neo4j: el grafo curricular se modela relacionalmente y se proyecta.
- No GraphQL salvo ADR posterior.
- No Elasticsearch salvo ADR posterior.
- No Kafka salvo ADR posterior.
- No Redis «por costumbre»: introducirlo sólo si una necesidad concreta lo justifica.
- OpenAPI es contrato entre backend y frontend; cliente TypeScript se genera.
- Operaciones largas se desacoplan mediante una interfaz de jobs/tasks; no contaminar dominio con Celery/RQ u otro proveedor.

## 5. Stack objetivo

La versión exacta debe resolverse en tiempo de bootstrap según política anterior.

### Frontend
- Next.js estable más reciente compatible;
- React compatible con Next;
- TypeScript `strict`;
- App Router;
- Server Components por defecto;
- Tailwind CSS;
- shadcn/ui para primitives componibles;
- React Flow (`@xyflow/react`) para grafo interactivo;
- ELK.js para auto-layout del grafo;
- dnd-kit para planificación drag/drop;
- Zod sólo donde aporte validación cliente/contrato;
- Playwright para E2E;
- Vitest + Testing Library para unidades/componentes;
- axe o equivalente para accesibilidad automatizada.

### Backend
- Python 3.14;
- Django estable compatible;
- Django Ninja si sus pruebas de compatibilidad pasan; si no, documenta ADR antes de cambiar;
- Pydantic para DTOs/AST donde corresponda;
- PostgreSQL;
- psycopg 3;
- pytest + pytest-django;
- Hypothesis para propiedades del motor;
- OR-Tools CP-SAT para optimización;
- OpenTelemetry para instrumentación.

### Tooling
- `uv` para entorno/dependencias Python si la versión estable verificada es compatible;
- `pnpm` para frontend/monorepo JS;
- Ruff para lint/format Python;
- mypy o Pyright: elegir uno y documentar;
- ESLint/Biome según compatibilidad oficial con Next instalado; no duplicar linters sin razón;
- GitHub Actions;
- Renovate;
- Docker/Compose;
- pre-commit opcional sólo si no duplica checks lentos.

## 6. Estructura de código objetivo

Respeta `docs/03_REPOSITORY_STRUCTURE.md`.

Backend por bounded contexts, no por tipo técnico global:

- identity
- institutions
- curriculum
- rules
- audit
- student_records
- offerings
- planning
- optimization
- governance
- imports
- notifications
- analytics

Dentro de cada módulo, separa domain/application/infrastructure/interfaces cuando aporte claridad; no produzcas arquitectura ceremonial.

Frontend por features/domains, con componentes de UI compartidos separados.

## 7. Norma de implementación

Para cada cambio:

1. identifica requisito/issue/roadmap item;
2. lee documentos relevantes;
3. inspecciona implementación existente;
4. define comportamiento observable y criterios de aceptación;
5. escribe/actualiza tests;
6. implementa el cambio coherente completo;
7. ejecuta tests focalizados;
8. ejecuta typecheck/lint;
9. actualiza OpenAPI/cliente si aplica;
10. ejecuta subagente reviewer;
11. resuelve hallazgos High/Critical;
12. ejecuta `python scripts/verify.py`;
13. actualiza documentación y estado;
14. sólo entonces marca completado.

## 8. Definition of Done global

Un elemento no está terminado si ocurre cualquiera de estos casos:

- TODO/FIXME relevante;
- `pass`, stub, mock permanente o respuesta hardcoded;
- tests omitidos/xfailed sin justificación documentada;
- migración sin prueba;
- endpoint sin contrato/documentación;
- regla académica sin evidencia;
- accesibilidad rota;
- comportamiento móvil no evaluado;
- manejo de errores ausente;
- seguridad relevante sin threat review;
- cambio de dominio sin actualización documental;
- cambio de API sin regenerar cliente;
- lint/typecheck/tests rojos;
- test «arreglado» debilitando aserciones para pasar;
- estado del roadmap desactualizado.

## 9. Política de pruebas académicas

El motor debe mantener propiedades como:

- determinismo;
- monotonicidad cuando una regla es monotónica;
- no doble conteo;
- trazabilidad de cada decisión;
- exactitud aritmética sin floats para créditos/porcentajes;
- equivalencia entre evaluación directa y serialización/deserialización del AST;
- comportamiento explícito ante `UNKNOWN`;
- ausencia de ciclos inválidos en prerrequisitos;
- manejo separado de correquisitos.

Crea golden cases para plan 2514.

## 10. UX

La interfaz debe responder inmediatamente:

- ¿qué he aprobado?;
- ¿qué estoy cursando?;
- ¿qué me falta por componente/agrupación?;
- ¿qué puedo cursar?;
- ¿qué está bloqueado y por qué?;
- ¿qué abre cada curso?;
- ¿qué está ofertado este período?;
- ¿qué conflictos de horario existen?;
- ¿qué ruta me acerca a un objetivo?;
- ¿qué requisito de grado no crediticio falta?;
- ¿de dónde sale cada regla?

No dibujes todas las flechas simultáneamente en la malla principal. Usa resaltado contextual. El grafo completo vive en su propia vista.

WCAG 2.2 AA como mínimo. Nunca codifiques estados sólo por color.

## 11. Seguridad y privacidad

- Nunca almacenes secretos en Git.
- Datos académicos individuales son privados.
- Principio de mínimo privilegio.
- Auditoría para cambios curriculares y acciones administrativas.
- Protección CSRF/CORS/cookies según arquitectura real.
- Cookies de sesión seguras/HttpOnly/SameSite cuando corresponda.
- CSP fuerte y headers.
- Rate limiting en superficies sensibles.
- Validación de archivos importados.
- No ejecutar contenido subido.
- Sanitizar datos mostrados.
- Backups probados con restore drills.
- Borrado/retención definidos.

## 12. Git y operaciones peligrosas

Permitido sin preguntar:
- leer;
- buscar;
- ejecutar tests;
- crear/modificar archivos del proyecto;
- `git status`, `git diff`, `git log`;
- crear migraciones locales no destructivas;
- Docker local no destructivo.

Requiere aprobación:
- `git commit` si el usuario no ha autorizado commits automáticos;
- despliegue;
- migraciones destructivas en un entorno con datos;
- borrado masivo;
- acceso/rotación de secretos;
- acciones sobre producción.

Denegado:
- `git push` sin autorización explícita;
- `git reset --hard` sobre trabajo ajeno;
- borrar archivos no entendidos para «hacer pasar» tests;
- introducir secretos en archivos;
- publicar reglas académicas inferidas por un LLM.

## 13. Subagentes obligatorios

Usa:
- `architecture-reviewer` para cambios estructurales;
- `code-reviewer` para cada bloque significativo;
- `curriculum-auditor` para datos/reglas académicas;
- `security-reviewer` antes de producción o cambios sensibles;
- `ux-reviewer` para flujos críticos.

Los reviewers son de solo lectura y no deben «arreglar» sus propios hallazgos.

## 14. Skills obligatorias

Carga la Skill correspondiente antes de:
- cambiar currículo;
- implementar una feature;
- actualizar dependencias;
- cambiar API;
- crear migraciones;
- preparar release;
- depurar una regresión;
- tocar seguridad.

## 15. Política anti-deriva

Si descubres que la implementación se está convirtiendo en:
- una malla estática;
- un conjunto de `if course.code == ...`;
- reglas duplicadas en frontend/backend;
- un JSON monolítico no versionado;
- una base de datos sin procedencia;
- un «MVP» con funcionalidad aplazada indefinidamente;

detén ese enfoque, registra el problema y corrige arquitectura antes de continuar.

## 16. Cierre de sesión

Deja `docs/state/CURRENT_STATE.md` contestando:
- qué quedó terminado;
- qué verificaciones pasaron;
- qué no quedó terminado;
- siguiente acción exacta;
- decisiones abiertas;
- riesgos;
- comandos para reanudar.

El siguiente agente debe poder continuar sin leer la conversación anterior.
