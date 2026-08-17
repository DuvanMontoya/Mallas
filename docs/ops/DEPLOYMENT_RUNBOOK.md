# Runbook de despliegue desde servidor limpio

Este procedimiento es la referencia operativa para una release. Requiere
Docker Engine/Compose, acceso al registry y un secret manager; no requiere
Python, Node ni `pnpm` en el servidor de aplicación.

## Precondiciones

1. Existe un tag de release y dos digests de imagen aprobados para API y web.
2. El secret manager entrega `infra/production.env` sin guardarlo en Git.
3. El bucket de backups está disponible, cifrado, versionado y en una cuenta o
   proyecto separado del servidor.
4. Se ha ejecutado un restore drill del backup más reciente dentro del período
   de retención.
5. El cambio curricular, si existe, tiene su propuesta, revisión, evidencia y
   aprobación humana separadas; CI no publica una revisión.

## Primer despliegue o servidor reemplazado

```bash
git clone --branch <release-tag> <repository-url> curriculum-navigator
cd curriculum-navigator
install -m 600 /secure/injected/production.env infra/production.env
python3 scripts/production_preflight.py --env-file infra/production.env
docker compose --env-file infra/production.env -f infra/docker-compose.production.yml config >/tmp/compose.rendered.yml
docker compose --env-file infra/production.env -f infra/docker-compose.production.yml pull postgres reverse-proxy api web
docker compose --env-file infra/production.env -f infra/docker-compose.production.yml --profile migration run --rm migrate
docker compose --env-file infra/production.env -f infra/docker-compose.production.yml up -d postgres api web reverse-proxy
# Ejecutar desde el host operador/CI, no dentro del contenedor de aplicación.
python3 scripts/smoke.py --base-url https://app.example.edu --web-url https://app.example.edu
```

El `config` renderizado se inspecciona para confirmar que no contiene
credenciales antes de ejecutarlo. El API no se publica con `ports`; sólo
Compose y el proxy lo alcanzan por la red privada. La imagen de aplicación no
incluye Python/Node/pnpm como herramientas de operación adicionales: el smoke
se ejecuta desde la estación del operador o desde CI, que sí tiene el runtime
diagnóstico y acceso HTTPS.

## Release posterior

1. Confirmar el digest nuevo y el backup pre-deploy.
2. Ejecutar `docker compose ... run --rm migrate` con la imagen nueva.
3. Arrancar la nueva imagen y esperar `service_healthy`.
4. Ejecutar smoke API/web, health, readiness y el journey crítico de login,
   dashboard, planner y gobernanza editorial.
5. Observar errores, latencia, publicaciones rechazadas y jobs durante la
   ventana de release.

No se eliminan imágenes anteriores hasta cerrar la ventana de rollback y no se
borra el volumen de PostgreSQL como parte de un despliegue.

## Comprobaciones de seguridad

- `docker compose config` no debe mostrar secretos literales en logs o
  artefactos.
- `docker inspect` debe mostrar `app` para API y `nextjs` para web.
- API/web deben estar en `read_only`, con `no-new-privileges` y sólo los
  volúmenes explícitos.
- El scan de imágenes debe tener cero Critical; High requiere triage y no se
  promueve sin decisión registrada.
- TLS se termina en Caddy con HSTS; el registry y el secret manager requieren
  autenticación separada del usuario de despliegue.

## Rollback

Seguir `docs/ops/ROLLBACK_RUNBOOK.md`. Una imagen se puede revertir sin
restaurar la base sólo si las migraciones son compatibles hacia atrás. Si la
migración no es compatible, detener tráfico, restaurar backup en un entorno
aislado y ejecutar el plan de recuperación aprobado; no hacer `down -v` sobre
la base de producción.
