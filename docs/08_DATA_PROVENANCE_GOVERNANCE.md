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

## Controles implementados

La bandeja editorial materializa el diff de una extracción como candidatos
`PENDING`; aceptar o rechazar un candidato es una decisión auditable y no
publica por sí misma. Para pasar a `VERIFIED`, la regla debe tener evidencia
que apunte al mismo snapshot normativo. La publicación exige una propuesta en
estado `APPROVED`, validación sin bloqueos, ausencia de candidatos pendientes,
confirmación humana explícita y una segunda función autorizada.

Las propuestas y requisitos de borrador usan versiones/ETag. Una escritura
obsoleta falla con conflicto de concurrencia; no se resuelve silenciosamente
con un overwrite. El recibo de publicación conserva el hash de contenido, el
hash del conjunto de fuentes, el diff, el informe de validación y la
confirmación. Los eventos de transición, revisión de candidatos y vínculos de
evidencia se muestran en la línea de auditoría de la propuesta.

## Publicación e impacto

La publicación pasa una compuerta previa que bloquea candidatos pendientes,
errores de validación, `UNKNOWN` no resueltos que impidan una conclusión y
desacuerdos de base entre la propuesta y la revisión vigente. El backend no
permite que un LLM publique ni que convierta una inferencia en `VERIFIED`.

Cuando la transición tiene éxito, una única transacción crea el recibo
inmutable y un `PublicationEvent` con el hash de la publicación, la revisión
que queda vigente, la revisión sustituida, el diff semántico, el resumen de
impacto y el plan de recomputación. Cada matrícula basada en la revisión
anterior recibe un `PublicationImpact` con el identificador y hash de su última
auditoría. El estado anterior queda intacto y la nueva auditoría requiere una
decisión sobre la revisión aplicable.

Las notificaciones se materializan como solicitudes en un outbox transaccional,
pero sólo un despachador posterior al commit puede entregarlas. Un fallo de
validación o un rollback de la transacción no produce usuarios notificados.
Los cambios preliminares no son eventos públicos; una corrección se publica
como una revisión nueva con su propia procedencia.
