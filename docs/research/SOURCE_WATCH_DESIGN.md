# Vigilancia de fuentes normativas

## Objetivo y límite

La vigilancia sólo detecta que una fuente oficial cambió, dejó de responder o
se volvió antigua. No extrae una regla como `VERIFIED`, no crea un
`SourceSnapshot`, no muta una revisión y no publica automáticamente. Todo
cambio pasa por `DISCOVERED → SNAPSHOT → EXTRACTED → DRAFT → VALIDATED →
IN_REVIEW → APPROVED → PUBLISHED` con evidencia archivada y revisión humana.
Política operativa: `no auto-publish`.

La configuración allowlisted vive en
`docs/research/source_watch.json`. Cada fuente tiene host HTTPS exacto y una
edad máxima. El job conserva un hash acotado, estado, fecha de comprobación,
`Last-Modified` cuando el servidor lo entrega y una razón segura de error.
Cuando no hay `Last-Modified`, el estado es `UNKNOWN`: que la URL sea alcanzable
no demuestra que el contenido normativo sea reciente o semánticamente igual.

## Job

```powershell
python scripts/source_freshness.py `
  --config docs/research/source_watch.json `
  --output var/reports/source-freshness.json `
  --fail-on-stale `
  --fail-on-unknown
```

El job valida HTTPS, puerto 443, allowlist, DNS público, redirects
allowlisted, timeout y tamaño máximo. El JSON es un artefacto operativo; no se
sube como evidencia normativa hasta archivar el contenido mediante el flujo de
governance. `.github/workflows/source-freshness.yml` lo ejecuta semanalmente y
lo conserva como artifact.

## Estados y actuación

| Estado | Significado | Acción |
| --- | --- | --- |
| `FRESH` | Respuesta 2xx y no supera la edad de `Last-Modified` | revisar el reporte; no publicar automáticamente |
| `STALE` | `Last-Modified` excede la edad máxima | abrir investigación y archivar una nueva captura |
| `UNKNOWN` | job offline o sin evidencia temporal | no tomar decisión académica; reintentar con red |
| `ERROR` | DNS, TLS, redirect, HTTP o límite falló | fail closed, revisar disponibilidad/allowlist |

La fuente secundaria nunca sustituye una norma primaria. Una discrepancia se
registra como `DISPUTED` y permanece fuera de publicación hasta resolverla.
