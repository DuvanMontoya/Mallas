# 03 — Estructura objetivo del repositorio

```text
/
├── AGENTS.md
├── apps/
│   ├── api/
│   │   ├── config/
│   │   ├── modules/
│   │   │   ├── identity/
│   │   │   ├── institutions/
│   │   │   ├── curriculum/
│   │   │   ├── rules/
│   │   │   ├── audit/
│   │   │   ├── student_records/
│   │   │   ├── offerings/
│   │   │   ├── planning/
│   │   │   ├── optimization/
│   │   │   ├── governance/
│   │   │   ├── imports/
│   │   │   ├── notifications/
│   │   │   └── analytics/
│   │   ├── tests/
│   │   └── manage.py
│   └── web/
│       ├── app/
│       ├── features/
│       ├── components/
│       ├── lib/
│       ├── styles/
│       └── tests/
├── packages/
│   ├── api-client/        # generado desde OpenAPI
│   ├── ui/
│   └── config/
├── data/
│   ├── curricula/
│   ├── fixtures/
│   └── layouts/
├── docs/
│   ├── adr/
│   ├── research/
│   └── state/
├── schemas/
├── scripts/
├── sources/
├── infra/
├── diagrams/
├── prompts/
└── .codex/
    ├── agents/
    └── skills/
```

## Regla de dependencias backend

`domain` no importa Django.

`application` puede importar domain y puertos.

`infrastructure` implementa puertos con Django/ORM/proveedores.

`interfaces` expone HTTP/commands/tasks.

No es obligatorio crear cuatro carpetas en cada módulo si son vacías. La separación conceptual sí es obligatoria.

## Regla frontend

- `app/`: routing/composición Next.
- `features/`: comportamiento por dominio.
- `components/`: primitives/reutilizables.
- `packages/api-client`: no editar manualmente.
- ningún cálculo normativo vive en hooks/componentes.
