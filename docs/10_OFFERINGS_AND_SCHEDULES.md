# 10 — Oferta, grupos y horarios

## Separaciones

`eligible(course, student, revision)` es normativo.

`offered(course, term)` es temporal.

`schedulable(section, preferences)` considera horario.

`enrollable` puede requerir otros datos institucionales no disponibles; no usar la palabra si no se puede afirmar.

## Modelo

AcademicTerm → CourseOffering → Section → Meetings.

## Fuentes

Registrar fuente y `retrieved_at`. La oferta puede cambiar durante inscripción.

## Estados UI

- cumple requisitos + ofertada;
- cumple requisitos + no ofertada;
- bloqueada;
- regla desconocida;
- ofertada + conflicto;
- ofertada + cupo desconocido.

No afirmar disponibilidad de cupos si la fuente no la proporciona en tiempo real.

## Horarios

Usar intervalos temporales con zona horaria del campus. Detectar:
- solapamiento;
- traslados si se modelan;
- sesiones alternas;
- fechas parciales;
- festivos sólo si forman parte del problema.
