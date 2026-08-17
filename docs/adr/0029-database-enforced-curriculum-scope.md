# ADR-0029 — Invariantes de alcance e inmutabilidad de contenido curricular en base de datos

**Estado:** ACCEPTED  
**Fecha:** 2026-08-17

## Contexto

Las validaciones de Django protegen las rutas normales de escritura, pero no
se ejecutan cuando una importación, un comando administrativo o una operación
ORM usa `QuerySet.update()`, `bulk_create()` o una mutación de una tabla
intermedia Many-to-Many. Además, publicar una revisión debe congelar no sólo
la fila de la revisión sino también sus grupos, memberships, requisitos y
enlaces de evidencia.

## Decisión

- El motor conserva las validaciones de modelo (`full_clean`) para producir
  errores explicables en SQLite, tests y rutas de aplicación.
- PostgreSQL instala triggers `BEFORE INSERT OR UPDATE`/`DELETE` para bloquear
  contenido hijo de revisiones `PUBLISHED`, `SUPERSEDED` o `RETIRED`, y para
  comprobar que cursos, grupos, plan, programa, institución, término,
  matrícula, asignación de rol y curso cursado permanezcan dentro del mismo
  scope.
- Las señales `m2m_changed` protegen localmente los enlaces de evidencia de
  requisitos publicados; PostgreSQL mantiene la misma defensa en la tabla
  intermedia.
- Las revisiones publicadas continúan siendo inmutables y cualquier cambio
  normativo crea una revisión nueva con propuesta, evidencia y publicación
  auditable.

## Alternativas descartadas

- Confiar sólo en `Model.save()`/`Model.delete()`: deja bypass por operaciones
  masivas y no satisface el aislamiento multi-programa.
- Duplicar la regla en frontend: el frontend no es autoridad académica.
- Usar un microservicio o un grafo separado para validar scope: añade una
  ventana de inconsistencia sin necesidad demostrada.

## Consecuencias

Las migraciones deben ejecutarse antes de considerar PostgreSQL listo y las
funciones de trigger deben mantenerse junto con el modelo. Los usuarios de
runtime necesitan permisos de lectura sobre las tablas que los triggers
consultan; el rol migrator conserva la autoridad DDL. SQLite sigue siendo útil
para tests, pero los tests que prueban bypass SQL se marcan explícitamente
como cobertura PostgreSQL.

## Riesgos y revisión

Toda nueva relación curricular o de oferta debe añadirse a la matriz de scope
y a su trigger o validación de modelo. Revisar este ADR si se cambia el motor
de base de datos, se introducen cargas masivas nuevas o se modifica la
semántica de publicación.
