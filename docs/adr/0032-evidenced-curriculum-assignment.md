# ADR 0032 — Asignación curricular evidenciada y reproducible

- Estado: aceptado para P102
- Fecha: 2026-08-19

## Contexto

Una revisión curricular describe norma académica; no demuestra por sí sola a
qué admisión, cohorte, reingreso, traslado o transición individual debe
aplicarse. Elegir la primera revisión publicada o comparar únicamente su fecha
con el período de ingreso inventa una regla de aplicabilidad.

El Acuerdo 496 de 2023 archivado establece que rige desde su publicación, pero
el repositorio sólo demuestra la fecha de expedición `2023-05-09`. No hay
evidencia archivada de fecha de publicación, cohortes, grandfathering,
reingresos o transiciones.

## Decisión

1. `CurriculumAssignmentPolicy` es un agregado versionado separado de
   `CurriculumPlan` y `CurriculumRevision`. Conserva programa, plan/revisión
   objetivo, contexto, límites de admisión, cohorte, plan anterior, fechas
   normativa/efectiva separadas, estado editorial, estado epistemológico,
   evidencia y hashes.
2. Sólo una política `PUBLISHED` o histórica `SUPERSEDED`, `VERIFIED`, con
   evidencia y hashes completos puede resolver automáticamente.
3. Cero coincidencias devuelve `UNKNOWN`; coincidencias sin evidencia o varias
   políticas aplicables devuelven `NEEDS_REVIEW`. El orden de consulta y una
   prioridad numérica nunca desempatan una contradicción normativa.
4. Preview y alta usan el mismo resolver puro y el mismo `decision_hash`. La
   creación automática exige ese hash para cerrar el cambio entre preview y
   escritura.
5. Cada alta persiste `CurriculumAssignmentDecision` append-only con inputs y
   su procedencia, candidatos, razones, política/objetivo, versión del resolver,
   método y hash. PostgreSQL protege políticas, evidencia y decisiones frente a
   mutación directa.
6. El contrato legacy que aporta plan/revisión conserva una matrícula
   `NEEDS_REVIEW`, pero no la activa como resolución automática. El flujo nuevo
   no expone selectores técnicos de plan/revisión.
7. Ninguna matrícula existente cambia de revisión automáticamente. Toda
   transición posterior crea una nueva decisión auditable.

## Consecuencias

- Incorporar un programa exige archivar evidencia de aplicabilidad, no sólo el
  contenido curricular.
- Estadística 2514 permanece sin política automática `VERIFIED` hasta resolver
  D-010. La plataforma explica la causa y no selecciona silenciosamente.
- Reingreso, traslado, doble titulación y transición son contextos distintos y
  no heredan la regla de admisión ordinaria.
