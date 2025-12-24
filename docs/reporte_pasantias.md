# UNIVERSIDAD TECNOLÓGICA EQUINOCCIAL

**Tecnología superior en desarrollo de software**

**Pasantías clínica “Nuestra Señora de Guadalupe”**

## TEMA:

**Automatización del parte diario mediante la creación de un sitio web**

**Autores**
- Michael Lidioma
- Jossue Guerreo

Quito – Ecuador
2025

---

## Contenido

- I. Introducción
- II. Reportes
- III. Requerimientos

---

## I. Introducción

En el contexto de prácticas preprofesionales realizadas en la clínica “Nuestra Señora de Guadalupe”, se identificó que el parte diario de atención médicas sale del sistema, lo que puede estar generando pérdidas de tiempo en la consolidación de la información, duplicidad de registros y posibles inconsistencias de los reportes.

Ante esta necesidad, se solicitó realizar un análisis de la base de datos existente con el objetivo de proponer una estructura que permita generar el parte diario, aprovechando la información que ya existe durante el proceso de la atención a los pacientes.

Herramientas entregadas para el análisis:
- Base de datos en Windows SQL Server Management Studio
- Base de datos en Access
- Parte diario 2025 hasta octubre
- Máximo acceso a los reportes clínicos
- Código fuente programa en C#

## II. Reportes

El presente reporte entregado detalla la información diaria de las atenciones médicas realizadas en la clínica, el objetivo es proporcionar un resumen organizado y confiable de las atenciones efectuadas, considerando los datos de los pacientes, servicios, especialidades entre otros con el fin de apoyar el control, seguimiento y toma de decisiones administrativas y médicas.

Incluye:
- Número de atenciones
- Valor recaudado por consulta
- Valor recaudado por medicina
- Número de citas
- Cancelaciones

## III. Requerimientos

1. Número de atenciones: El sistema deberá calcular y mostrar el total de atenciones médicas realizadas en un periodo determinado.
2. Valor recaudado por consulta: Debe sumar los costos asociados a los servicios de atención prestados.
3. Valor recaudado por medicina: Total recaudado por venta o despacho de medicamentos.
4. Número de citas: Contabilizar el total de citas agendadas en el periodo seleccionado.
5. Cancelaciones: Identificar y contabilizar las citas canceladas.

---

## Estructura de datos (resumen)

Se listan las tablas importantes y campos clave (pacientes, profesionales, especialidad, servicios, institucion, tipo beneficio, diagnósticos, fechas, etc.).

## Solución (alto nivel)

Propuesta: implementar sincronización automática desde Access local hacia SQL Server centralizado, con backend Django que normalice y exponga los datos para reportes.

> **Nota del equipo:** Por ahora, dejar de lado la incorporación a SQL Server y centrarnos en conectar correctamente el archivo Access y permitir la importación manual desde la interfaz web.

---

**Fin del documento**
