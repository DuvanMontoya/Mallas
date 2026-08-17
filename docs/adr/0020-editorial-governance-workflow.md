# ADR-0020 — Flujo editorial auditable para gobernanza curricular

Estado: aceptado

Fecha: 2026-08-16

## Contexto

La ingestión de una fuente normativa puede producir candidatos de extracción,
diffs y revisiones de reglas antes de que exista una decisión humana. Esos
artefactos no pueden mutar una revisión publicada ni convertir una inferencia
en una regla `VERIFIED`. El backoffice también necesita separar la edición de
la aprobación, detectar concurrencia y dejar un recibo reproducible de cada
publicación.

## Decisión

Se implementa un bounded context editorial dentro de `governance` con los
siguientes objetos y límites:

- `ExtractionCandidate` representa una afirmación propuesta por la extracción,
  con operación semántica, estado, estado epistemológico y evidencia enlazada.
- `Review` y `Publication` son registros append-only a nivel de modelo. Una
  revisión publicada es inmutable; un cambio posterior requiere otra revisión.
- Las mutaciones pasan por servicios de aplicación deterministas que verifican
  alcance institucional, estado de workflow, evidencia, ETag/`If-Match` y
  separación editor/revisor. El frontend sólo presenta hechos y solicita estas
  operaciones.
- La bandeja, el visor de snapshot, el inspector AST, el diff semántico, el
  informe de validación, el análisis de impacto y la cola de revisión se
  exponen mediante `/api/v1/governance/*` y una pantalla `/sources`.
- Las operaciones masivas tienen una previsualización sin escrituras. El token
  de preview incorpora la versión de la propuesta, candidatos, decisión,
  estado epistemológico y evidencia; cualquier cambio vuelve inválido el
  token.
- Cada transición y vínculo de evidencia registra un `AuditEvent`. El detalle
  de la propuesta agrega los eventos de la propuesta, revisión, publicación,
  candidatos, requisitos y revisiones relacionadas.

La validación bloquea la publicación cuando una regla `VERIFIED` no tiene
evidencia, quedan candidatos pendientes, hay ciclos/totales inconsistentes o
existe otro error estructural. La publicación exige una confirmación humana
explícita y se delega a `CurriculumRevisionService.publish` para conservar las
invariantes del dominio curricular.

## Consecuencias

### Positivas

- Es posible revisar una extracción sin contaminar el plan oficial.
- Un editor puede preparar y enviar una propuesta, pero no aprobarla por sí
  solo; la autorización se vuelve a comprobar en el backend.
- Un conflicto de concurrencia se convierte en un error explicable y recarga
  la versión actual, en lugar de sobrescribir trabajo ajeno.
- El hash de contenido, el hash del conjunto de fuentes, el diff, la
  validación, el impacto y la confirmación quedan ligados al recibo de
  publicación.

### Costes y límites

- La cadena editorial tiene más estados y consultas que una edición directa.
- La evidencia debe pertenecer al snapshot de la propuesta; una fuente nueva
  genera un nuevo snapshot y una nueva decisión.
- La protección append-only de `Review`/`Publication` se mantiene en la capa
  de dominio y servicio; una futura política de despliegue puede añadir una
  restricción/triggers de base de datos si la operación institucional lo exige.
