# 40 — Workflows administrativos

## Nueva fuente
Discover → archive → hash → extract → diff → validate → review → approve/publish.

## Nueva revisión
No edita la publicada. Se deriva draft, se ve diff semántico, impacto y errores antes de aprobación.

## Override individual
Una excepción de estudiante debe indicar autoridad, motivo, evidencia, vigencia y actor; nunca reescribe el currículo global.

## Importación de oferta
Snapshot por período, origen, timestamp y checksum. Reimportar es idempotente.

## Revisión de ambigüedad
Estados: open, researching, resolved_verified, unresolved_unknown, disputed. Toda resolución deja trail.
