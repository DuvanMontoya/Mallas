# Matriz de configuración por entorno

| Variable | Desarrollo | CI | Producción | Secreto |
|---|---|---|---|---|
| `DJANGO_DEBUG` | `true` | `false` | `false` | no |
| `DJANGO_SECRET_KEY` | placeholder local | ephemeral CI | secret manager, 50+ chars | sí |
| `DATABASE_URL` | local Compose | service PostgreSQL | private DB endpoint | sí |
| `ALLOWED_HOSTS` | localhost | localhost | exact hostnames | no |
| `CSRF_TRUSTED_ORIGINS` | localhost HTTP | test origin | exact HTTPS origins | no |
| `CORS_ALLOWED_ORIGINS` | localhost | test origin | exact HTTPS origins | no |
| `SECURE_SSL_REDIRECT` | false | false | false behind TLS proxy | no |
| `SECURE_PROXY_SSL_HEADER` | false | false | true | no |
| `PRIVATE_IMPORT_STORAGE_ROOT` | local private dir | ephemeral workspace | encrypted private volume/bucket adapter | no |
| `API_IMAGE`, `WEB_IMAGE` | local build tags | SHA build tags | registry digest refs | no |
| `OBSERVABILITY_METRICS_TOKEN` | empty | ephemeral | secret manager | sí |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | empty/opt-in | empty | private collector endpoint | no |
| `SOURCE_FETCH_ALLOWED_HOSTS` | empty/fail closed | empty | explicit institutional allowlist | no |
| `OBJECT_STORAGE_*` | empty | empty | secret manager/provider binding | endpoint no; keys sí |

`infra/production.env.example` contiene nombres y placeholders solamente. La
CI y el servidor obtienen valores reales por variables protegidas; no se
construye una imagen con `ARG`/`ENV` de credenciales.
