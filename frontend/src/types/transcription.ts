/**
 * Response returned by POST /api/transcriptions/transcribe on successful transcription.
 */
export interface TranscribeResponse {
  transcriptionId: string;
  text: string;
}

/**
 * Request body for POST /api/transcriptions/accept.
 */
export interface AcceptRequest {
  transcriptionId: string;
  text: string;
}

/**
 * Response returned by POST /api/transcriptions/accept.
 */
export interface AcceptResponse {
  status: 'accepted';
}

/**
 * Request body for POST /api/transcriptions/reset.
 */
export interface ResetRequest {
  transcriptionId: string;
}

/**
 * Response returned by POST /api/transcriptions/reset.
 */
export interface ResetResponse {
  status: 'reset';
}

/**
 * Represents a transcription session stored in the backend.
 */
export interface TranscriptionSession {
  id: string;
  templateSessionId: string;
  status: 'pending' | 'accepted' | 'discarded';
  originalText: string;
  finalText: string | null;
  durationSeconds: number;
  createdAt: string;
  acceptedAt: string | null;
  discardedAt: string | null;
}

/**
 * Known error codes returned by the transcription backend endpoints.
 */
export type TranscriptionErrorCode =
  | 'AUDIO_TOO_SHORT'
  | 'AUDIO_TOO_LONG'
  | 'UNSUPPORTED_AUDIO_FORMAT'
  | 'EMPTY_AUDIO_FILE'
  | 'WHISPER_UNAVAILABLE'
  | 'WHISPER_EMPTY_RESPONSE'
  | 'WHISPER_NO_SPEECH'
  | 'EMPTY_TRANSCRIPTION'
  | 'NO_CONFIRMED_SCHEMA'
  | 'SESSION_NOT_FOUND'
  | 'DATABASE_ERROR';

/**
 * Standard error response from the transcription API.
 */
export interface TranscriptionApiErrorResponse {
  detail: string;
  errorCode: string;
}

/**
 * Typed error class for transcription API errors with user-friendly messages.
 */
export class TranscriptionApiError extends Error {
  public readonly statusCode: number;
  public readonly errorCode: TranscriptionErrorCode | string;
  public readonly userMessage: string;

  constructor(statusCode: number, errorCode: string, detail: string) {
    super(detail);
    this.name = 'TranscriptionApiError';
    this.statusCode = statusCode;
    this.errorCode = errorCode;
    this.userMessage = mapTranscriptionErrorToUserMessage(statusCode, errorCode, detail);
  }
}

/**
 * Maps backend error responses to user-friendly messages in Spanish.
 */
function mapTranscriptionErrorToUserMessage(
  statusCode: number,
  errorCode: string,
  detail: string
): string {
  switch (errorCode) {
    case 'AUDIO_TOO_SHORT':
      return 'El audio es demasiado corto. Grabe al menos 1 segundo.';
    case 'AUDIO_TOO_LONG':
      return 'El audio es demasiado largo. Máximo 30 segundos.';
    case 'UNSUPPORTED_AUDIO_FORMAT':
      return 'El formato de audio no es compatible.';
    case 'EMPTY_AUDIO_FILE':
      return 'El archivo de audio está vacío.';
    case 'WHISPER_UNAVAILABLE':
      return 'El servicio de transcripción no está disponible. Intente de nuevo.';
    case 'WHISPER_EMPTY_RESPONSE':
      return 'No se pudo transcribir el audio. Intente grabar de nuevo.';
    case 'WHISPER_NO_SPEECH':
      return 'No se detectó habla en el audio. Intente grabar de nuevo.';
    case 'EMPTY_TRANSCRIPTION':
      return 'El texto no puede estar vacío.';
    case 'NO_CONFIRMED_SCHEMA':
      return 'Primero debe cargar y confirmar un archivo Excel.';
    case 'SESSION_NOT_FOUND':
      return 'La sesión de transcripción no fue encontrada.';
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
