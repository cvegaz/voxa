/**
 * Represents a single extracted value mapped to a column.
 */
export interface RecordValue {
  columnName: string;
  value: string;
}

/**
 * Request body for POST /api/extraction/process.
 */
export interface ExtractionRequest {
  sessionId: string;
  transcribedText: string;
}

/**
 * Response returned by POST /api/extraction/process on successful extraction.
 */
export interface ExtractionResult {
  extractionId: string;
  record: RecordValue[];
  rowNumber: number;
}

/**
 * Represents a single extraction record stored in the backend.
 */
export interface ExtractionRecord {
  extractionId: string;
  rowNumber: number;
  record: RecordValue[];
  transcribedText: string;
  createdAt: string;
}

/**
 * Response returned by GET /api/extraction/records/{session_id}.
 */
export interface RecordsResponse {
  records: ExtractionRecord[];
  totalRows: number;
}

/**
 * Standard error response from the extraction API.
 */
export interface ExtractionApiErrorResponse {
  detail: string;
  errorCode: string;
}

/**
 * Known error codes returned by the extraction backend endpoints.
 */
export type ExtractionErrorCode =
  | 'EMPTY_TRANSCRIPTION'
  | 'SESSION_NOT_FOUND'
  | 'SESSION_NOT_CONFIRMED'
  | 'LLM_UNAVAILABLE'
  | 'LLM_INVALID_RESPONSE'
  | 'LLM_EMPTY_RESPONSE'
  | 'FILE_WRITE_ERROR'
  | 'FILE_NOT_FOUND'
  | 'DATABASE_ERROR';

/**
 * Typed error class for extraction API errors with user-friendly messages.
 */
export class ExtractionApiError extends Error {
  public readonly statusCode: number;
  public readonly errorCode: ExtractionErrorCode | string;
  public readonly userMessage: string;

  constructor(statusCode: number, errorCode: string, detail: string) {
    super(detail);
    this.name = 'ExtractionApiError';
    this.statusCode = statusCode;
    this.errorCode = errorCode;
    this.userMessage = mapExtractionErrorToUserMessage(statusCode, errorCode, detail);
  }
}

/**
 * Maps backend error responses to user-friendly messages in Spanish.
 */
function mapExtractionErrorToUserMessage(
  statusCode: number,
  errorCode: string,
  detail: string
): string {
  switch (errorCode) {
    case 'EMPTY_TRANSCRIPTION':
      return 'El texto transcrito está vacío. Grabe audio antes de extraer datos.';
    case 'SESSION_NOT_FOUND':
      return 'La sesión no fue encontrada. Puede que haya expirado.';
    case 'SESSION_NOT_CONFIRMED':
      return 'La sesión no ha sido confirmada. Confirme el esquema antes de extraer datos.';
    case 'LLM_UNAVAILABLE':
      return 'El servicio de extracción no está disponible en este momento. Intente de nuevo.';
    case 'LLM_INVALID_RESPONSE':
      return 'Error al procesar la extracción. Intente de nuevo.';
    case 'LLM_EMPTY_RESPONSE':
      return 'El servicio no generó una respuesta válida. Intente de nuevo.';
    case 'FILE_WRITE_ERROR':
      return 'Error al escribir en el archivo Excel. Intente de nuevo.';
    case 'FILE_NOT_FOUND':
      return 'El archivo Excel no fue encontrado. Cargue un nuevo archivo.';
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
