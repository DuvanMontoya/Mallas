---
name: db-migration
description: Protocolo para migraciones Django/PostgreSQL seguras, reversibles cuando sea viable, con datos, locks, índices y despliegue.
---

# DB migration

1. Clasifica schema-only/data/destructive.
2. Evalúa tamaño y locks.
3. Diseña expand/contract si producción puede tener tráfico.
4. Nunca borrar columna con código dependiente activo.
5. Añade test de migración cuando haya transformación.
6. Plan de rollback/restore.
7. `makemigrations --check` y `migrate` sobre DB limpia.
8. Prueba upgrade desde snapshot representativo cuando aplique.
9. Revisión antes de operación destructiva.
