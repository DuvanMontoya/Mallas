# 37 — Retención, exportación y borrado

Separar:
- datos normativos públicos/versionados: retención histórica larga;
- auditorías institucionales: según política/contrato;
- datos personales del estudiante: minimización y retención definida;
- logs: ventanas limitadas, PII redactada;
- archivos importados: borrar originales tras extracción cuando la política lo permita.

El producto debe soportar exportación de datos personales y procesos de borrado/anonymización sin destruir evidencia normativa compartida.

## Candidatos de historia académica

- `CandidateRecord.raw_payload` sólo contiene campos académicos en allowlist;
- previews no aplicados expiran a los 30 días por defecto, configurable mediante
  `HISTORY_RAW_PAYLOAD_RETENTION_DAYS`;
- al aplicar un lote, el payload crudo se purga en la misma transacción después de
  crear `ImportEvidence` y los objetos académicos definitivos;
- `raw_payload_expires_at` y `raw_payload_purged_at` permiten operar y demostrar la
  política sin inferirla desde timestamps genéricos;
- `python manage.py purge_history_raw_payloads` es idempotente y debe programarse en
  operaciones. El mismo comando elimina físicamente los bytes originales de
  `RawArtifact` al vencer `content_expires_at`, vacía su `storage_key` y conserva
  hash, tamaño, tipo, procedencia y `content_purged_at` como evidencia auditable.
  No elimina decisiones ni intentos confirmados.
