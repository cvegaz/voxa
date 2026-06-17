# TODO — Mejoras para futuras versiones

## Pendientes de discusión e implementación

### 1. Confirmación del Registro antes de guardar
- Mostrar al usuario los campos extraídos por el LLM antes de insertarlos en el Excel
- Permitir editar valores individuales antes de confirmar la inserción
- Decidir si es un paso obligatorio o una opción configurable

### 2. Idioma de la narración
- Definir si la app soportará solo español o múltiples idiomas
- Afecta la configuración del Transcriptor y los prompts del LLM
- Considerar selección de idioma en la carga o detección automática

### 3. Múltiples registros en un solo audio
- Permitir que una sola narración genere más de una fila en el Excel
- Ejemplo: "Juan tiene 30 años; María tiene 25"
- Definir si el LLM detecta automáticamente múltiples registros o si siempre es 1 audio = 1 fila

### 4. Persistencia del Contexto_Enriquecido
- Guardar el Contexto_Enriquecido asociado al archivo Excel para no perderlo al cerrar la app
- Opciones: guardarlo como metadato en el mismo .xlsx, como archivo .json adjunto, o en almacenamiento local de la app
- Evaluar si al reabrir se reutiliza sin pedir la descripción al usuario otra vez

### 5. Dockerizar la aplicación completa
- Crear docker-compose con servicios: backend Python, frontend React, PostgreSQL
- Facilitar despliegue en cualquier máquina sin configuración manual
- Incluir volúmenes para persistencia de datos y archivos Excel

### 6. Reemplazar Claude por modelo local (Ollama)
- Permitir usar un LLM local (LLaMA/Mistral vía Ollama) en lugar de Claude API
- Eliminar dependencia de API externa y costos asociados
- Evaluar calidad de extracción con modelos locales vs Claude
