# MASTER PROMPT — construir el producto completo

Estás dentro de la raíz del repositorio **Curriculum Navigator**. Tu trabajo es construir el producto completo de producción especificado aquí. No estás haciendo un MVP, demo, mock, prototipo ni una primera versión recortada.

## 0. Antes de tocar código

Haz exactamente esto:

1. Lee `AGENTS.md` completo.
2. Lee `START_HERE.md`.
3. Lee `docs/00_PRODUCT_SCOPE.md`.
4. Lee `docs/01_PRODUCT_PRINCIPLES.md`.
5. Lee `docs/02_DOMAIN_GLOSSARY.md`.
6. Lee `docs/03_REPOSITORY_STRUCTURE.md`.
7. Lee `docs/04_DOMAIN_MODEL.md`.
8. Lee `docs/05_RULE_ENGINE_SPEC.md`.
9. Lee `docs/06_DEGREE_AUDIT_SPEC.md`.
10. Lee `docs/07_CURRICULUM_VERSIONING.md`.
11. Lee `docs/08_DATA_PROVENANCE_GOVERNANCE.md`.
12. Lee `docs/31_CURRICULUM_2514_BASELINE.md`.
13. Lee `docs/research/TECHNOLOGY_BASELINE.md`.
14. Lee `docs/state/CURRENT_STATE.md`, `ROADMAP_STATUS.json`, `OPEN_DECISIONS.md` y `RISKS.md`.
15. Ejecuta `python scripts/verify.py`.
16. Inspecciona `git status`, `git log --oneline -20`.
17. Inspecciona el dataset `data/curricula/.../plan_2514_acuerdo_496_2023.json`.
18. Inspecciona `codex.json`, `.codex/agents/` y `.codex/skills/`.

No resumas esto para el usuario. Úsalo.

## 1. Verificación tecnológica obligatoria

Antes de scaffold:

### codex
- Obtén tu versión.
- Consulta documentación oficial correspondiente.
- Si `codex.json` usa sintaxis incompatible con tu versión, migra sólo la configuración, preservando semántica y documentando el cambio.
- Mantén `git push` denegado.

### gpt
El modelo esperado es gpt. No dependas de su memoria conversacional; usa repositorio/estado.

### Django
Consulta exclusivamente fuente oficial de Django para saber si **Django 6.1 final** ya existe.
- Si 6.1 final existe: usa la última 6.1.x estable compatible.
- Si sigue `UNDER DEVELOPMENT`, usa la última 6.0.x estable oficial. No instales RC/alpha/dev en producción.
- En ambos casos escribe código limpio compatible con el futuro upgrade cuando sea razonable.
- No falsifiques que «usamos 6.1» si no es final.

### Next.js
Consulta:
- registry NPM `next@latest`;
- release notes/documentación oficial.
Instala la última **estable**, no preview/canary, y usa docs version-matched.

### Resto
Resuelve versiones compatibles, estables y actuales para Python 3.14, PostgreSQL, Django Ninja, React Flow, ELK, dnd-kit, OR-Tools y tooling.
Registra las versiones resueltas en `docs/research/TECHNOLOGY_BASELINE.md`.
Fija lockfiles.

## 2. Regla de autonomía

No me preguntes decisiones técnicas ordinarias. Investiga, decide, documenta y avanza.

Sólo detente si:
- necesitas un secreto/credencial imposible de obtener;
- una norma académica oficial es genuinamente ambigua y no puede quedar simplemente `UNKNOWN`;
- una operación destructiva/irreversible necesita autorización;
- se requiere una decisión de marca/licencia/negocio que cambia derechos o costos;
- una dependencia crítica es incompatible y las alternativas implican un cambio arquitectónico mayor.

La falta de una marca final no bloquea: usa nombre interno neutral.
La falta de integración SIA no bloquea: implementa importadores/manual + adapter future.

## 3. No hagas MVP

No utilices expresiones como:
- «por ahora dejamos»;
- «en una futura versión»;
- «MVP»;
- «stub temporal»;
- «mock mientras tanto»;

para sacar del alcance módulos ya declarados obligatorios.

Puedes desarrollar por fases porque hay dependencias, pero el trabajo total continúa hasta pasar P25/P26.

Si una función no puede completarse por una dependencia externa real, construye:
- interfaz;
- modelo;
- estados;
- pruebas;
- fallback honesto;
- documentación;
y marca la dependencia externa explícita. No finjas que está completa.

## 4. Arquitectura no negociable

Respeta AGENTS.md, especialmente:

