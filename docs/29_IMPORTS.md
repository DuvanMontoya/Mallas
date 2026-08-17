# 29 — Importadores

## Arquitectura

`Importer` produce candidatos, nunca objetos definitivos directamente.

```text
RawInput
 → Parser
 → CandidateRecords
 → Reconciliation
 → Validation
 → Preview
 → User/Admin confirmation
 → Commit
```

## Robustez

- fingerprint;
- idempotencia;
- errores por fila;
- provenance;
- schema version;
- rollback del batch.

## Historia académica — P06

La implementación de historia académica vive en `domain.history` (parser puro) y en
`modules.imports.application.history` (orquestación ORM). `POST /api/v1/history/imports`
acepta únicamente CSV, JSON o PDF privados y devuelve un preview. Cada preview crea un
`ImportBatch`, un `RawArtifact`, `CandidateRecord` por fila y una `Reconciliation` por
candidato; los candidatos no son historia oficial hasta la confirmación.

El formato propio JSON exige `schema_version: student-history/1.0.0` y `records`; el CSV
exige `course_code`, `term_code` y `status`. La normalización valida estados explícitos,
nota decimal, créditos y número de intento, conserva errores/warnings por fila y calcula
fingerprints reproducibles. La idempotencia se aplica por enrollment y SHA-256 del
archivo. Los conflictos de curso/período o número de intento, duplicados de archivo,
ambigüedades temporales y códigos externos quedan pendientes de decisión; nunca se
sobrescribe un intento existente.

El PDF usa `pypdf` 6.16.1 para extracción de texto solamente. Sus filas son candidatos
con confianza y locator de página/línea, siempre requieren revisión humana y se
conserva un extracto hashado como evidencia. No hay OCR ni LLM con autoridad para
confirmar historia. `ACCEPT` crea un `CourseAttempt` de origen `IMPORT`, `EXTERNAL`
crea `AcademicRecognition` con curso destino y referencia externa, y `SKIP` no altera la
historia. Todas las confirmaciones generan evidencia de procedencia, recalculan la
auditoría de grado dentro de una transacción y escriben `AuditEvent`.

Los endpoints de intentos permiten listar, crear manualmente, editar campos permitidos
y anular de forma auditable. Las comprobaciones de ownership/RBAC se ejecutan en el
backend para cada operación; el frontend no es una frontera de seguridad.

## PDF

Extracción LLM/OCR es probabilística. Conservar:
- archivo original;
- texto extraído;
- confianza;
- campos no resueltos;
- confirmación.

## Implementación P02

El baseline curricular se valida con `apps/api/modules/imports/application/baseline.py` y se
aplica mediante `services.import_curriculum_baseline`. El pipeline verifica el
`schema_version`, calcula un fingerprint canónico, valida totales/referencias/ciclos,
comprueba el SHA-256 del snapshot PDF y escribe un `ImportBatch` idempotente.

El lote crea una revisión `DRAFT`, una `ChangeProposal`, entidades de curso y grupos, y
locators `Evidence` por página. La ingestión no puede modificar revisiones que ya estén
en revisión editorial, aprobadas o publicadas. Las ambigüedades del baseline quedan en
`UNKNOWN` o `INFERRED_PENDING_REVIEW`; no se resuelven por heurística.

Comandos disponibles:

```bash
python manage.py validate_curriculum --json
python manage.py import_curriculum --json
python manage.py diff_curriculum --base <baseline-anterior.json> <baseline-candidato.json>
```
