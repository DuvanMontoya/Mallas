# Runbook de backup y restore

## Política de referencia

| Activo | Frecuencia | Retención | RPO/RTO objetivo | Protección |
|---|---:|---:|---:|---|
| PostgreSQL custom dump | Cada noche y antes de migración riesgosa | 35 días + mensual 12 meses | 24 h / 2 h | cifrado KMS/age, object storage versionado e inmutable |
| WAL/PITR, si la criticidad lo exige | continua | según contrato | 15 min / 1 h | servicio gestionado o archivo separado |
| Artefactos de importación | versionado al escribir | política de datos personales | sin pérdida durante retención | bucket privado, SSE-KMS, sin acceso público |

Estos objetivos son una configuración operativa de referencia, no evidencia de
un SLO medido. La institución debe aprobar retención, borrado y residencia.

## Crear backup

Con `pg_dump` instalado en el host:

```bash
DATABASE_URL='postgresql://backup_user@db.internal:5432/curriculum?sslmode=verify-full' \
  python3 scripts/backup_postgres.py --output-dir /var/backups/curriculum
```

En desarrollo o CI, usando el cliente dentro del contenedor:

```bash
DATABASE_URL='postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum' \
  python scripts/backup_postgres.py --container infra-postgres-1 --output-dir var/backups
```

El script no registra contraseñas, crea el dump en formato custom, escribe
metadata SHA-256 y usa permisos 0600. El job operativo debe cifrar el archivo
antes de subirlo al bucket separado y conservar también la metadata.

## Restore drill automatizable

```bash
DATABASE_URL='postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum' \
  python scripts/restore_drill.py var/backups/curriculum-<timestamp>.dump \
  --container infra-postgres-1
```

El drill:

1. verifica el hash y tamaño de la metadata;
2. genera una base `restore_drill_*` no controlable por entrada de usuario;
3. restaura sin owner/ACL;
4. comprueba filas de `django_migrations` y tablas públicas;
5. elimina la base temporal en `finally`, incluso si la validación falla.

El resultado JSON y el hash se conservan como evidencia de operación. Para un
restore real, restaurar primero a una instancia aislada, validar migraciones,
conteos, health y smoke, y sólo después cambiar tráfico mediante el runbook de
rollback. Nunca restaurar sobre la base productiva sin una orden aprobada.

## Verificación mensual

- probar el archivo más antiguo aún dentro de retención;
- comprobar que la metadata coincide con el dump;
- medir tiempo de backup y restore contra RPO/RTO objetivo;
- comprobar cifrado, versionado, object lock y permisos del bucket;
- registrar resultado, operador, versión de imagen, PostgreSQL y acciones de
  reparación en el sistema de auditoría operativa.

La cadencia semanal/mensual y la condición de bloqueo de release están en
`docs/ops/RELEASE_CADENCE.md`. El restore drill no se considera satisfactorio
si sólo valida que el archivo existe: debe crear una base temporal, restaurar,
comprobar migraciones/tablas y demostrar el `DROP DATABASE` final.
