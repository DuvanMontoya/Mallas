# Mantenimiento de PostgreSQL

## Preflight obligatorio

Desde el contenedor API o un entorno operatorio con el mismo lockfile:

```powershell
uv run --frozen python manage.py db_maintenance --check-only --json
uv run --frozen python manage.py migrate --check
uv run --frozen python manage.py makemigrations --check --dry-run
```

El primer comando informa el vendor y las migraciones pendientes. Un estado
distinto de cero bloquea la release. No se ejecutan migraciones destructivas ni
se modifica el esquema desde un job de mantenimiento.

## Estadísticas

En una ventana aprobada, después del backup:

```powershell
uv run --frozen python manage.py db_maintenance --analyze --json
```

En PostgreSQL esto ejecuta únicamente `VACUUM (ANALYZE)` sobre la base actual,
con autocommit para respetar la restricción de PostgreSQL. En SQLite local usa
`ANALYZE`. El comando no acepta nombres de tabla ni SQL desde entrada de
usuario y no borra datos.

## Frecuencia y evidencia

- `migrate --check` y `makemigrations --check --dry-run`: cada PR/release;
- `VACUUM (ANALYZE)`: semanal o según métricas de bloat/estadísticas;
- revisión de conexiones, locks, espacio y errores: semanal;
- restore drill y prueba de backup: mensual y antes de una migración riesgosa.

Registrar fecha, versión de imagen, base objetivo (sin credenciales), duración,
resultado y operador en el sistema de auditoría operativa.
