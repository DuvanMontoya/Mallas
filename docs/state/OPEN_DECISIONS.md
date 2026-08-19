# Decisiones abiertas

Sólo deben llegar al usuario decisiones genuinamente empresariales o irreversibles.

## D-001 Marca pública
Nombre comercial final pendiente. Usar nombre interno neutral `Curriculum Navigator` hasta decisión de marca.

## D-002 Licencia
No imponer licencia sin decisión del propietario.

## D-003 Django 6.1
No es decisión de producto: se resuelve automáticamente verificando si 6.1 final existe al bootstrap. Si no, usar latest patch 6.0 estable y mantener compatibilidad.

## D-004 Integración SIA
No asumir API ni scraping. Construir importadores propios y adaptador futuro. Cualquier integración autenticada requiere fuente/autorización.

## D-005 Resolver versión estable de Next

La revisión P91 observó `next@16.2.12` como canal `latest` y el proyecto
actualmente resuelve 16.3.1. No se modifica el lockfile mientras el registry
no sea accesible. En un runner con red, resolver la versión estable compatible,
regenerar el lockfile y ejecutar lint, typecheck, tests, build y E2E antes de
aceptar el cambio.

## D-006 Evidencia normativa posterior a Acuerdo 496 de 2023

La reauditoría P90 encontró referencias oficiales actuales al Acuerdo 496 de
2023 y observaciones de la página vigente, pero no un snapshot normativo
íntegro archivado que habilite mutar la revisión `PUBLISHED`. Mantener
`UNKNOWN`/`INFERRED_PENDING_REVIEW` hasta obtener archivo y revisión humana.

## D-007 Cierre de gates operativos

No es una decisión de producto: P24–P26, P92 y P94 sólo pueden pasar a `done`
cuando el runner tenga Docker/PostgreSQL, Python 3.14/Django, Node/pnpm y
herramientas manuales accesibles. Los resultados históricos no sustituyen la
ejecución posterior a los cambios.

## D-008 Decisiones cerradas durante la auditoría — 2026-08-17

La defensa de inmutabilidad y aislamiento de scope se implementó como
defensa en profundidad modelo + señal + trigger PostgreSQL y quedó registrada
en `docs/adr/0029-database-enforced-curriculum-scope.md`. No requiere elección
del usuario; la ejecución real de sus migraciones sigue siendo un gate
operativo externo.

## D-009 Universo de la primera campaña multiprograma

Antes de P107, el propietario debe fijar un universo institucional cerrado y
auditable para la primera `CoverageCampaign` (institución, sedes y fecha de
corte). La plataforma no anunciará “todos los pregrados” sin un inventario
oficial completo. Un piloto puede lanzarse con cobertura parcial, siempre
rotulada como tal, sin publicar currículos sin evidencia.

## D-010 Evidencia de aplicabilidad para asignación automática 2514

El Acuerdo 496 archivado demuestra el contenido del plan y en su artículo 6
indica que rige desde la publicación. La fecha `2023-05-09` disponible es la de
expedición; no existe snapshot de la fecha de publicación ni regla archivada de
cohorte, transición, reingreso o conservación de plan anterior. No es una
decisión que pueda tomar el software: gobierno curricular debe aportar y revisar
esa evidencia. Hasta entonces P102 puede implementar estados y resolución
fail-closed, pero la política 2514 será `UNKNOWN` y no asignará automáticamente.
