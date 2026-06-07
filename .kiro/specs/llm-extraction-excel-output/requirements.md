# Requirements Document

## Introduction

Este módulo recibe el texto transcrito del módulo `audio-transcription-controls` y, usando el Esquema_Columnas confirmado por `excel-template-loader`, lo analiza mediante un modelo de lenguaje (LLM) para extraer los valores de cada campo. Los valores extraídos se insertan como una nueva fila en el archivo Excel y se muestran en tiempo real al usuario en una vista tabular al final de la pantalla principal.

## Glossary

- **Aplicacion**: El sistema de escritorio/web descrito en este documento.
- **Esquema_Columnas**: Estructura detectada del archivo Excel activo (nombre, Tipo_Dato y Ejemplo_Valor por columna). Provista por el módulo `excel-template-loader`.
- **Tipo_Dato**: Formato esperado del valor a extraer para una columna (ej: `texto`, `número entero`, `fecha DD/MM/YYYY`, `booleano`).
- **Ejemplo_Valor**: Ilustración del tipo de contenido que puede aparecer en una narración de audio para un campo dado.
- **Texto_Transcrito**: Texto de entrada proveniente del módulo `audio-transcription-controls`.
- **LLM_Processor**: Componente que analiza el Texto_Transcrito usando el Esquema_Columnas para extraer los valores correspondientes a cada campo.
- **Registro**: Conjunto de valores extraídos correspondientes a una fila del Archivo_Excel, con un valor (o vacío) por cada columna del Esquema_Columnas.
- **Archivo_Excel**: Archivo `.xlsx` activo cargado por el módulo `excel-template-loader`. Los datos reales se añaden a partir de la fila 4.
- **Vista_Excel**: Componente que muestra el contenido actual del Archivo_Excel en la interfaz de usuario.
- **Pantalla_Principal**: Interfaz principal de la Aplicacion donde se realizan todas las interacciones del usuario.

---

## Requirements

### Requirement 1: Extracción de campos mediante LLM

**User Story:** Como usuario, quiero que la aplicación analice automáticamente el texto transcrito para extraer los datos correspondientes a las columnas de mi archivo Excel, usando los tipos de dato y ejemplos definidos en la plantilla para mejorar la precisión de la extracción.

#### Acceptance Criteria

1. WHEN el LLM_Processor recibe el Texto_Transcrito, THE LLM_Processor SHALL usar el Esquema_Columnas activo — incluyendo el nombre, Tipo_Dato y Ejemplo_Valor de cada columna — para construir el contexto de extracción enviado al modelo de lenguaje.
2. WHEN el LLM_Processor analiza el Texto_Transcrito, THE LLM_Processor SHALL intentar identificar un valor para cada campo del Esquema_Columnas, usando el Tipo_Dato como restricción de formato y el Ejemplo_Valor como referencia del tipo de contenido esperado.
3. WHEN el LLM_Processor completa el análisis del Texto_Transcrito, THE LLM_Processor SHALL construir un Registro con los valores extraídos, asignando un valor vacío a cualquier campo del Esquema_Columnas que no haya podido identificar.
4. IF el LLM_Processor no puede identificar el valor de algún campo del Registro, THEN THE LLM_Processor SHALL asignar un valor vacío a ese campo y continuar con la construcción del Registro.
5. IF el LLM_Processor recibe un Texto_Transcrito vacío, THEN THE Aplicacion SHALL mostrar un mensaje de error indicando que el texto no contiene información procesable y preservar el cuadro de texto en su estado actual.
6. IF ocurre cualquier fallo durante el procesamiento del LLM, incluyendo errores de comunicación o errores de procesamiento interno, THEN THE Aplicacion SHALL mostrar un mensaje de error indicando la causa del fallo y preservar el Texto_Transcrito en el cuadro de texto para que el usuario pueda reintentar.

---

### Requirement 2: Inserción y guardado en el archivo Excel

**User Story:** Como usuario, quiero que los datos extraídos se guarden automáticamente en el archivo Excel, para acumular todos los registros en el mismo archivo que cargué como plantilla.

#### Acceptance Criteria

1. WHEN el LLM_Processor construye un Registro, THE Aplicacion SHALL añadir el Registro como una nueva fila al Archivo_Excel a partir de la fila 4, respetando el orden de columnas del Esquema_Columnas.
2. WHEN el Archivo_Excel es actualizado con un nuevo Registro, THE Aplicacion SHALL guardar los cambios en el Archivo_Excel en disco, sobreescribiendo el archivo existente.
3. IF ocurre un error al guardar el Archivo_Excel en disco, THEN THE Aplicacion SHALL mostrar un mensaje de error indicando la causa del fallo y que el Registro fue procesado pero no guardado en el archivo.

---

### Requirement 3: Vista del Excel en tiempo real

**User Story:** Como usuario, quiero ver en tiempo real cómo se va llenando el Excel con los registros añadidos, para poder verificar que los datos se están guardando correctamente.

#### Acceptance Criteria

1. THE Vista_Excel SHALL mostrar el contenido actual del Archivo_Excel en una tabla al final de la Pantalla_Principal, excluyendo las tres filas de cabecera de la plantilla.
2. WHEN un nuevo Registro es añadido al Archivo_Excel, THE Vista_Excel SHALL actualizar su contenido para reflejar la nueva fila añadida en un plazo máximo de 2 segundos.
3. WHEN el módulo `excel-template-loader` confirma un Archivo_Excel válido, THE Vista_Excel SHALL mostrar todas las filas de datos existentes del archivo (fila 4 en adelante), incluyendo registros previamente guardados.
4. WHILE el LLM_Processor está procesando el Texto_Transcrito, THE Vista_Excel SHALL mantener su contenido actual sin cambios hasta que el Registro sea añadido como nueva fila al Archivo_Excel.
