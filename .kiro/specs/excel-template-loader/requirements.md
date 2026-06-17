# Requirements Document

## Introduction

Este módulo es responsable de la carga y validación de archivos Excel que actúan como plantillas de datos. La app acepta archivos Excel (.xlsx) como formato de entrada del usuario, pero internamente convierte el contenido a un formato tabular ligero (CSV/DataFrame) para procesamiento más eficiente. La exportación final también se genera en formato Excel. El archivo define el esquema de captura: la fila 1 contiene los nombres de columna, la fila 2 el tipo de dato esperado para cada campo, y la fila 3 un ejemplo de valor real obtenido de una narración de audio. La app valida que el archivo cumpla esta estructura (máximo 8 columnas), detecta el esquema y lo presenta al usuario para confirmación antes de continuar con cualquier otra operación.

## Glossary

- **Aplicacion**: El sistema de escritorio/web descrito en este documento.
- **Excel_Loader**: Componente responsable de cargar, validar y analizar el archivo Excel proporcionado por el usuario.
- **Archivo_Excel**: Archivo con extensión `.xlsx` que actúa como plantilla. Sus primeras tres filas son de cabecera: fila 1 = nombres de columna, fila 2 = tipo de dato esperado, fila 3 = ejemplo de valor. Contiene entre 1 y 8 columnas. Los datos reales se añaden a partir de la fila 4.
- **Esquema_Columnas**: Estructura detectada del Archivo_Excel al cargarlo. Para cada columna contiene: nombre (fila 1), tipo de dato (fila 2) y ejemplo de valor (fila 3). Tiene entre 1 y 8 entradas.
- **Tipo_Dato**: Valor de la fila 2 del Archivo_Excel para una columna dada. Indica el formato esperado del valor a extraer (ej: `texto`, `número entero`, `fecha DD/MM/YYYY`, `booleano`).
- **Ejemplo_Valor**: Valor de la fila 3 del Archivo_Excel para una columna dada. Ilustra el tipo de contenido que puede aparecer en una narración de audio para ese campo.
- **Formato_Interno**: Representación tabular interna (CSV/DataFrame) a la que se convierte el Archivo_Excel tras su carga y validación. Se usa para todo el procesamiento de datos por ser más ligero y eficiente que operar directamente sobre el formato .xlsx.
- **Pantalla_Esquema**: Pantalla o panel que se muestra tras cargar un Archivo_Excel válido, donde la app presenta el Esquema_Columnas detectado para que el usuario lo revise antes de continuar.
- **Contexto_Excel**: Párrafo descriptivo proporcionado por el usuario que explica qué es el Excel, su historia y lo que contiene. Se usa como contexto adicional para el LLM_Processor. Tiene un límite máximo de una hoja de texto (aproximadamente 3000 caracteres).
- **Contexto_Enriquecido**: Versión mejorada del Contexto_Excel generada por el LLM tras analizar el texto del usuario junto con el Esquema_Columnas y los datos de entrada del archivo. Se almacena internamente y se usa como contexto definitivo para la extracción de campos.
- **Pantalla_Principal**: Interfaz principal de la Aplicacion donde se realizan todas las interacciones del usuario.

---

## Requirements

### Requirement 1: Carga del archivo Excel

**User Story:** Como usuario, quiero cargar un archivo Excel que actúe como plantilla con nombres de columna, tipos de dato y ejemplos de valor, para que la aplicación detecte automáticamente el esquema y lo use para extraer datos de mis narraciones de audio.

#### Acceptance Criteria

1. THE Excel_Loader SHALL presentar un control de carga de archivos en la Pantalla_Principal que permita al usuario seleccionar un archivo `.xlsx` desde el sistema de archivos.
2. WHEN el usuario selecciona un archivo `.xlsx`, THE Excel_Loader SHALL leer las primeras tres filas del archivo para construir el Esquema_Columnas (fila 1 como nombres de columna, fila 2 como Tipo_Dato de cada columna, y fila 3 como Ejemplo_Valor de cada columna) y convertir el contenido completo del archivo a Formato_Interno (DataFrame) para todo procesamiento posterior.
3. IF el archivo `.xlsx` cargado tiene más de 8 columnas, THEN THE Excel_Loader SHALL rechazar el archivo y mostrar un mensaje de error indicando que el archivo supera el límite de 8 columnas permitido en esta versión, sin alterar el Archivo_Excel previamente cargado.
4. IF el archivo `.xlsx` cargado tiene la fila 1 vacía o sin ningún nombre de columna válido, THEN THE Excel_Loader SHALL rechazar el archivo y mostrar un mensaje de error indicando que no se encontraron nombres de columna en la primera fila, sin alterar el Archivo_Excel previamente cargado.
5. IF el archivo `.xlsx` cargado tiene la fila 2 vacía para alguna columna, THEN THE Excel_Loader SHALL rechazar el archivo y mostrar un mensaje de error indicando que faltan los tipos de dato en la fila 2 para las columnas afectadas, sin alterar el Archivo_Excel previamente cargado.
6. IF el archivo `.xlsx` cargado tiene la fila 3 vacía para alguna columna, THEN THE Excel_Loader SHALL rechazar el archivo y mostrar un mensaje de error indicando que faltan los ejemplos de valor en la fila 3 para las columnas afectadas, sin alterar el Archivo_Excel previamente cargado.
7. IF el usuario selecciona un archivo que no tiene la extensión `.xlsx`, THEN THE Excel_Loader SHALL rechazar el archivo y mostrar un mensaje de error indicando que el formato no es compatible, sin alterar el Archivo_Excel previamente cargado.
8. WHILE un Archivo_Excel válido está cargado, THE Aplicacion SHALL mantener el Formato_Interno (DataFrame) y el Esquema_Columnas disponibles para todas las operaciones de grabación y extracción de datos.
9. WHEN el Excel_Loader valida exitosamente un Archivo_Excel, THE Excel_Loader SHALL convertir el contenido del archivo a Formato_Interno (DataFrame en memoria) y descartar la referencia directa al archivo .xlsx, utilizando únicamente el Formato_Interno para todas las operaciones subsiguientes de la Aplicacion.
10. WHEN el usuario carga un Archivo_Excel nuevo mientras ya existe uno cargado, THE Excel_Loader SHALL reemplazar el Archivo_Excel anterior, actualizar el Esquema_Columnas y el Formato_Interno con el nuevo archivo y mostrar la Pantalla_Esquema nuevamente para confirmación.

