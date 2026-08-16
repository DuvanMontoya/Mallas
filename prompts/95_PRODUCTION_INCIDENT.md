# Protocolo de incidente de producción

Prioridad: seguridad de datos y restauración del servicio, no cambios impulsivos.

1. Identifica alcance y severidad.
2. Preserva evidencia/logs.
3. Si hay exposición de secreto, rota mediante procedimiento autorizado.
4. Si hay corrupción de datos, detén writes si es necesario y usa backup/PITR según runbook.
5. No `reset --hard`, no borrar logs.
6. Crea reproducción.
7. Implementa hotfix mínimo con test.
8. Revisa seguridad.
9. Despliega según release runbook.
10. Postmortem sin culpa: causa raíz, detección, impacto, acciones.
11. Añade test/monitor que evite recurrencia.
