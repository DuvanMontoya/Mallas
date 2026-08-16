# 08 — Procedencia y gobernanza

## Regla

Una regla sin evidencia no se publica.

## Fuente primaria

Priorizar:
1. Sistema Legal UNAL / norma oficial;
2. documento PDF oficial;
3. página institucional oficial;
4. comunicados oficiales.

Fuentes secundarias pueden ayudar a descubrir, nunca a sustituir una norma cuando ésta existe.

## Evidencia

Cada regla necesita uno o más locators:
- documento;
- snapshot;
- página;
- artículo/sección/fila;
- hash/extracto corto;
- nota humana.

## Ingestión asistida por LLM

Permitido:
- extraer candidatos;
- normalizar nombres;
- detectar posibles relaciones;
- generar diff preliminar.

Prohibido:
- marcar VERIFIED por sí solo;
- resolver ambigüedades silenciosamente;
- publicar;
- inventar códigos;
- inferir una derogación sin fuente.

## Workflow

`DISCOVERED → SNAPSHOT → EXTRACTED → DRAFT → VALIDATED → IN_REVIEW → APPROVED → PUBLISHED`

Dos roles distintos para edición y publicación en producción institucional, salvo emergencia documentada.

## Source hash

Cada snapshot se almacena con SHA-256. Si la URL sirve contenido distinto, se conserva un snapshot nuevo.
