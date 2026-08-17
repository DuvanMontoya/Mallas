# ERD implementado — P06

La fuente ejecutable del esquema es el conjunto de modelos Django y sus migraciones en `apps/api/modules/*/migrations/`. El diagrama Mermaid en `diagrams/domain-model.mmd` resume las relaciones; esta tabla fija las decisiones que no deben inferirse de la posición visual.

| Bounded context | Entidades persistidas | Relaciones esenciales |
|---|---|---|
| Identity | `identity.User`, `RoleAssignment`, `AuditEvent`, `RateLimitBucket` | Una cuenta puede tener cero o un `StudentProfile`; staff/editor/reviewer no se modelan como estudiantes implícitos. Los roles son asignaciones temporales y con alcance; el audit log es append-only y los contadores de rate limit son compartidos entre workers. |
| Institutions | `Institution`, `Campus`, `Faculty`, `Program` | Institución → sede → facultad → programa; códigos únicos dentro de su propietario. |
| Curriculum | `CurriculumPlan`, `CurriculumRevision`, `Course`, `CourseVersion`, `RequirementGroup`, `PlanMembership` | La identidad de `Course` es durable; versión temporal, membresía y oferta son relaciones separadas. No existe `Course.prerequisite_id`. |
| Rules | `Requirement` | El propietario se identifica por `owner_type`/`owner_id`; la regla se almacena como AST JSON versionable (`ast_schema_version`/`ast_hash`), queda ligada opcionalmente a una `CurriculumRevision`, y conserva estado epistemológico, hash y evidencia M:N. |
| Governance | `NormativeDocument`, `SourceSnapshot`, `Evidence`, `NormRelation`, `ChangeProposal` | Evidencia apunta a bytes archivados por snapshot/hash; las relaciones normativas son explícitas y no se deducen por fecha; una propuesta semántica no equivale a publicación. |
| Offerings | `AcademicTerm`, `CourseOffering`, `Section`, `Meeting` | La oferta depende de período y versión de curso; la elegibilidad no depende de que exista una sección. |
| Student records | `StudentProfile`, `StudentAdvisorAssignment`, `ProgramEnrollment`, `CourseAttempt`, `AcademicRecognition`, `AcademicException` | El enrollment conserva programa, plan, revisión base y término de admisión; un intento conserva origen/usuario/lote y sólo se anula, no se borra; la consulta de historia ajena exige asignación de asesor vigente; excepciones son individuales, temporales y auditables. |
| Imports | `ImportBatch`, `RawArtifact`, `CandidateRecord`, `Reconciliation`, `ImportEvidence` | El lote es por enrollment y archivo, idempotente por SHA-256, conserva schema/parser/fingerprints y estado preview/applied; el artefacto es privado; candidatos y decisiones preceden a la confirmación; la evidencia enlaza cada cambio al locator/extracto fuente; nunca se ejecuta contenido subido. |
| Planning | `PlanScenario`, `PlannedCourse`, `PlanningPreference` | Los escenarios son del estudiante/enrollment; un curso planificado tiene término y origen USER/OPTIMIZER. |
| Audit | `DegreeAuditRun`, `DegreeAuditResult`, `CreditAllocation` | Cada ejecución conserva fingerprints, versión de motor y asignaciones para impedir doble conteo. |
| Optimization | `OptimizationRun` | La ejecución conserva snapshot/hash de entrada, versión del solver, estado operativo/resultado, objetivos, solución, hash de salida, explicación y marcas de ejecución/cancelación. |
| Notifications | `NotificationEvent`, `NotificationDelivery`, `NotificationPreference`, `NotificationOutbox` | Una publicación crea una solicitud durable; el evento inmutable se materializa después del commit y se fan-out por usuario/canal con `dedupe_key`. Sólo la entrega in-app tiene lectura; email es opcional y no recibe payload académico. |

## Invariantes de persistencia

- Una revisión `PUBLISHED` no se modifica en contenido ni se elimina; su transición posterior sólo puede ser `SUPERSEDED` o `RETIRED` mediante el servicio de aplicación.
- Una única revisión publicada puede existir por plan; una revisión nueva debe declarar explícitamente la que supersede.
- `AuditEvent` sólo se inserta: el modelo, el admin y el trigger PostgreSQL bloquean UPDATE/DELETE; las cuentas con eventos no se eliminan en cascada y deben pasar por un flujo futuro de anonymización/retención. SQLite conserva la protección de modelo/admin para desarrollo y tests.
- `RoleAssignment` y `StudentAdvisorAssignment` son vigentes sólo dentro de sus ventanas temporales; ninguna de las dos relaciones convierte la posición visual de la malla en una regla académica.
- `Course`, `CourseVersion`, `PlanMembership` y `CourseOffering` tienen claves y temporalidad independientes.
- Las restricciones de rango, unicidad, pertenencia de institución y capacidad están en el modelo y se prueban en `tests/test_domain_foundation.py`.
- El importador curricular sólo actualiza revisiones `DRAFT`; una revisión `IN_REVIEW`, `APPROVED` o `PUBLISHED` se rechaza antes de tocar sus hijos.
- Los componentes del baseline se conservan como grupos padre `COMPONENT::<id>` y las 12 agrupaciones normativas como hijos con su identificador fuente.
- `ChangeProposal` conserva el diff semántico determinista y requiere un workflow editorial posterior.
- Un `ImportBatch` de historia sólo puede pasar de preview a applied si no hay errores ni reconciliaciones pendientes; la confirmación crea intentos/reconocimientos y su evidencia en una transacción con una nueva auditoría de grado.
- El paquete `apps/api/domain` sólo contiene primitivas puras y no importa Django.
- `NotificationEvent` sólo puede enlazar una `PublicationEvent` publicada; no se
  materializan drafts ni se crean entregas duplicadas para el mismo
  evento/usuario/canal. `NotificationDelivery.read_at` sólo aplica a `IN_APP`.

## Comandos de regeneración/verificación

```bash
uv run --frozen python manage.py makemigrations --check --dry-run
uv run --frozen python manage.py migrate --check
uv run --frozen pytest tests/test_domain_foundation.py
uv run --frozen pytest tests/test_curriculum_ingestion.py
uv run --frozen python manage.py validate_curriculum --json
uv run --frozen python manage.py import_curriculum --json
```
