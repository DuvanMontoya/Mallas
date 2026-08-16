# Schemas

`requirement.schema.json` define el AST inicial del motor.

El esquema de producción puede evolucionar, pero:
- debe tener `schema_version`;
- migraciones de AST deben ser explícitas;
- una revisión publicada conserva el AST original o una migración reproducible;
- agregar un nodo requiere semántica, tests unitarios, properties y documentación.
