# Criterios de aceptación canónicos

Este índice reúne los gates que deben estar verdes antes de declarar el
producto listo. “Implementado” y “verificado en este entorno” son estados
distintos; un bloqueo externo se conserva como tal.

## Matrices y gates

- [Matriz de gates de aceptación](41_ACCEPTANCE_GATES_MATRIX.md)
- [Gates de aceptación de dominio](acceptance/DOMAIN_ACCEPTANCE.md)
- [Gates de producción](acceptance/PRODUCTION_GATES.md)
- [Matriz de trazabilidad P25](audit/P25_TRACEABILITY_MATRIX.md)
- [Auditoría de sistema P25](audit/P25_SYSTEM_AUDIT.md)
- [Auditoría anti-MVP P98](audit/ANTI_MVP_AUDIT_2026-08-17.md)

## Verificación reproducible

Desde la raíz del checkout, el orden canónico es:

```powershell
python scripts/verify.py
python scripts/scan_secrets.py
python scripts/sast.py
python scripts/verify_deployment.py
python scripts/verify_docs_clone_clean.py
python scripts/verify_state_recovery.py
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm e2e
```

Para los gates que requieren PostgreSQL, Docker, navegador o servicios externos,
la evidencia debe indicar versión, digest, migraciones, resultados, logs y
limitaciones. No se permite marcar un gate como PASS sólo por inspección de
código ni degradar aserciones para ocultar un fallo.

## Criterio de decisión

La declaración final sólo puede ser `READY` cuando no haya filas `PARTIAL`,
`MISSING`, `UNKNOWN` publicable o `BLOCKED_EXTERNAL` sin una evidencia externa
válida y reproducible. Las fuentes curriculares no archivadas requieren revisión
humana; una revisión publicada es inmutable y cualquier corrección crea otra
revisión.

