# Navegador Curricular UNAL — Full Agent Build Kit

Este repositorio no es un MVP ni un prototipo de malla curricular. Es el **paquete de control, conocimiento, especificación y ejecución** para construir de extremo a extremo un producto completo de navegación curricular, auditoría de grado, grafo de requisitos, oferta académica, planificación y optimización de trayectorias.

## Objetivo inicial

- Institución: Universidad Nacional de Colombia
- Sede: Bogotá
- Facultad: Ciencias
- Programa: Estadística
- Plan: 2514
- Norma base verificada: Acuerdo 496 de 2023 del Consejo de Facultad de Ciencias
- Créditos del plan: 141
- Duración estimada publicada: 9 semestres

## Qué contiene este ZIP

1. `AGENTS.md`: constitución operativa obligatoria para codex/gpt.
2. `prompts/`: secuencia completa de prompts listos para copiar y pegar.
3. `docs/`: especificación funcional, técnica, normativa, UX, seguridad, pruebas, negocio y operación.
4. `.codex/`: subagentes y Skills especializados.
5. `data/`: plan 2514 estructurado de forma legible por máquina, catálogo externo y casos de prueba.
6. `schemas/`: esquemas del DSL de requisitos y del currículo.
7. `scripts/`: validadores y utilidades para impedir regresiones.
8. `sources/`: copia de la fuente normativa aportada por el usuario y registro de fuentes públicas.
9. `infra/`: diseño de infraestructura y plantillas de despliegue.
10. `diagrams/`: diagramas Mermaid de dominio, arquitectura y flujos.

## Cómo usarlo

### Paso 1 — descomprimir

Descomprima el ZIP en una carpeta vacía que será la raíz real del proyecto.

### Paso 2 — iniciar Git

```bash
git init
git add .
git commit -m "chore: initialize curriculum platform control repository"
```

### Paso 3 — abrir codex en esa carpeta

Use una versión actualizada de codex. Conecte gpt mediante `/connect`, elija gpt y seleccione `gpt` en `/models`.

### Paso 4 — no use `/init` para reemplazar AGENTS.md

`AGENTS.md` ya fue diseñado deliberadamente. Si codex propone regenerarlo, no permita que lo reemplace sin revisar el diff.

### Paso 5 — copiar el primer prompt

Abra:

`prompts/00_MASTER_AUTONOMOUS_BUILD.md`

Cópielo y péguelo completo en codex.

### Paso 6 — continuar

El agente debe trabajar desde el ROADMAP y guardar su estado dentro del repositorio. Los prompts siguientes sirven para forzar auditorías o reanudar fases concretas, no para volver a explicarle el proyecto desde cero.

## Regla central

La memoria permanente del proyecto es el repositorio, no el contexto de la conversación del modelo.

La autoridad se ordena así:

1. normas oficiales y evidencia,
2. datos publicados y versionados,
3. código + migraciones,
4. tests y verificadores,
5. documentación/ADRs,
6. estado del roadmap,
7. conversación del agente.

Si una conversación contradice una fuente oficial o un test de invariantes, la conversación pierde.