---

### Requirement 2: Pantalla de confirmación del esquema

**User Story:** Como usuario, quiero ver el esquema detectado de mi archivo Excel (nombres de columna, tipos de dato y ejemplos) antes de empezar a grabar, para verificar que la aplicación interpretó correctamente mi plantilla.

#### Acceptance Criteria

1. WHEN el Excel_Loader construye el Esquema_Columnas con éxito, THE Aplicacion SHALL mostrar la Pantalla_Esquema antes de habilitar los controles de grabación.
2. THE Pantalla_Esquema SHALL mostrar una tabla con una fila por cada columna del Esquema_Columnas, indicando: número de columna, nombre, Tipo_Dato y Ejemplo_Valor.
3. THE Pantalla_Esquema SHALL mostrar un botón "Confirmar" que permita al usuario aceptar el esquema y continuar.
4. WHEN el usuario presiona el botón "Confirmar" en la Pantalla_Esquema, THE Aplicacion SHALL cerrar la Pantalla_Esquema y habilitar los controles de grabación de audio en la Pantalla_Principal.
5. THE Pantalla_Esquema SHALL mostrar un botón "Cambiar archivo" que permita al usuario regresar al selector de archivo sin continuar con el esquema actual.
6. WHEN el usuario presiona el botón "Cambiar archivo" en la Pantalla_Esquema, THE Aplicacion SHALL cerrar la Pantalla_Esquema, descartar el Archivo_Excel actual y presentar nuevamente el control de carga de archivos en la Pantalla_Principal.

---

### Requirement 3: Descripción contextual del Excel

**User Story:** Como usuario, quiero poder escribir un párrafo explicando qué es mi Excel, su historia y lo que contiene, para que el LLM tenga mejor contexto al extraer datos de mis narraciones de audio.

#### Acceptance Criteria

1. THE Aplicacion SHALL presentar un campo de texto multilínea en la Pantalla_Esquema (o en un paso previo a la confirmación) donde el usuario pueda ingresar el Contexto_Excel.
2. THE Aplicacion SHALL validar que el Contexto_Excel no exceda el límite de una hoja de texto (máximo 3000 caracteres).
3. IF el Contexto_Excel ingresado excede los 3000 caracteres, THEN THE Aplicacion SHALL mostrar un mensaje indicando que el texto supera el límite permitido y no permitir continuar hasta que se reduzca.
4. THE Aplicacion SHALL validar que el Contexto_Excel tenga una extensión mínima suficiente (al menos 50 caracteres) para proveer contexto útil al LLM.
5. IF el Contexto_Excel tiene menos de 50 caracteres, THEN THE Aplicacion SHALL mostrar un mensaje indicando que la descripción es demasiado corta y solicitar al usuario que la amplíe.
6. WHEN el usuario confirma el Esquema_Columnas y ha proporcionado un Contexto_Excel válido, THE Aplicacion SHALL enviar el Contexto_Excel junto con el Esquema_Columnas y los datos de ejemplo (fila 3) al LLM para generar el Contexto_Enriquecido.
7. WHEN el LLM genera el Contexto_Enriquecido, THE Aplicacion SHALL almacenar internamente el Contexto_Enriquecido y utilizarlo como contexto definitivo para todas las operaciones de extracción de campos subsiguientes, descartando el Contexto_Excel original del flujo de procesamiento.
8. WHILE el LLM está generando el Contexto_Enriquecido, THE Aplicacion SHALL mostrar un indicador de progreso y no permitir avanzar a la grabación de audio hasta que el proceso finalice.
9. IF ocurre un error al generar el Contexto_Enriquecido, THEN THE Aplicacion SHALL mostrar un mensaje de error descriptivo y permitir al usuario reintentar o editar el Contexto_Excel antes de continuar.
