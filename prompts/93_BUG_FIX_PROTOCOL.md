# Corrección de bug sin regresiones

Carga `regression-debug`.

1. Reproduce el bug con input mínimo.
2. Escribe test que falla.
3. Identifica invariant/contrato violado.
4. Localiza causa raíz.
5. Corrige en la capa correcta.
6. No añadas hardcode de código de curso salvo datos fixture.
7. Ejecuta tests focales y globales.
8. Si el bug afecta regla académica, curriculum-auditor.
9. Si afecta auth/security, security-reviewer.
10. Actualiza docs/ADR si revela decisión faltante.
11. Deja estado y explicación de causa raíz.
