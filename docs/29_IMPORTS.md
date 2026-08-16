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

## PDF

Extracción LLM/OCR es probabilística. Conservar:
- archivo original;
- texto extraído;
- confianza;
- campos no resueltos;
- confirmación.
