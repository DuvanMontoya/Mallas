# P04 — Auditoría de grado y asignación de créditos

No construyas un MVP. Esta fase es un bloque del producto completo.

## Preparación obligatoria

1. Lee `AGENTS.md`.
2. Lee `docs/state/CURRENT_STATE.md` y `docs/state/ROADMAP_STATUS.json`.
3. Inspecciona Git y código existente.
4. Lee `docs/06_DEGREE_AUDIT_SPEC.md`.
4. Lee `docs/24_BUSINESS_LOGIC_MATRIX.md`.
4. Lee `docs/31_CURRICULUM_2514_BASELINE.md`.

## Skills obligatorias
- carga `feature-delivery`

## Objetivo

Construir auditor reproducible que distinga créditos ganados/aplicados, obligatorias, buckets, requisitos no crediticios y UNKNOWN.

## Entregables obligatorios

1. Definir AuditInput/AuditContext/AuditResult puros.
2. Resolver estado de intentos y equivalencias mediante facts preparados por application layer.
3. Implementar CreditLedger/Allocation sin doble conteo.
4. Completar componentes y agrupaciones según required credits + mandatory courses + reglas.
5. Calcular overall sin convertir un simple porcentaje de créditos en graduación.
6. Incluir graduation requirements externos.
7. Generar remaining requirements y next-unlocks.
8. Persistir DegreeAuditRun con fingerprints/hash/engine version.
9. Cachear sólo por fingerprint si se justifica, manteniendo recomputación reproducible.
10. Crear golden degree audit fixtures completos para 2514.
11. API interna/app service para ejecutar auditoría.
12. Explicaciones localizables.

## Gates de aceptación

- [ ] no double count
- [ ] curso 4cr puede completar threshold 3 sin reasignar excedente arbitrariamente
- [ ] auditoría distingue earned/applied/unapplied
- [ ] UNKNOWN impide afirmar completitud cuando es material
- [ ] mismo input produce mismo result hash
- [ ] tests con homologaciones/excepciones
- [ ] plan completo puede auditarse correctamente

## Revisión

- Ejecuta subagente `architecture-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `code-reviewer` y resuelve todos los Critical/High.
- Ejecuta subagente `curriculum-auditor` y resuelve todos los Critical/High.

- Ejecuta `python scripts/verify.py`.
- Actualiza `docs/state/CURRENT_STATE.md`.
- Actualiza el item correspondiente de `docs/state/ROADMAP_STATUS.json`.
- Registra ADR si cambias una decisión arquitectónica.
- No marques la fase `done` si queda stub, TODO de alcance, test omitido o error conocido sin registrar.
