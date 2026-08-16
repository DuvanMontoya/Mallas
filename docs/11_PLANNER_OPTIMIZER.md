# 11 — Planificador y optimizador

## Escenario

Un escenario es independiente de la historia real. No altera auditoría oficial hasta que un curso se convierte en intento real.

## Validación incremental

Al mover un curso a un término:
- evaluar prerrequisitos contra historia + términos anteriores;
- evaluar correquisitos contra mismo término;
- comprobar límite de créditos;
- oferta conocida;
- conflicto de sección si hay grupo;
- mostrar warnings, no perder el cambio silenciosamente.

## Modelo CP-SAT

Variables de ejemplo:
`x[c,t] ∈ {0,1}` si curso c está planificado en t.

Restricciones:
- cada curso máximo una vez salvo repeat policy;
- prerequisite ordering;
- corequisite same/earlier;
- required group coverage;
- credit bounds;
- term offering;
- schedule conflicts;
- target completion;
- locked choices del usuario.

Objetivos lexicográficos:
1. satisfacer todos los requisitos;
2. minimizar último término;
3. minimizar cursos de oferta incierta/infrecuente;
4. balancear créditos;
5. preferencias.

No mezclar objetivos con pesos mágicos sin documentar escala.

## Explicabilidad

Cada solución muestra:
- por qué se incluyó cada curso;
- qué requisito satisface;
- qué desbloquea;
- restricciones activas;
- supuestos de oferta;
- estatus del solver.
