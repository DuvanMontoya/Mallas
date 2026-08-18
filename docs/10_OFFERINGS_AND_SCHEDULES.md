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

## Procedencia, frescura y capacidad

Cada término, oferta y grupo que proviene de una captura conserva el
`SourceSnapshot` y su `retrieved_at`. El read model expone la edad como
`FRESH`, `STALE` o `UNKNOWN` y muestra el nombre, URL, hash y método de la
fuente cuando están disponibles. Una captura no se presenta como actual sólo
porque exista en la base de datos.

La capacidad es una afirmación separada de la existencia del grupo. Si la
fuente no declara capacidad transaccional en tiempo real, el resultado es
`UNKNOWN` o `REPORTED_NOT_REAL_TIME`; no se calcula ni se muestra un cupo
disponible como si fuera reservable.

La integración se hace mediante `OfferingSourceAdapter`. La primera ruta
operativa acepta payloads JSON normalizados y archivados. El adaptador de
referencia del buscador público SIA no inicia sesiones privadas ni hace
scraping autenticado: una captura debe ser obtenida por un proceso autorizado,
validada y entregada junto con su metadato de fuente. Ver ADR-0017 y el
registro de fuentes para los límites y URLs institucionales.

## Tres estados independientes

El API devuelve por separado `offered_state`, `eligibility_state` y
`schedulable_state`. Por ello son válidas estas combinaciones:

- `OFFERED` + `BLOCKED`: existe grupo, pero la persona todavía no satisface la
  regla normativa;
- `NOT_OFFERED` + `ELIGIBLE`: la persona puede cursar la asignatura, pero no
  hay grupo reportado para el término;
- `OFFERED` + `ELIGIBLE` + conflicto: el grupo existe y es elegible, pero la
  selección de horarios se solapa;
- cualquier estado + `UNKNOWN`: falta evidencia suficiente y se explica la
  razón, sin convertirla en un booleano.

## Alcance de períodos por matrícula

`GET /api/v1/academic-terms?enrollment_id=...` autoriza primero la matrícula y
devuelve únicamente períodos de su institución y campus, más períodos institucionales
sin campus. Si se suministra además un filtro incompatible de institución o campus, la
petición se rechaza; planificador e historia no consumen un catálogo global.

Los triggers PostgreSQL de término y oferta son funciones separadas por tabla. Cada
función sólo accede a columnas existentes en su propio registro y valida que campus,
institución, curso y período permanezcan en el mismo alcance.
