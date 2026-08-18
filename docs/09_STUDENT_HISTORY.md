# 09 — Historia académica

## Importación

Fuentes soportadas por el producto final:
- entrada manual guiada;
- CSV/JSON de formato propio;
- PDF de historia académica con extracción asistida y revisión;
- integración oficial si en el futuro existe API autorizada.

No realizar scraping autenticado del SIA ni manejar credenciales institucionales sin autorización explícita y diseño de seguridad.

La historia persistida distingue `CourseAttempt` de `AcademicRecognition`. Un intento
conserva curso/version temporal, período, número de intento, estado oficial, nota,
créditos aplicados, origen, usuario que lo ingresó y lote/evidencia de importación.
Las modificaciones manuales están limitadas al propietario o a un rol autorizado; el
borrado es un anulado auditable (`ANNULLED`), no una eliminación física.

## Pipeline de importación

`upload → antivirus/type checks → parse candidate → normalize → reconcile course codes → preview → user confirms → commit import batch`

Nunca importar silenciosamente.

## Idempotencia

Cada lote conserva SHA-256 del archivo, fingerprint de contenido, versión de schema y
versión de parser. La unicidad de reimportación es por enrollment + SHA-256; repetir el
mismo archivo para el mismo enrollment devuelve el preview existente y no duplica
intentos. La confirmación también es idempotente después de aplicar el lote.

## Conflictos

Si un intento ya existe:
- comparar término/código/nota/estado;
- mostrar diff;
- exigir una decisión explícita `ACCEPT`, `EXTERNAL` o `SKIP`;
- no sobrescribir el registro existente; una aceptación de un segundo intento obtiene
  el siguiente número disponible;
- conservar lineage.

## Estados y créditos

El motor no deduce aprobación exclusivamente desde nota si el registro tiene estado oficial explícito. Define política por institución.

## Formatos y revisión

CSV y JSON usan el formato propio `student-history/1.0.0` y producen candidatos con
errores por fila, warnings, normalización, fingerprint, locator y estado de
reconciliación. Los registros con estado explícito no se reinterpretan por heurística.
Los códigos externos se resuelven mediante una equivalencia seleccionada y una nota;
no se convierten automáticamente en cursos internos.

El PDF se procesa como extracción de texto conservadora con `pypdf`: cada candidato
queda marcado para confirmación humana, conserva página/línea/extracto/confianza y no
puede convertirse en historia autoritativa por una inferencia del parser, OCR o LLM.
Un preview con errores o decisiones pendientes no puede confirmarse. La confirmación
crea `ImportEvidence` enlazada al artefacto privado y ejecuta una nueva auditoría de
grado dentro de la misma transacción; si falla, se revierte todo el batch.

Los archivos se almacenan fuera de media pública bajo `PRIVATE_IMPORT_STORAGE_ROOT`,
con nombre derivado del UUID/hash, límite de 10 MiB, extensiones CSV/JSON/PDF,
validación de MIME/firma, rechazo de ejecutables/archivos comprimidos y nunca se
ejecutan como código. La autorización se comprueba en cada lectura, resolución,
confirmación y mutación manual.

## Datos sensibles

Historia académica sólo visible a propietario y roles autorizados.

## Consistencia de lectura y aislamiento de PDF

La colección de intentos expone un cursor firmado y opaco. El primer cursor fija
`snapshot_at`; las páginas siguientes conservan ese corte y avanzan por una clave
estable coherente con el orden solicitado. El cliente sigue `next_cursor`, sin mezclar
offsets, para recuperar una historia completa sin duplicados u omisiones causados por
inserciones concurrentes.

El parser PDF se ejecuta en un proceso hijo sin acceso a la transacción ORM. El padre
aplica timeout y límite de memoria antes de liberar el trabajo; ante timeout, muerte o
respuesta inválida termina el proceso y falla de forma cerrada. En Windows se usa un
Job Object y en POSIX `RLIMIT_AS`. Los límites se configuran con
`HISTORY_PDF_PARSE_TIMEOUT_SECONDS` y `HISTORY_PDF_PARSE_MEMORY_MIB`.
