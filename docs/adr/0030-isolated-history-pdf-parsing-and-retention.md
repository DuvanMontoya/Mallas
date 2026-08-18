# ADR-0030 — Aislamiento del parser PDF y retención mínima de candidatos

Estado: `ACCEPTED`  
Fecha: 2026-08-17

## Contexto

La extracción PDF es trabajo sobre contenido no confiable. Ejecutarla dentro del
request y de la transacción que bloquea una matrícula permite agotar CPU/memoria y
extiende locks. Además, persistir todas las columnas importadas conserva PII que no es
necesaria para reconciliar una historia académica.

## Decisión

- PDF se analiza en un proceso hijo efímero; CSV/JSON, acotados y estructurados,
  permanecen en proceso.
- El proceso recibe un límite de memoria del sistema operativo y un timeout del padre.
  Nunca accede al ORM ni inicia la transacción de persistencia.
- La transacción y sus locks comienzan sólo después de recibir un `ParseReport` válido.
- `raw_payload` usa allowlist académica y límites de longitud.
- Un lote aplicado purga payloads crudos inmediatamente. Un preview expira por fecha y
  un comando idempotente aplica la retención.
- La evidencia mínima, fingerprints, decisiones y objetos confirmados se conservan;
  la purga no altera trazabilidad académica.

## Alternativas descartadas

- Analizar el PDF dentro del request principal: no contiene memoria/CPU ni separa el
  fallo del proceso web.
- Introducir Celery/Redis de inmediato: añade infraestructura sin que el aislamiento
  local y la interfaz de jobs existentes lo requieran todavía.
- Conservar el payload completo cifrado: el cifrado no sustituye minimización y sigue
  ampliando el impacto de una exposición autorizada o una retención excesiva.

## Consecuencias

Un PDF hostil no comparte memoria ilimitada con Django y un timeout no deja el request
bloqueado indefinidamente. La implementación debe mantener caminos específicos para
Windows Job Objects y POSIX `RLIMIT_AS`, probar timeout/muerte y operar periódicamente
la purga. El parser sigue sin autoridad: toda extracción PDF exige revisión humana.

## Riesgos y condiciones de revisión

El límite de memoria depende del sistema operativo y debe complementarse con límites
del contenedor. Se revisará esta decisión si el volumen exige cola persistente,
reintentos asíncronos o scanning externo, manteniendo la misma frontera de proceso y
sin dar autoridad académica al parser.
