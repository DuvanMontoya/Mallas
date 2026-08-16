# P06 — Historia académica e importadores

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/09_STUDENT_HISTORY.md`.
4. Lee `docs/29_IMPORTS.md`.
4. Lee `docs/17_SECURITY_PRIVACY.md`.

## Skills obligatorias
- carga `feature-delivery`
- carga `security-change`
- carga `db-migration`

## Objetivo

Implementar gestión completa de historia académica con import batches idempotentes, reconciliación, preview y confirmación.

## Entregables obligatorios

1. CRUD seguro de historia manual con trazabilidad.
2. ImportBatch/RawArtifact/CandidateRecord/Reconciliation models según necesidad.
3. Formato CSV/JSON propio documentado.
4. Pipeline de PDF candidate extraction con interfaz de parser y revisión humana; no convertir OCR/LLM en autoridad.
5. Preview de cambios antes de commit.
6. Detección de duplicados/conflictos.
7. Fingerprint e idempotencia.
8. Reconocer course codes externos/equivalencias.
9. Adjuntar evidencia/source a intentos importados.
10. Recalcular audit tras commit transactionally/async-safe.
11. Validar uploads: size/type/no execution/secure storage.
12. UI/API para corregir candidatos no resueltos.

## Gates de aceptación

- [ ] reimport no duplica
- [ ] conflictos no se sobrescriben silenciosamente
- [ ] PDF candidate necesita confirmación
- [ ] un archivo de otro usuario no es accesible
- [ ] audit se actualiza después de historia confirmada
- [ ] errores por fila son explicables

## Revisión

- Ejecuta subagente `security-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `ux-reviewer` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
