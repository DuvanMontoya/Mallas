# 14 — Arquitectura backend

## Estilo

Monolito modular Django.

HTTP no llama ORM disperso: endpoint → application service → repositories/domain.

## Pure domain

`rules` y núcleo de `audit` no importan:
- django;
- settings;
- ORM;
- network clients.

## Transacciones

Application services definen límites transaccionales.

Publicar revisión:
1. lock proposal/revision;
2. validate;
3. freeze content hash;
4. persist publication event;
5. commit;
6. enqueue recomputations after commit.

## Queries

Para lecturas complejas se permiten query services optimizados que no contaminen reglas.

## Cache

No introducir Redis inicialmente. Cachear sólo cuando profiling demuestre beneficio; una cache nunca es fuente de verdad.

## Jobs

Interfaz:
```python
class JobDispatcher(Protocol):
    def enqueue(self, job: JobSpec) -> JobId: ...
```

Proveedor concreto reemplazable.

## IDs

Preferir UUIDv7 si la versión estable del stack lo soporta de manera clara; si no, UUID4. Documentar ADR.

## Timestamps

UTC en DB; zona local sólo en presentación/meeting semantics.
