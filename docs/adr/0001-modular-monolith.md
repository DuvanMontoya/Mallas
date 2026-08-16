# ADR-0001 — Monolito modular Django

**Estado:** ACCEPTED  
**Fecha:** 2026-08-08

## Contexto
El dominio combina reglas curriculares, estudiantes, oferta, planeación, optimización y gobierno de datos. Requiere transacciones fuertes y evolución rápida, pero no presenta una necesidad demostrada de despliegues independientes por dominio.

## Decisión
Construir el backend como **monolito modular Django** con límites explícitos entre contextos y una sola base PostgreSQL inicialmente.

## Límites
Identity, Institutions, Curriculum, Rules, Audit, Student Records, Offerings, Planning, Optimization, Governance, Imports, Notifications y Analytics.

## Consecuencias
- transacciones y consistencia sencillas;
- menos infraestructura accidental;
- modularidad exigida mediante imports/tests, no mediante red;
- una separación futura sólo ocurre mediante ADR respaldado por mediciones.

## Descartado
Microservicios desde el inicio: mayor coste operativo, consistencia distribuida y superficie de fallo sin beneficio demostrado.
