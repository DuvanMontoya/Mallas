# 09 — Historia académica

## Importación

Fuentes soportadas por el producto final:
- entrada manual guiada;
- CSV/JSON de formato propio;
- PDF de historia académica con extracción asistida y revisión;
- integración oficial si en el futuro existe API autorizada.

No realizar scraping autenticado del SIA ni manejar credenciales institucionales sin autorización explícita y diseño de seguridad.

## Pipeline de importación

`upload → antivirus/type checks → parse candidate → normalize → reconcile course codes → preview → user confirms → commit import batch`

Nunca importar silenciosamente.

## Idempotencia

Cada import batch tiene fingerprint. Reimportar el mismo archivo no duplica intentos.

## Conflictos

Si un intento ya existe:
- comparar término/código/nota/estado;
- mostrar diff;
- permitir merge controlado;
- conservar lineage.

## Estados y créditos

El motor no deduce aprobación exclusivamente desde nota si el registro tiene estado oficial explícito. Define política por institución.

## Datos sensibles

Historia académica sólo visible a propietario y roles autorizados.
