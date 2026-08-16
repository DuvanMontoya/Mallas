# ADR-0007 — Versiones tecnológicas verificadas al ejecutar

**Estado:** ACCEPTED

No se congela en la documentación una versión «más reciente» indefinidamente. El bootstrap consulta fuentes oficiales, evita prereleases salvo decisión explícita, comprueba compatibilidad y después fija lockfiles. Las actualizaciones se hacen mediante la Skill `dependency-upgrade`.
