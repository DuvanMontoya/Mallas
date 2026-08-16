# 00 — Alcance total del producto

## 1. Definición

La plataforma es un **Curriculum Intelligence & Degree Planning System** centrado inicialmente en estudiantes de Estadística UNAL Bogotá.

No se limita a representar asignaturas: calcula el cumplimiento de requisitos, explica dependencias, incorpora oferta real por período, permite escenarios y optimiza rutas.

## 2. Personas

### Estudiante
Necesita comprender y gestionar su trayectoria sin interpretar manualmente acuerdos, tablas y cadenas de prerrequisitos.

### Aspirante
Explora la estructura del programa, dependencias y posibles rutas sin historia personal.

### Asesor académico
Audita estudiantes, detecta bloqueos y compara escenarios.

### Editor curricular
Ingiere documentos, propone reglas y corrige metadatos.

### Revisor curricular
Contrasta cambios con fuentes y publica revisiones.

### Analista institucional
Estudia cuellos de botella, demanda potencial y avance de cohortes con datos autorizados.

### Administrador
Gestiona instituciones, programas, permisos, fuentes y configuración.

## 3. Módulos finales obligatorios

1. Catálogo académico y currículo versionado.
2. Motor de requisitos.
3. Auditoría de grado.
4. Historia académica.
5. Malla curricular interactiva.
6. Grafo de dependencias.
7. Oferta de cursos por período.
8. Secciones y horarios.
9. Planificador manual de escenarios.
10. Optimizador de trayectoria.
11. Requisitos no crediticios de grado.
12. Equivalencias/homologaciones/sustituciones/excepciones.
13. Importadores de historia y fuentes.
14. Backoffice editorial/normativo.
15. Flujo de revisión y publicación.
16. Notificaciones y alertas.
17. Analítica estudiantil.
18. Analítica institucional.
19. Autenticación, autorización y auditoría.
20. Observabilidad.
21. Backups/DR.
22. CI/CD y gestión de dependencias.
23. Documentación pública e interna.
24. Multi-programa/multi-sede/multiinstitución.
25. Localización/i18n preparada.

## 4. Capacidades de la malla

Cada tarjeta de curso debe poder mostrar:
- código;
- nombre;
- créditos;
- componente;
- agrupación;
- obligatoriedad;
- estado personal;
- elegibilidad;
- oferta del período;
- requisito que la bloquea;
- número de cursos/requisitos que desbloquea;
- progreso que aporta;
- evidencia normativa.

Interacciones:
- hover/focus: contexto;
- click: panel de detalle;
- resaltar ancestros;
- resaltar descendientes;
- mostrar rutas mínimas;
- filtrar por componente, agrupación, estado, créditos;
- alternar vista sugerida / por profundidad / personalizada;
- zoom sólo donde aporte valor;
- exportar/imprimir;
- compartir escenario sin exponer historia privada.

## 5. Auditoría

Debe producir:
- total de créditos aprobados;
- total aplicado;
- exceso/no aplicado;
- progreso por componente;
- progreso por agrupación;
- obligatorias faltantes;
- optativas necesarias;
- requisitos no crediticios;
- inconsistencias;
- `UNKNOWN`;
- lista de próximos desbloqueos;
- explicación verificable de cada resultado.

## 6. Planificador

Debe soportar:
- múltiples escenarios;
- drag/drop;
- períodos futuros;
- límites de créditos;
- restricciones de horario;
- días preferidos/no disponibles;
- curso objetivo;
- fecha objetivo;
- carga académica;
- prioridad por área/interés;
- preferencias de modalidad;
- materias obligatorias primero/opcional;
- incertidumbre de oferta;
- comparación entre escenarios.

## 7. Optimización

El optimizador no reemplaza al estudiante. Genera soluciones explicadas.

Objetivos posibles:
- minimizar períodos restantes;
- minimizar riesgo de bloqueo;
- maximizar desbloqueos;
- equilibrar créditos;
- minimizar huecos horarios;
- respetar preferencias;
- maximizar cursos requeridos frente a libres;
- minimizar dependencia de cursos de oferta infrecuente.

Debe distinguir:
- `OPTIMAL`;
- `FEASIBLE`;
- `INFEASIBLE`;
- `UNKNOWN/TIME_LIMIT`.

## 8. Backoffice

Todo cambio curricular pasa por:
`DISCOVERED → SNAPSHOT → EXTRACTED → DRAFT → VALIDATED → IN_REVIEW → APPROVED → PUBLISHED`

No existe publicación automática de extracción LLM.

## 9. Fuera de alcance deliberado inicial

No se construye:
- un sistema oficial de inscripción SIA;
- modificación de registros oficiales de la UNAL;
- pago de matrícula;
- emisión de certificados oficiales.

Sí se diseñan puntos de integración futuros sin simular autorización oficial.

## 10. Criterio de éxito

Un estudiante debe poder responder correctamente, con evidencia y en menos de segundos:
«¿Dónde estoy, qué me falta, qué puedo ver ahora, qué me abre cada curso, qué se está ofreciendo, qué debería planear y por qué?»
