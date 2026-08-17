# ADR-0025 — Lecturas medidas y límites explícitos de optimización

## Estado

Aceptado — 2026-08-16.

## Contexto

P21 exige medir las rutas de malla, grafo y auditoría antes de introducir
infraestructura. El profiling local del plan 2514 mostró 164 consultas en una
auditoría de lectura, mientras que la malla y el grafo ya estaban dentro de
una escala universitaria pequeña. La cola del optimizador usaba dos workers,
pero su `ThreadPoolExecutor` podía aceptar trabajo sin límite.

## Decisión

- La búsqueda de enrollment preferido se expresa en una sola consulta SQL con
  `CASE`, conservando la prioridad normativa de estados y el desempate por
  fecha.
- La construcción de snapshots de auditoría precarga las evidencias y sus
  snapshots; no se añade un cache que pueda competir con el run persistido.
- La proyección del grafo reutiliza adyacencia e índices en cada request y la
  malla reutiliza un índice inverso de desbloqueos.
- El optimizador queda limitado a dos workers y 20 jobs en vuelo; una solicitud
  que supera capacidad queda auditada como `REJECTED` y se rechaza con 409.
- Los índices existentes se conservan porque `EXPLAIN` muestra cobertura de
  las consultas críticas. No se añade migración especulativa.
- React Flow/ELK se mantiene como carga diferida exclusiva de la ruta del
  grafo; el bundle audit se incorpora como herramienta reproducible.

## Alternativas descartadas

- Redis o caché de auditoría: no hay evidencia de que el read model persistido
  incumpla el presupuesto y la caché no puede convertirse en fuente de verdad.
- precálculo global de clausuras: la proyección de plan 2514 queda por debajo
  del presupuesto medido y el motor relacional ya conserva relaciones
  explicables;
- cola ilimitada o nuevos microservicios: ocultarían la presión de capacidad y
  contradirían los límites operacionales del monolito modular.

## Consecuencias

Las lecturas de auditoría reducen round trips sin alterar el resultado del
motor, y las pruebas verifican la selección y los presupuestos. La capacidad
del optimizador es explícita y observable, pero los despliegues con más
workers deberán revisar el límite junto con CPU, memoria y el pool de
conexiones. Los presupuestos de producción siguen pendientes de un baseline
con el servidor de despliegue y volumen real; no se publican como SLO desde
esta medición local.
