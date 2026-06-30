import { localized } from '../i18n/LanguageContext';

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
  /** Maximum records allowed before the session auto-finalizes. */
  maxRows: number;
  /** Whether the session is closed (manually finalized or cap reached). */
  finalized: boolean;
}

/**
 * Response returned by POST /api/extraction/finalize/{session_id}.
 */
export interface FinalizeResponse {
  status: string;
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
  | 'SESSION_FINALIZED'
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
 * Maps backend error responses to user-friendly messages in the active UI
 * language (Spanish or English).
 */
function mapExtractionErrorToUserMessage(
  statusCode: number,
  errorCode: string,
  detail: string
): string {
  switch (errorCode) {
    case 'EMPTY_TRANSCRIPTION':
      return localized(
        'El texto transcrito está vacío. Grabe audio antes de extraer datos.',
        'The transcribed text is empty. Record audio before extracting data.'
      );
    case 'SESSION_NOT_FOUND':
      return localized(
        'La sesión no fue encontrada. Puede que haya expirado.',
        'The session was not found. It may have expired.'
      );
    case 'SESSION_NOT_CONFIRMED':
      return localized(
        'La sesión no ha sido confirmada. Confirme el esquema antes de extraer datos.',
        'The session has not been confirmed. Confirm the schema before extracting data.'
      );
    case 'SESSION_FINALIZED':
      return localized(
        'La sesión ya fue finalizada. Descargue el Excel o cargue una nueva plantilla.',
        'The session is already finalized. Download the Excel or upload a new template.'
      );
    case 'LLM_UNAVAILABLE':
      return localized(
        'El servicio de extracción no está disponible en este momento. Intente de nuevo.',
        'The extraction service is unavailable right now. Please try again.'
      );
    case 'LLM_INVALID_RESPONSE':
      return localized(
        'Error al procesar la extracción. Intente de nuevo.',
        'Error processing the extraction. Please try again.'
      );
    case 'LLM_EMPTY_RESPONSE':
      return localized(
        'El servicio no generó una respuesta válida. Intente de nuevo.',
        'The service did not produce a valid response. Please try again.'
      );
    case 'FILE_WRITE_ERROR':
      return localized(
        'Error al escribir en el archivo Excel. Intente de nuevo.',
        'Error writing to the Excel file. Please try again.'
      );
    case 'FILE_NOT_FOUND':
      return localized(
        'El archivo Excel no fue encontrado. Cargue un nuevo archivo.',
        'The Excel file was not found. Upload a new file.'
      );
    case 'DATABASE_ERROR':
      // Surface the backend detail when present: a discarded detail is exactly
      // what masked the original file_path crash (ADR-0013).
      return detail || localized(
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
    return detail || localized(
      'Error del servidor. Intente de nuevo más tarde.',
      'Server error. Please try again later.'
    );
  }

  return detail || localized(
    'Ha ocurrido un error inesperado.',
    'An unexpected error occurred.'
  );
}
