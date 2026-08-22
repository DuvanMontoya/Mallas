# Matriz de aceptación Chrome — estudiante real local

**Estado:** en ejecución. Ninguna fila `PENDING` constituye evidencia de cierre.

**Entorno:** Google Chrome del propietario, Next local, Django 6.0.8 y PostgreSQL
18 en el puerto local aislado `55432`. La identidad usada debe ser sintética,
creada por el frontend administrativo y persistida por los flujos reales.

## Criterio común por ruta

Cada ruta debe verificarse en escritorio y 390 px, con navegación visible,
teclado, foco, ausencia de overflow del documento, consola sin errores y
requests sin 4xx/5xx inesperados. Los estados `UNKNOWN` sólo son válidos cuando
representan una incertidumbre académica real y explicable; no sustituyen datos
operativos que el producto sí puede crear o gestionar.

| Ruta | Rol/estado | Comportamiento y acciones que deben probarse | Escritorio | 390 px | Consola/red |
|---|---|---|---|---|---|
| `/login` | anónimo | acceso, error seguro y recuperación | PASS: login real del estudiante y sesión persistida | PENDING | PASS: `auth/me` 200 tras recarga |
| `/reset-password` | anónimo | solicitud no enumerante y retorno | PASS visual | PASS: sin overflow documental | PASS visual; escritura no ejecutada |
| `/change-password` | estudiante con clave inicial | cambio obligatorio y sesión posterior | BLOCKED: formulario real verificado; falta secreto privado definitivo | PENDING | PASS: sesión limitada; rutas privadas responden 403 |
| `/onboarding` | estudiante nuevo | identidad, historia, período, carga, tour y reanudación | PENDING | PENDING | PENDING |
| `/` | estudiante | inicio útil y siguiente decisión | PENDING | PENDING | PENDING |
| `/curriculum` | estudiante | búsqueda, filtros, selección, detalle, evidencia y estados | PENDING | PENDING | PENDING |
| `/curriculum/print` | estudiante | vista imprimible completa y legible | PENDING | PENDING | PENDING |
| `/graph` | estudiante | foco, dependencias, ancestros/descendientes y explicación | PENDING | PENDING | PENDING |
| `/audit` | estudiante | créditos, faltantes, `UNKNOWN`, trazabilidad y evidencia | PENDING | PENDING | PENDING |
| `/history` | estudiante | alta/edición de intentos, reconocimientos y recálculo | PENDING | PENDING | PENDING |
| `/history/import` | estudiante | carga real, preview, revisión y aplicación | PENDING | PENDING | PENDING |
| `/offerings` | estudiante | período, oferta, secciones, horarios y conflictos | PENDING | PENDING | PENDING |
| `/planner` | estudiante | crear escenario, período, curso, mover, validar y proyectar | PENDING | PENDING | PENDING |
| `/analytics` | estudiante | snapshot, tendencia, bloqueos y escenarios | PENDING | PENDING | PENDING |
| `/sources` | estudiante | búsqueda, documento, snapshot, locator y procedencia | PENDING | PENDING | PENDING |
| `/profile` | estudiante | identidad, rectificación permitida y exportación | PENDING | PENDING | PENDING |
| `/admin/students` | administrador frontend | alta, preview, revisión, identidad y transición sin Django admin | PASS: alta real persistida y notificación | PENDING | PASS: creación 201; asignación `NEEDS_REVIEW` explicable |

## Gates transversales pendientes

- Creación del estudiante exclusivamente desde `/admin/students`. **PASS**:
  identidad sintética, cuenta, rol y matrícula fueron creados por el frontend.
- Login del estudiante en Chrome y persistencia de sesión real. **PASS**: la
  sesión sobrevivió recarga y reinicio de la API.
- Navegación por todos los enlaces visibles y deep links relevantes.
- Estados vacíos resueltos mediante datos/acciones disponibles, sin fixtures de UI.
- Escrituras persistidas y comprobadas después de recargar.
- Logout y rechazo posterior de rutas privadas.
- Repetición automatizada proporcional sin sustituir la evidencia de Chrome.

## Bloqueo seguro confirmado — 2026-08-22

Chrome está autenticado como estudiante y muestra el cambio obligatorio con los
tres campos requeridos. La integración de Chrome no ofrece `browserAuth` en esta
sesión. La política de credenciales impide que el agente lea, invente o escriba
la contraseña privada definitiva; el propietario indicó que está en el móvil y
no puede tomar temporalmente el control del PC. Por ello no es posible completar
el cambio ni recorrer rutas privadas sin degradar la seguridad. No se marca
ninguna ruta posterior como aceptada.
