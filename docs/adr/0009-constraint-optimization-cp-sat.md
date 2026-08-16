# ADR-0009 — Optimización académica con OR-Tools CP-SAT

**Estado:** ACCEPTED

El planificador automático modela selección/periodización/horarios como problema discreto. CP-SAT se usa para restricciones duras y objetivos jerárquicos. Si no existe solución, el producto debe explicar qué restricciones la hacen imposible o devolver un conjunto útil de conflictos, no una respuesta inventada.
