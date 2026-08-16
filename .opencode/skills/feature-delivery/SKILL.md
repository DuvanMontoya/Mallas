---
name: feature-delivery
description: Protocolo obligatorio para implementar una feature completa end-to-end sin dejar stubs ni olvidar tests, documentación, API o UX.
---

# Feature delivery

1. Identifica item de roadmap y criterios.
2. Lee specs de dominio/UX/API.
3. Inspecciona código existente.
4. Define vertical slice completo.
5. Añade tests antes/durante implementación.
6. Implementa backend domain/application/infrastructure.
7. Expone API tipada.
8. Regenera cliente.
9. Implementa UI con estados loading/error/empty/unknown.
10. Añade accesibilidad.
11. Ejecuta tests focalizados.
12. Revisor independiente.
13. Corrige Critical/High.
14. `python scripts/verify.py`.
15. Actualiza docs/state.
No declares «done» con placeholders.
