# ADR 0016 — Proyección semántica del grafo de dependencias

## Estado

Aceptado — 2026-08-16

## Contexto

La malla necesita explicar qué bloquea y qué desbloquea una asignatura sin
convertir el AST de reglas en flechas simplificadas. Una regla puede contener
`ALL`/`ANY`, equivalencias, correquisitos, umbrales de créditos, notas mínimas,
requisitos externos o información `UNKNOWN`. La posición visual de la malla no
es una regla normativa, y el frontend no puede convertirse en un segundo motor
académico.

## Decisión

El backend construye una proyección pura y determinista desde las reglas
parseadas:

- cursos son nodos `COURSE` identificados por `course:<code>`;
- cada condición lógica o cuantitativa es un nodo `CONDITION` identificado por
  propietario, requisito y ruta AST estable;
- las aristas conservan semantic, tipo, requisito, ruta y directness;
- las relaciones curso→curso se exponen aparte para cierres transitivos,
  desbloqueos, correquisitos y rutas cortas, sin eliminar los nodos de
  condición del grafo explicativo;
- los ciclos se calculan con orden estable y se entregan como señal de
  gobernanza, nunca como permiso implícito;
- las revisiones, estados epistemológicos, evidencia y límites de matrícula
  siguen siendo propiedad del read model y de la autorización del backend.

La ruta `/graph` usa un Client Component lazy para React Flow y ELK. React Flow
es sólo presentación: conexiones y arrastre están deshabilitados. La interfaz
incluye filtros de vista, foco contextual, leyenda con texto, rutas explicadas
y una lista textual equivalente, accesible por teclado y usable sin depender
del canvas.

## Consecuencias

Se puede distinguir una relación directa de una ruta transitiva y explicar qué
condición intermedia interviene. Los umbrales no se vuelven cursos ficticios y
los requisitos desconocidos permanecen visibles. El payload incluye más nodos
que un grafo curso→curso y requiere layout lazy; ELK y el panel de foco cubren
esa complejidad sin introducir una base de datos de grafos ni un microservicio.

La proyección depende del AST canónico y debe cambiar junto con sus tests
deterministas/golden. Cualquier futura edición de reglas requiere un bounded
context de gobernanza separado y no se habilita desde esta vista.

## Alternativas descartadas

- Flechas directas curso→curso: ocultan `ALL`/`ANY`, umbrales y evidencia.
- Neo4j: no aporta autoridad ni versionamiento que no pueda modelarse
  relacionalmente; el dominio sigue siendo relacional.
- Resolver el grafo en el navegador: duplicaría reglas y permitiría divergencia
  frente al motor Python.
- Canvas sin alternativa textual: incumple la arquitectura de accesibilidad y
  hace opaca la explicación para teclado/lectores de pantalla.