- monolito modular Django;
- frontend Next separado;
- PostgreSQL;
- domain engine puro;
- OpenAPI + cliente TS generado;
- no reglas académicas en React;
- no LLM dentro de audit/eligibility;
- revisión publicada inmutable;
- Course ≠ CourseVersion ≠ PlanMembership ≠ Offering;
- malla ≠ norma;
- UNKNOWN es válido;
- evidencia obligatoria;
- no double counting;
- no Neo4j/Kafka/GraphQL/microservicios salvo ADR justificado posterior.

## 5. Primera tarea: convertir el kit en repositorio ejecutable

Ejecuta P00:

1. resuelve toolchain;
2. crea monorepo;
3. scaffold `apps/api` y `apps/web`;
4. configura PostgreSQL local por Compose;
5. configura `uv`, `pnpm`, Python/Node versions;
6. configura lint/format/typecheck/test;
7. configura GitHub Actions inicial;
8. configura Renovate;
9. configura generación OpenAPI y cliente;
10. conserva scripts existentes;
11. expande `scripts/verify.py` sin borrar sus checks;
12. asegúrate de que un clone limpio pueda arrancar con instrucciones reproducibles;
13. actualiza README con comandos reales;
14. ejecuta suite inicial;
15. reviewer.

## 6. Después: ejecutar TODO el ROADMAP

No te detengas en P00.

Carga `docs/state/ROADMAP_STATUS.json` y ejecuta cada fase cuya dependencia esté `done`, en orden topológico.

Para cada fase:
- abre su prompt `prompts/NN_*.md`;
- carga Skills indicadas;
- usa subagentes de revisión;
- actualiza status y estado;
- ejecuta `scripts/verify.py`.

No marques una fase `done` si no cumple gates.

## 7. Requisitos de calidad durante toda la construcción

### Backend
- typing estricto razonable;
- services transaccionales;
- repositories/ports donde desacoplen domain;
- migrations seguras;
- no N+1 obvio;
- errors tipados;
- UTC;
- IDs documentados;
- audit trail.

### Frontend
- responsive real;
- keyboard;
- screen reader;
- no hydration innecesaria;
- error/empty/loading;
- URL/deep links;
- no estado académico duplicado;
- visualización limpia;
- mobile no es miniatura del desktop.

### API
- contratos;
- errors;
- pagination;
- concurrency;
- idempotencia donde aplica;
- generated client fresh.

### Seguridad
- threat reviews;
- ownership;
- file security;
- SSRF;
- CSRF/CSP/CORS;
- secrets;
- logging;
- backups.

### Datos académicos
- source/evidence;
- versioning;
- ambiguity;
- golden cases;
- exact arithmetic;
- reproducibility.

## 8. Plan 2514: baseline que debes usar

No reconstruyas desde memoria. Existe el dataset machine-readable y PDF archivado.

Antes de cargarlo a DB:
1. valida schema;
2. ejecuta `scripts/validate_curriculum.py`;
3. construye importer idempotente;
4. importa como draft;
5. ejecuta `curriculum-auditor`;
6. no publiques las reglas marcadas UNKNOWN/INFERRED sin un workflow explícito;
7. para el entorno demo/dev puedes tener una revisión de fixture claramente etiquetada `SOURCE_BASELINE_NOT_OFFICIAL_PUBLICATION` o resolver las ambigüedades mediante fuentes oficiales si las encuentras.

No alteres la fuente para hacer tests más cómodos.

## 9. Memoria persistente

Al final de cada bloque significativo:
- actualiza `docs/state/CURRENT_STATE.md`;
- actualiza `ROADMAP_STATUS.json`;
- registra ADR;
- registra riesgos;
- registra sesión.

Si te acercas a límite de contexto:
1. deja repositorio verde;
2. actualiza estado con siguiente comando exacto;
3. no inventes que terminaste;
4. termina diciendo al usuario que use `prompts/99_RESUME_AUTONOMOUS.md`.

## 10. Calidad de los commits

Si tienes permiso de commit:
- commits pequeños/coherentes;
- Conventional Commits;
- no mezcles refactor no relacionado;
- jamás push.

Si no tienes permiso, deja working tree organizado y diff revisable.

## 11. Cierre final de producto

Cuando creas haber acabado:
1. ejecuta `prompts/25_FULL_SYSTEM_AUDIT.md`;
2. ejecuta `prompts/98_ANTI_MVP_COMPLETENESS_AUDIT.md`;
3. ejecuta security-reviewer;
4. architecture-reviewer;
5. ux-reviewer;
6. curriculum-auditor;
7. `scripts/check_no_todos.py`;
8. `scripts/verify.py`;
9. tests E2E completos;
10. backup+restore drill documentado;
11. smoke deployment;
12. revisa documentación desde clone limpio.

No declares producción lista si alguno de los gates falla.

Comienza ahora. No me devuelvas sólo un plan: inspecciona, crea, ejecuta, prueba, revisa y continúa.
