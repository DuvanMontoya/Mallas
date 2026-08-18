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

## Alta nativa de estudiante y matrícula

`/admin/students` es la superficie operativa primaria; Django Admin no es el flujo de
producto. Un `ADMIN` sólo ve instituciones de su alcance. El catálogo encadena
institución → programa/campus → plan → revisión `PUBLISHED` → período de admisión.
La creación es atómica: cuenta con contraseña hasheada, perfil estudiantil, matrícula,
rol `STUDENT` acotado a institución/programa y `AuditEvent`. No se devuelve ni registra
la contraseña temporal y un fallo de validación no deja cuentas huérfanas. Las rutas
`/api/v1/admin/students/*` son privadas, `no-store`, requieren sesión y CSRF para
escrituras.
