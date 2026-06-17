# Requirements Document

## Introduction

Este módulo cubre la captura de audio desde el micrófono del usuario, su transcripción automática a texto, y los controles de la pantalla principal que permiten al usuario aceptar el texto transcrito para procesarlo o descartarlo para iniciar una nueva grabación. Depende de que el módulo `excel-template-loader` haya cargado y confirmado un Esquema_Columnas válido antes de operar.

## Glossary

- **Aplicacion**: El sistema de escritorio/web descrito en este documento.
- **Esquema_Columnas**: Estructura detectada del archivo Excel activo. Provista por el módulo `excel-template-loader`. Debe estar confirmada antes de que este módulo opere.
- **Grabador**: Componente de la interfaz que gestiona la captura de audio desde el micrófono del usuario.
- **Audio**: Señal de voz capturada desde el micrófono del usuario durante una sesión de grabación.
- **Transcriptor**: Componente responsable de convertir el audio grabado en texto legible.
- **Texto_Transcrito**: Texto resultante de la transcripción del audio grabado.
- **LLM_Processor**: Componente del módulo `llm-extraction-excel-output` que recibe el Texto_Transcrito para su análisis. Referenciado aquí solo como destino del flujo.
- **Pantalla_Principal**: Interfaz principal de la Aplicacion donde se realizan todas las interacciones del usuario.

---

## Requirements

### Requirement 1: Grabación de audio

**User Story:** Como usuario, quiero grabar mi voz a través del micrófono, para que la aplicación capture lo que digo y lo procese.

#### Acceptance Criteria

1. THE Grabador SHALL mostrar un botón etiquetado "Grabar" en la Pantalla_Principal.
2. IF el permiso de micrófono no ha sido concedido previamente, WHEN el usuario presiona el botón "Grabar", THE Grabador SHALL solicitar permiso de acceso al micrófono del dispositivo antes de iniciar la captura.
3. WHEN el permiso de micrófono es concedido y el usuario presiona el botón "Grabar", THE Grabador SHALL iniciar la captura de audio desde el micrófono y mostrar un indicador visual que señale que la grabación está activa.
4. WHEN el usuario presiona el botón "Grabar" por segunda vez durante una sesión activa, THE Grabador SHALL detener la captura de audio.
5. WHEN el Grabador detiene la captura de audio, THE Grabador SHALL enviar el Audio al Transcriptor.
6. IF el permiso de acceso al micrófono es denegado, THEN THE Grabador SHALL mostrar un mensaje de error indicando que se requiere acceso al micrófono para usar esta funcionalidad.
7. IF ocurre un error de hardware durante la captura de audio, THEN THE Grabador SHALL detener la grabación y mostrar un mensaje de error que indique que no se pudo acceder al dispositivo de audio.

---

### Requirement 2: Transcripción de audio a texto

**User Story:** Como usuario, quiero que el audio grabado sea convertido automáticamente a texto, para poder revisar lo que dije antes de procesarlo.

#### Acceptance Criteria

1. WHEN el Grabador envía el Audio al Transcriptor, THE Transcriptor SHALL procesar el audio y generar el Texto_Transcrito.
2. WHEN el Transcriptor genera el Texto_Transcrito, THE Aplicacion SHALL mostrar el Texto_Transcrito en un cuadro de texto editable ubicado debajo del botón de grabación en la Pantalla_Principal.
3. WHILE el Transcriptor está procesando el Audio, THE Aplicacion SHALL mostrar un indicador visual de progreso en la Pantalla_Principal, y dicho indicador SHALL desaparecer cuando la transcripción finalice (con éxito o con error).
4. IF el Audio tiene una duración inferior a 1 segundo, THEN THE Transcriptor SHALL rechazar el Audio antes de iniciar la transcripción y mostrar un mensaje indicando que el audio es demasiado corto para ser procesado.
5. IF el Audio tiene una duración superior a 30 segundos, THEN THE Grabador SHALL detener automáticamente la captura de audio y enviar el Audio al Transcriptor con los 30 segundos grabados.
6. IF el Transcriptor no puede procesar el Audio por un error de servicio, THEN THE Aplicacion SHALL mostrar un mensaje de error descriptivo, limpiar el Texto_Transcrito del cuadro de texto y restablecer el Grabador a su estado inicial.
6. THE Aplicacion SHALL permitir al usuario editar manualmente el Texto_Transcrito en el cuadro de texto antes de proceder.

---

### Requirement 3: Controles de la pantalla principal

**User Story:** Como usuario, quiero tener controles para aceptar el texto transcrito o limpiar la pantalla y empezar de nuevo, para gestionar el flujo de entrada de datos.

#### Acceptance Criteria

1. THE Aplicacion SHALL mostrar un botón "Aceptar" en la Pantalla_Principal.
2. THE Aplicacion SHALL mostrar un botón "Agregar nuevo" en la Pantalla_Principal.
3. WHEN el usuario presiona el botón "Aceptar" y existe un Texto_Transcrito no vacío, THE Aplicacion SHALL verificar que existe un Esquema_Columnas confirmado y, si es así, enviar el Texto_Transcrito al LLM_Processor para su análisis.
4. IF el usuario presiona el botón "Aceptar" y no existe un Texto_Transcrito, THEN THE Aplicacion SHALL mostrar un mensaje indicando que primero debe grabar y transcribir un audio.
5. IF el usuario presiona el botón "Aceptar" y no existe un Esquema_Columnas confirmado, THEN THE Aplicacion SHALL mostrar un mensaje indicando que primero debe cargar y confirmar un archivo Excel.
6. WHEN el usuario presiona el botón "Agregar nuevo", THE Aplicacion SHALL limpiar el cuadro de texto del Texto_Transcrito y restablecer el Grabador a su estado inicial, manteniendo el Esquema_Columnas confirmado.
7. WHEN el usuario presiona el botón "Aceptar" y las condiciones son válidas, THE Aplicacion SHALL deshabilitar los botones "Aceptar" y "Agregar nuevo" mientras el LLM_Processor procesa el Texto_Transcrito, y los habilitará nuevamente al completarse el procesamiento.
8. WHEN ocurre un error de transcripción o de grabación, THE Aplicacion SHALL restablecer automáticamente el Grabador a su estado inicial.
