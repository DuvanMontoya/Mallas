---
name: release
description: Prepara una release de producción con gates de calidad, seguridad, migración, backup, smoke, rollback y observabilidad.
---

# Release

No release si:
- verify falla;
- Critical/High abierto;
- migración riesgosa sin plan;
- backup/restore no está operativo;
- cambio normativo no aprobado;
- secretos faltantes.

Secuencia:
build → tests → scan → migration review → backup gate → deploy → migrate → smoke → observability check → rollback readiness → release notes.
