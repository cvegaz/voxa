# Audio Excel Data Entry — Índice del Proyecto

Aplicación para capturar datos mediante narración de audio y guardarlos en un archivo Excel usando un modelo de lenguaje (LLM) para la extracción de campos.

El proyecto está organizado en tres módulos independientes, cada uno con su propio spec de requisitos, diseño y tareas.

## Estructura del proyecto

| Módulo | Descripción |
|--------|-------------|
| **excel-template-loader** | Carga y validación del archivo Excel plantilla, detección del esquema (columnas, tipos de dato, ejemplos) y pantalla de confirmación |
| **audio-transcription-controls** | Grabación de audio desde micrófono, transcripción a texto y controles Aceptar / Agregar nuevo |
| **llm-extraction-excel-output** | Extracción de campos con LLM, inserción de registros en el Excel y vista en tiempo real |

## Flujo general entre módulos

```
excel-template-loader
        ↓  Esquema_Columnas confirmado
audio-transcription-controls
        ↓  Texto_Transcrito aceptado
llm-extraction-excel-output
        ↓  Registro insertado en Archivo_Excel
```

## Dependencias entre módulos

- `audio-transcription-controls` requiere que `excel-template-loader` haya confirmado un Esquema_Columnas válido antes de habilitar los controles de grabación.
- `llm-extraction-excel-output` requiere el Esquema_Columnas de `excel-template-loader` y el Texto_Transcrito de `audio-transcription-controls`.

## Specs

- `.kiro/specs/excel-template-loader/`
- `.kiro/specs/audio-transcription-controls/`
- `.kiro/specs/llm-extraction-excel-output/`
