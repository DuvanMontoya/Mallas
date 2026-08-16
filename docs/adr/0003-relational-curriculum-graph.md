# ADR-0003 — Grafo curricular sobre PostgreSQL

**Estado:** ACCEPTED

## Decisión
Persistir cursos, reglas y relaciones en PostgreSQL. Proyectar el grafo en memoria/API cuando sea necesario.

## Razón
El grafo es pequeño/mediano, está fuertemente asociado con datos transaccionales y muchas dependencias son hiperrreglas (`ALL`, `ANY`, umbrales), no aristas simples.

## Descartado
Neo4j no aporta suficiente valor inicial para justificar una segunda base y sincronización.
