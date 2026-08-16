# 31 — Baseline curricular: Estadística UNAL Bogotá, plan 2514

## Estado de esta especificación

Base documental: Acuerdo 496 de 2023, copia archivada en `sources/unal/estadistica/`.

La página actual de la Facultad de Ciencias publica:
- título: Estadístico(a);
- SNIES 32;
- duración estimada: 9 semestres;
- créditos: 141.

La FAQ actual del Área Curricular remite al Acuerdo 496/2023 para asignaturas, agrupaciones y créditos.

## Distribución

### Fundamentación — 52 créditos

- Fundamentación Matemático-Estadística: 36
- Fundamentación de Ciencias: 3
- Complementación Matemática: 4
- Programación: 3
- Comunicación: 3
- Guarda y Flujo de Datos: 3

### Formación Disciplinar o Profesional — 61 créditos

- Núcleo Estadístico: 36
- Aplicación Estadística: 6
- Complementación Estadística: 4
- Metodología: 3
- Consolidación Estadística: 12

### Libre Elección — 28 créditos

Total:
`52 + 61 + 28 = 141`.

## Obligatorias explícitas

Fundamentación Matemático-Estadística:
- 2015168 Fundamentos de matemáticas
- 2015181 Sistemas Numéricos
- 2016377 Cálculo diferencial en una variable
- 2015556 Cálculo integral en una variable
- 2015162 Cálculo vectorial
- 2015555 Álgebra lineal básica
- 2016378 Álgebra matricial
- 2015178 Probabilidad
- 2016379 Inferencia estadística

Núcleo Estadístico:
- 2016366 Estadística descriptiva y exploratoria
- 2016360 Análisis de regresión

Consolidación:
- 2016345 Seminario de estadística
- 2016344 Consultoría estadística
- completar además 8 créditos mediante una modalidad/opción de Trabajo de Grado según estructura y normas vigentes.

## Reglas de especial interés

- Guarda/Flujo: opciones requieren al menos 3 créditos de Programación.
- Diseño y desarrollo de encuestas: Muestreo Estadístico + 3 créditos de Programación.
- Trabajo de grado: 80% del total del plan. Sobre 141 créditos, el primer entero que satisface `C/141 >= 0.8` es 113.
- Seminario y Consultoría: 39 créditos del componente disciplinar.
- Práctica Estudiantil Estadística 2028081: 10 créditos de Libre Elección y requiere completar Núcleo Estadístico.
- Las optativas pueden revisarse anualmente: el dataset debe ser temporal/versionado.

## Ambigüedades preservadas

No corregir por intuición:
- Fundamentos de física moderna: el agrupamiento lógico de «Mecánica newtoniana o Fundamentos de mecánica y Cálculo diferencial...» debe confirmarse.
- Estadística espacial: la tabla muestra Análisis de Regresión como dependencia, pero el tipo de requisito no queda claramente rotulado.
- Teoría de respuesta al ítem: mismo problema.
- Indicadores sociales, Estadística y sociedad, Formulación y gerencia de proyectos: aparece «Prerrequisito» sin identificador claro en la tabla.

La aplicación debe mostrar `UNKNOWN` hasta verificación.

## Requisito de lengua extranjera

No forma parte de los 141 créditos. Se modela como requisito no crediticio de grado, versionado por normativa institucional vigente. La página oficial de Admisiones consultada para este kit indica nivel B1.

## Machine-readable

La fuente estructurada está en:

`data/curricula/unal/bogota/estadistica/2514/plan_2514_acuerdo_496_2023.json`

No se debe convertir automáticamente este archivo en revisión `PUBLISHED` sin pasar por el workflow editorial.
