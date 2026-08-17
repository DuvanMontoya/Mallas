# Runbook de freshness y cola de reglas desconocidas

## Freshness

1. Revisar el artifact `source-freshness` del workflow semanal.
2. Para `UNKNOWN`, `STALE` o `ERROR`, comprobar si la fuente se trasladó, si el certificado
   es válido y si el host sigue siendo parte de la allowlist institucional.
3. No ampliar allowlists, aceptar HTTP ni abrir rangos privados como solución
   de emergencia.
4. Si hay cambio real, archivar el contenido con SHA-256, crear una propuesta
   nueva y enlazar evidencia por página/sección/fila.
5. Ejecutar validación, impacto, revisión y publicación humana; conservar el
   reporte como evidencia operativa separada.

## Cola de reglas UNKNOWN

Desde `apps/api` y con una cuenta de operación autorizada:

```powershell
uv run --frozen python manage.py unknown_rule_queue --output var/reports/unknown-rules.json
uv run --frozen python manage.py unknown_rule_queue --format csv --output var/reports/unknown-rules.csv
```

El comando sólo lee requisitos con estado `UNKNOWN`,
`INFERRED_PENDING_REVIEW` o `DISPUTED`, incluye el lineage de evidencia que ya
exista y marca cada fila `HUMAN_REVIEW_REQUIRED`/`publish_blocker=true`. No
edita reglas y no puede publicar. La cola se prioriza por impacto del
requisito y antigüedad del snapshot en el sistema de gobierno; si la fuente no
permite verificarlo, se conserva `UNKNOWN`.
