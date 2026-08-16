---
name: security-change
description: Protocolo para cambios de autenticación, autorización, uploads, fetch de URLs, secretos o datos privados con threat model y security review.
---

# Security change

1. Define activos y trust boundaries.
2. Identifica abuso plausible.
3. Implementa deny-by-default.
4. Añade tests negativos.
5. Verifica ownership/RBAC.
6. Revisa logs.
7. Revisa CSRF/CORS/CSP/session.
8. Para URL fetch: bloquea redes privadas/redirect bypass.
9. Para uploads: size/type/scanning/no execution.
10. Ejecuta security-reviewer.
