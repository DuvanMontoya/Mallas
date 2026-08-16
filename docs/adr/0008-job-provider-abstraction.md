# ADR-0008 — Trabajos asíncronos detrás de un puerto

**Estado:** ACCEPTED

El dominio y los casos de uso no dependen de Celery/RQ/Redis. Las tareas largas se exponen mediante un puerto de jobs. La implementación de producción se selecciona cuando las necesidades operativas estén medidas.
