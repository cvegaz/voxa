/**
 * Translation catalog for Voxa's UI (Spanish + English).
 *
 * Keys are flat, dot-namespaced by area. Values may contain `{placeholder}`
 * tokens that the `t()` helper (see LanguageContext) substitutes at render time.
 *
 * Spanish is the default/source language; every key must exist in both maps.
 */

export type Language = 'es' | 'en';

export const SUPPORTED_LANGUAGES: Language[] = ['es', 'en'];
export const DEFAULT_LANGUAGE: Language = 'es';

export type TranslationKey = keyof typeof messages.es;

export const messages = {
  es: {
    // App shell
    'app.tagline': 'Captura de datos por voz con extracción mediante inteligencia artificial',
    'app.loading': 'Cargando…',
    'app.footer': 'Voxa · Transcripción y extracción potenciadas por IA',

    // Language switcher (tooltips describe the target language)
    'lang.switchToEs': 'Usar Voxa en español',
    'lang.switchToEn': 'Use Voxa in English',
    'lang.groupLabel': 'Idioma de la aplicación',

    // File upload
    'upload.dropPrefix': 'Arrastre un archivo aquí o ',
    'upload.dropHighlight': 'haga clic para seleccionar',
    'upload.hint': 'Solo archivos .xlsx (máximo 8 columnas)',
    'upload.processing': 'Procesando archivo…',
    'upload.ariaUploading': 'Subiendo archivo',
    'upload.ariaDropzone': 'Zona de carga de archivos. Haga clic o arrastre un archivo .xlsx aquí.',
    'upload.invalidExtension': 'El archivo seleccionado no es compatible. Solo se aceptan archivos .xlsx.',
    'upload.ariaRetry': 'Reintentar carga de archivo',

    // Schema confirmation
    'schema.title': 'Esquema detectado',
    'schema.ariaTable': 'Esquema de columnas del archivo cargado',
    'schema.colName': 'Nombre',
    'schema.colType': 'Tipo de Dato',
    'schema.colExample': 'Ejemplo',
    'schema.confirm': 'Confirmar',
    'schema.changeFile': 'Cambiar archivo',

    // Context input
    'context.label': 'Descripción del contexto del Excel',
    'context.placeholder': 'Describa qué es este Excel, su historia y lo que contiene (mínimo 50 caracteres)...',
    'context.counter': '{count}/{max} caracteres',
    'context.tooShort': 'Escriba al menos 50 caracteres ({count} actualmente)',
    'context.tooLong': 'El texto supera el límite de 3000 caracteres',
    'context.confirm': 'Confirmar y Continuar',
    'context.ariaConfirm': 'Confirmar contexto y continuar',
    'context.processing': 'Procesando contexto con inteligencia artificial...',
    'context.success': 'Contexto enriquecido generado exitosamente.',

    // Audio recorder
    'recorder.record': 'Grabar',
    'recorder.stop': 'Detener',
    'recorder.ariaStart': 'Iniciar grabación de audio',
    'recorder.ariaStop': 'Detener grabación',
    'recorder.ariaProcessing': 'Procesando audio',
    'recorder.ariaTimer': 'Tiempo de grabación: {time}',
    'recorder.tooShort': 'El audio es demasiado corto (mínimo 1 segundo)',
    'recorder.permissionDenied': 'Se requiere acceso al micrófono para usar esta funcionalidad.',
    'recorder.deviceError': 'No se pudo acceder al dispositivo de audio.',
    'recorder.bluetoothWarning':
      'Estás usando un micrófono Bluetooth. Por limitaciones del Bluetooth, su calidad de captura es baja y la transcripción puede salir incompleta. Para mejor precisión, usa el micrófono del dispositivo o uno por cable/USB.',

    // Transcription display
    'display.placeholder': 'El texto transcrito aparecerá aquí...',
    'display.ariaTextarea': 'Texto transcrito',
    'display.ariaTranscribing': 'Transcribiendo audio',
    'display.acceptedNotice':
      '✓ Esta narración se agregó a la fila {row}. Revísala contra la tabla; presiona Grabar o Agregar nuevo para continuar.',

    // Control buttons
    'controls.accept': 'Aceptar',
    'controls.addNew': 'Agregar nuevo',
    'controls.ariaAccept': 'Aceptar texto transcrito y enviar para procesamiento',
    'controls.ariaAddNew': 'Agregar nuevo audio descartando el texto actual',
    'controls.errNoText': 'Primero debe grabar y transcribir un audio.',
    'controls.errNoSchema': 'Primero debe cargar y confirmar un archivo Excel.',

    // Extraction status
    'extraction.processing': 'Procesando extracción...',
    'extraction.ariaProcessing': 'Procesando extracción',
    'extraction.success': 'Registro insertado en fila {row}',
    'extraction.ariaSuccess': 'Extracción exitosa',
    'extraction.ariaRetry': 'Reintentar extracción',

    // Vista Excel
    'vista.empty': 'No hay registros aún.',
    'vista.ariaTable': 'Registros del archivo Excel',

    // Session controls
    'session.counter': '{count} / {max} registros',
    'session.capReached': 'Límite de {max} registros alcanzado. La sesión se finalizó.',
    'session.finalized': 'Sesión finalizada.',
    'session.download': 'Descargar Excel',
    'session.ariaDownload': 'Descargar el archivo Excel',
    'session.finalizeAndDownload': 'Finalizar y descargar',
    'session.ariaFinalize': 'Finalizar la sesión y descargar el Excel',

    // Shared
    'common.retry': 'Reintentar',
    'common.unexpectedError': 'Ha ocurrido un error inesperado. Intente de nuevo.',

    // Transcription page (orchestration) errors
    'page.errTranscribe': 'Error al transcribir el audio. Intente de nuevo.',
    'page.errAccept': 'Error al procesar la transcripción. Intente de nuevo.',
    'page.errExtract': 'Error al extraer datos. Intente de nuevo.',
    'page.errDownload': 'Error al descargar el archivo. Intente de nuevo.',
    'page.errFinalize': 'Error al finalizar la sesión. Intente de nuevo.',
  },

  en: {
    'app.tagline': 'Capture data by voice with AI-powered extraction',
    'app.loading': 'Loading…',
    'app.footer': 'Voxa · AI-powered transcription and extraction',

    'lang.switchToEs': 'Usar Voxa en español',
    'lang.switchToEn': 'Use Voxa in English',
    'lang.groupLabel': 'Application language',

    'upload.dropPrefix': 'Drag a file here or ',
    'upload.dropHighlight': 'click to select',
    'upload.hint': 'Only .xlsx files (up to 8 columns)',
    'upload.processing': 'Processing file…',
    'upload.ariaUploading': 'Uploading file',
    'upload.ariaDropzone': 'File upload area. Click or drag an .xlsx file here.',
    'upload.invalidExtension': 'The selected file is not supported. Only .xlsx files are accepted.',
    'upload.ariaRetry': 'Retry file upload',

    'schema.title': 'Detected schema',
    'schema.ariaTable': 'Column schema of the uploaded file',
    'schema.colName': 'Name',
    'schema.colType': 'Data Type',
    'schema.colExample': 'Example',
    'schema.confirm': 'Confirm',
    'schema.changeFile': 'Change file',

    'context.label': 'Description of the Excel context',
    'context.placeholder': 'Describe what this Excel is, its history, and what it contains (minimum 50 characters)...',
    'context.counter': '{count}/{max} characters',
    'context.tooShort': 'Write at least 50 characters ({count} so far)',
    'context.tooLong': 'The text exceeds the 3000-character limit',
    'context.confirm': 'Confirm and Continue',
    'context.ariaConfirm': 'Confirm context and continue',
    'context.processing': 'Processing context with AI...',
    'context.success': 'Enriched context generated successfully.',

    'recorder.record': 'Record',
    'recorder.stop': 'Stop',
    'recorder.ariaStart': 'Start audio recording',
    'recorder.ariaStop': 'Stop recording',
    'recorder.ariaProcessing': 'Processing audio',
    'recorder.ariaTimer': 'Recording time: {time}',
    'recorder.tooShort': 'The audio is too short (minimum 1 second)',
    'recorder.permissionDenied': 'Microphone access is required to use this feature.',
    'recorder.deviceError': 'Could not access the audio device.',
    'recorder.bluetoothWarning':
      'You are using a Bluetooth microphone. Due to Bluetooth limitations, its capture quality is low and the transcription may come out incomplete. For better accuracy, use the device microphone or a wired/USB one.',

    'display.placeholder': 'The transcribed text will appear here...',
    'display.ariaTextarea': 'Transcribed text',
    'display.ariaTranscribing': 'Transcribing audio',
    'display.acceptedNotice':
      '✓ This narration was added to row {row}. Check it against the table; press Record or Add new to continue.',

    'controls.accept': 'Accept',
    'controls.addNew': 'Add new',
    'controls.ariaAccept': 'Accept the transcribed text and send it for processing',
    'controls.ariaAddNew': 'Record new audio, discarding the current text',
    'controls.errNoText': 'You must record and transcribe audio first.',
    'controls.errNoSchema': 'You must upload and confirm an Excel file first.',

    'extraction.processing': 'Processing extraction...',
    'extraction.ariaProcessing': 'Processing extraction',
    'extraction.success': 'Record inserted in row {row}',
    'extraction.ariaSuccess': 'Successful extraction',
    'extraction.ariaRetry': 'Retry extraction',

    'vista.empty': 'No records yet.',
    'vista.ariaTable': 'Excel file records',

    'session.counter': '{count} / {max} records',
    'session.capReached': 'Limit of {max} records reached. The session was finalized.',
    'session.finalized': 'Session finalized.',
    'session.download': 'Download Excel',
    'session.ariaDownload': 'Download the Excel file',
    'session.finalizeAndDownload': 'Finalize and download',
    'session.ariaFinalize': 'Finalize the session and download the Excel',

    'common.retry': 'Retry',
    'common.unexpectedError': 'An unexpected error occurred. Please try again.',

    'page.errTranscribe': 'Error transcribing the audio. Please try again.',
    'page.errAccept': 'Error processing the transcription. Please try again.',
    'page.errExtract': 'Error extracting data. Please try again.',
    'page.errDownload': 'Error downloading the file. Please try again.',
    'page.errFinalize': 'Error finalizing the session. Please try again.',
  },
} satisfies Record<Language, Record<string, string>>;
