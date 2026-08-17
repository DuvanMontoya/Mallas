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
1. lock proposal, candidate revision and current published revision;
2. validate the candidate and verify the proposal base is still current;
3. freeze content/source hashes and create the supersession relation;
4. persist publication receipt, immutable `PublicationEvent`, per-enrollment
   `PublicationImpact` rows and notification outbox entries;
5. commit or roll back the complete transition as one unit;
6. dispatch recomputation and notification work only after commit.

The old enrollment revision basis and old audit rows are not updated by this
transaction. A new correction/rollback is another revision. The event stores
the semantic impact and a deterministic job key so a replaceable worker can
resume work idempotently without making the domain depend on a task provider.

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
