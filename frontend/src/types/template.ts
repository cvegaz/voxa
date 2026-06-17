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
 * Maps backend error responses to user-friendly messages in Spanish.
 */
function mapErrorToUserMessage(
  statusCode: number,
  errorCode: string,
  detail: string
): string {
  switch (errorCode) {
    case 'INVALID_EXTENSION':
      return 'El archivo seleccionado no es compatible. Solo se aceptan archivos .xlsx.';
    case 'TOO_MANY_COLUMNS':
      return 'El archivo supera el límite de 8 columnas permitido en esta versión.';
    case 'EMPTY_HEADER_ROW':
      return 'No se encontraron nombres de columna en la primera fila del archivo.';
    case 'MISSING_DATA_TYPES':
      return 'Faltan los tipos de dato en la fila 2 para algunas columnas.';
    case 'MISSING_EXAMPLES':
      return 'Faltan los ejemplos de valor en la fila 3 para algunas columnas.';
    case 'UNREADABLE_FILE':
      return 'El archivo está corrupto o no se puede leer. Intente con otro archivo.';
    case 'CONTEXT_TOO_SHORT':
      return 'La descripción es demasiado corta. Escriba al menos 50 caracteres.';
    case 'CONTEXT_TOO_LONG':
      return 'La descripción supera el límite de 3000 caracteres.';
    case 'LLM_UNAVAILABLE':
      return 'El servicio de procesamiento no está disponible en este momento. Intente de nuevo.';
    case 'LLM_INVALID_RESPONSE':
      return 'Error al procesar el contexto. Intente de nuevo.';
    case 'SESSION_NOT_FOUND':
      return 'La sesión no fue encontrada. Puede que haya expirado.';
    case 'DATABASE_ERROR':
      return 'Error interno del servidor. Intente de nuevo más tarde.';
    default:
      break;
  }

  // Fallback based on status code ranges
  if (statusCode === 422) {
    return detail || 'Error de validación. Revise los datos ingresados.';
  }
  if (statusCode === 404) {
    return 'El recurso solicitado no fue encontrado.';
  }
  if (statusCode >= 500) {
    return 'Error del servidor. Intente de nuevo más tarde.';
  }

  return detail || 'Ha ocurrido un error inesperado.';
}
