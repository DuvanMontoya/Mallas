# Estrategia de object storage separado

## Propósito

Los artefactos de historia, documentos normativos, evidencias y backups no
deben vivir en la capa efímera de la aplicación ni en el mismo host que la
base transaccional. El registro académico guarda únicamente la clave privada,
SHA-256, tamaño, MIME, procedencia y retención; el objeto conserva el contenido
original y no es una autoridad normativa por sí mismo.

## Contrato

El adaptador de almacenamiento debe proporcionar:

- `put_private(key, bytes, content_type, sha256)` con escritura condicional;
- `get_private(key)` sólo para un servicio autorizado;
- `head_private(key)` para verificar hash/tamaño sin descargar;
- `delete_private(key)` sujeto a política de retención y auditoría;
- version ID y checksum devueltos por el proveedor;
- cifrado en reposo, TLS, versionado, lifecycle y object lock según política.

La validación de extensión, MIME, tamaño, firma, UTF-8, NUL y nunca-ejecutar
ocurre antes de `put_private`. Una URL pública o una URL prefirmada no se
almacena como sustituto de la evidencia: la base conserva snapshot/hash y
lineage.

## Separación y permisos

- `curriculum-source-snapshots`: bucket privado de documentos normativos,
  versionado, retención larga y acceso sólo a governance/import service.
- `student-import-artifacts`: bucket privado con retención mínima aprobada,
  KMS separado y borrado/anonymización conforme a la política de datos
  personales.
- `curriculum-db-backups`: cuenta/proyecto separado del runtime, cifrado con
  una clave no disponible para el proceso web, object lock y acceso sólo al
  job de backup/restore.

No se otorgan permisos `ListBucket` al frontend ni a usuarios; el API nunca
devuelve credenciales de object storage. Los backups no se mezclan con los
artefactos de estudiantes.

## Estado del repositorio

El adaptador `private-filesystem` y el volumen privado son la implementación
local verificable. La referencia Compose de producción mantiene el volumen
fuera del contenedor y deja las credenciales de object storage fuera de Git;
una instalación institucional debe conectar el contrato anterior a un bucket
S3-compatible o a un volumen cifrado gestionado antes de aceptar datos reales.
El hecho de que el backend funcione con filesystem local no autoriza a
considerarlo object storage separado.

La exportación/replicación de backups se ejecuta fuera del proceso web. Esta
separación evita que una credencial de bucket o una operación de borrado pueda
ser invocada desde una ruta de estudiante o desde el frontend.
