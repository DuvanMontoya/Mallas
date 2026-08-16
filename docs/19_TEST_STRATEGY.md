# 19 — Estrategia de pruebas

## Pirámide práctica

### Domain unit
Miles si es necesario; muy rápidas.

### Property-based
Hypothesis para AST/auditoría.

### Repository/application integration
DB real PostgreSQL en CI.

### API contract
OpenAPI snapshot + tests.

### Frontend unit/component
Estados, filtros, accesibilidad.

### E2E
Flujos críticos:
1. estudiante carga historia;
2. ve auditoría;
3. abre curso bloqueado y entiende por qué;
4. crea escenario;
5. optimiza;
6. editor propone cambio;
7. reviewer publica;
8. auditoría afectada se recalcula.

### Visual
Opcional pero recomendado para malla/grafo.

## Golden cases plan 2514

Casos deben cubrir:
- 0 créditos;
- sólo bloque obligatorio;
- completa Programación con curso de 4 créditos;
- 112 vs 113 créditos para 80%;
- Núcleo 32 vs 36;
- regla ANY;
- correquisito;
- UNKNOWN metodológico;
- historial con homologación;
- curso elegible en varios buckets;
- no double count.

## Mutation testing

Evaluar para `rules/audit` si costo CI es aceptable.
