# Schemas

`requirement.schema.json` define el AST inicial del motor.

`curriculum.schema.json` define la forma estructural mínima del baseline
curricular importable. La validación semántica adicional (referencias,
totales, ciclos, evidencia y estados epistemológicos) vive en el validador
puro `modules.imports.application.baseline`; el JSON Schema por sí solo nunca
autoriza publicación.

El esquema de producción puede evolucionar, pero:
- debe tener `schema_version`;
- migraciones de AST deben ser explícitas;
- una revisión publicada conserva el AST original o una migración reproducible;
- agregar un nodo requiere semántica, tests unitarios, properties y documentación.
