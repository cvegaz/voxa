import { localized } from '../i18n/LanguageContext';

/**
 * Represents a single column definition extracted from the Excel template.
 * Maps to the schema detected from rows 1-3 of the uploaded file.
 */
export interface ColumnDef {
  index: number;
  name: string;
  dataType: string;
  exampleValue: string;
}

/**
 * The complete column schema extracted from the template file.
 * Contains between 1 and 8 column definitions.
 */
export interface ColumnSchema {
  columns: ColumnDef[];
}

/**
 * Response returned by POST /api/templates/upload on successful file upload.
 */
export interface UploadResponse {
  sessionId: string;
  schema: ColumnSchema;
  fileName: string;
}

/**
 * Request body for POST /api/templates/confirm.
 */
export interface ConfirmRequest {
  sessionId: string;
  context: string;
}

/**
 * Response returned by POST /api/templates/confirm on successful enrichment.
 */
export interface ConfirmResponse {
  enrichedContext: string;
}

/**
 * Response from GET /api/templates/active representing the current active session.
 */
export interface ActiveSessionResponse {
  sessionId: string;
  schema: ColumnSchema;
  enrichedContext: string;
  fileName: string;
  confirmedAt: string;
}

/**
 * Standard error response from the backend API.
 */
export interface ApiErrorResponse {
  detail: string;
  errorCode: string;
}

/**
 * Known error codes returned by the backend.
 */
export type TemplateErrorCode =
  | 'INVALID_EXTENSION'
  | 'TOO_MANY_COLUMNS'
  | 'EMPTY_HEADER_ROW'
  | 'MISSING_DATA_TYPES'
  | 'MISSING_EXAMPLES'
  | 'UNREADABLE_FILE'
  | 'CONTEXT_TOO_SHORT'
  | 'CONTEXT_TOO_LONG'
  | 'LLM_UNAVAILABLE'
  | 'LLM_INVALID_RESPONSE'
  | 'SESSION_NOT_FOUND'
  | 'DATABASE_ERROR';

/**
 * Typed error class for template API errors with user-friendly messages.
 */
export class TemplateApiError extends Error {
  public readonly statusCode: number;
  public readonly errorCode: TemplateErrorCode | string;
  public readonly userMessage: string;

  constructor(statusCode: number, errorCode: string, detail: string) {
    super(detail);
    this.name = 'TemplateApiError';
    this.statusCode = statusCode;
    this.errorCode = errorCode;
    this.userMessage = mapErrorToUserMessage(statusCode, errorCode, detail);
  }
}

/**
 * Maps backend error responses to user-friendly messages in the active UI
 * language (Spanish or English).
 */
function mapErrorToUserMessage(
  statusCode: number,
  errorCode: string,
  detail: string
): string {
  switch (errorCode) {
    case 'INVALID_EXTENSION':
      return localized(
        'El archivo seleccionado no es compatible. Solo se aceptan archivos .xlsx.',
        'The selected file is not supported. Only .xlsx files are accepted.'
      );
    case 'TOO_MANY_COLUMNS':
      return localized(
        'El archivo supera el límite de 8 columnas permitido en esta versión.',
        'The file exceeds the 8-column limit allowed in this version.'
      );
    case 'EMPTY_HEADER_ROW':
      return localized(
        'No se encontraron nombres de columna en la primera fila del archivo.',
        'No column names were found in the first row of the file.'
      );
    case 'MISSING_DATA_TYPES':
      return localized(
        'Faltan los tipos de dato en la fila 2 para algunas columnas.',
        'Data types are missing in row 2 for some columns.'
      );
    case 'MISSING_EXAMPLES':
      return localized(
        'Faltan los ejemplos de valor en la fila 3 para algunas columnas.',
        'Example values are missing in row 3 for some columns.'
      );
    case 'UNREADABLE_FILE':
      return localized(
        'El archivo está corrupto o no se puede leer. Intente con otro archivo.',
        'The file is corrupt or cannot be read. Try a different file.'
      );
    case 'CONTEXT_TOO_SHORT':
      return localized(
        'La descripción es demasiado corta. Escriba al menos 50 caracteres.',
        'The description is too short. Write at least 50 characters.'
      );
    case 'CONTEXT_TOO_LONG':
      return localized(
        'La descripción supera el límite de 3000 caracteres.',
        'The description exceeds the 3000-character limit.'
      );
    case 'LLM_UNAVAILABLE':
      return localized(
        'El servicio de procesamiento no está disponible en este momento. Intente de nuevo.',
        'The processing service is unavailable right now. Please try again.'
      );
    case 'LLM_INVALID_RESPONSE':
      return localized(
        'Error al procesar el contexto. Intente de nuevo.',
        'Error processing the context. Please try again.'
      );
    case 'SESSION_NOT_FOUND':
      return localized(
        'La sesión no fue encontrada. Puede que haya expirado.',
        'The session was not found. It may have expired.'
      );
    case 'DATABASE_ERROR':
      return localized(
        'Error interno del servidor. Intente de nuevo más tarde.',
        'Internal server error. Please try again later.'
      );
    default:
      break;
  }

  // Fallback based on status code ranges
  if (statusCode === 422) {
    return detail || localized(
      'Error de validación. Revise los datos ingresados.',
      'Validation error. Check the entered data.'
    );
  }
  if (statusCode === 404) {
    return localized(
      'El recurso solicitado no fue encontrado.',
      'The requested resource was not found.'
    );
  }
  if (statusCode >= 500) {
    return localized(
      'Error del servidor. Intente de nuevo más tarde.',
      'Server error. Please try again later.'
    );
  }

  return detail || localized(
    'Ha ocurrido un error inesperado.',
    'An unexpected error occurred.'
  );
}
