# ADR-0017 — Adaptadores de oferta temporal y frescura

## Estado

Aceptada — 2026-08-16

## Contexto

La elegibilidad de una asignatura se deriva de una revisión curricular
publicada y de la historia académica del estudiante. La oferta de un grupo, su
horario y los datos de cupo cambian por período y no pueden mutar la revisión
curricular ni convertirse en reglas normativas. Además, el SIA tiene una
superficie pública de consulta, pero no se autoriza automatizar sesiones
autenticadas ni presentar datos de capacidad que la fuente no entregue.

La interfaz debe distinguir tres preguntas independientes:

1. ¿se reporta el grupo para el período (`offered`)?
2. ¿la persona satisface las reglas para cursarlo (`eligible`)?
3. ¿el horario es compatible con la selección (`schedulable`)?

## Decisión

Se modela la cadena temporal `AcademicTerm → CourseOffering → Section →
Meeting` separada de `CurriculumRevision`. Los cambios a términos, grupos,
reuniones o capacidad no crean una revisión curricular.

Las fuentes se integran mediante `OfferingSourceAdapter`, un contrato pequeño
que expone un descriptor y obtiene un payload normalizado. La implementación
productiva disponible es `StaticJsonOfferingAdapter`: recibe una captura
archivada y autorizada, valida el esquema, calcula SHA-256 y crea o reutiliza
un `SourceSnapshot`. `OfficialSiaPublicAdapter` documenta el punto de extensión
para el buscador público del SIA, pero falla explícitamente si se le pide
automatizar una consulta: no usa credenciales, no hace scraping privado y no
convierte una página no capturada en evidencia.

Cada captura conserva URL, método de recuperación, fecha `retrieved_at`,
hash, versión de esquema, período y si la fuente declaró capacidad en tiempo
real. La edad se proyecta como `FRESH`, `STALE` o `UNKNOWN`; una respuesta
ausente, antigua o ambigua no se transforma en disponibilidad actual.

Capacidad y matrícula son opcionales. Salvo que el descriptor de fuente marque
explícitamente `capacity_realtime`, el API devuelve `UNKNOWN` o
`REPORTED_NOT_REAL_TIME` y muestra una advertencia. Nunca se infiere que
`capacity - enrolled_count` sea un cupo transaccional.

La detección de conflictos es un servicio de dominio Python puro. Compara
intervalos locales por día de la semana, zona horaria, fechas parciales y DST;
los extremos iguales no chocan (`start < other_end`). Para una selección
concreta retorna cada ocurrencia recurrente que se solapa y mantiene la
trazabilidad hacia ambas secciones. Una zona horaria inválida produce
`UNKNOWN`, no un conflicto inventado.

## Consecuencias

- La importación puede repetirse de forma idempotente usando el hash de la
  captura.
- El read model puede mostrar oferta y elegibilidad contradictorias sin
  ocultar la contradicción: un grupo puede estar ofertado y bloqueado, o una
  asignatura elegible no estar ofertada.
- La página de ofertas es informativa; no ofrece capacidad de inscripción ni
  operaciones autenticadas del SIA.
- Los adaptadores futuros deben documentar autorización, formato, frecuencia,
  límites de acceso y la semántica de capacidad antes de conectarse.
- Se requiere una nueva captura para corregir una oferta publicada; no se
  sobrescribe evidencia histórica.

## Evidencia y referencias

- `docs/research/SOURCE_REGISTER.md`, entradas 18–22.
- `docs/10_OFFERINGS_AND_SCHEDULES.md`.
- `apps/api/modules/offerings/application/importer.py`.
- `apps/api/domain/offerings/schedule.py`.
