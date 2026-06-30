import { localized } from '../i18n/LanguageContext';

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
 * Maps backend error responses to user-friendly messages in the active UI
 * language (Spanish or English).
 */
function mapTranscriptionErrorToUserMessage(
  statusCode: number,
  errorCode: string,
  detail: string
): string {
  switch (errorCode) {
    case 'AUDIO_TOO_SHORT':
      return localized(
        'El audio es demasiado corto. Grabe al menos 1 segundo.',
        'The audio is too short. Record at least 1 second.'
      );
    case 'AUDIO_TOO_LONG':
      return localized(
        'El audio es demasiado largo. Máximo 20 segundos.',
        'The audio is too long. Maximum 20 seconds.'
      );
    case 'UNSUPPORTED_AUDIO_FORMAT':
      return localized(
        'El formato de audio no es compatible.',
        'The audio format is not supported.'
      );
    case 'EMPTY_AUDIO_FILE':
      return localized('El archivo de audio está vacío.', 'The audio file is empty.');
    case 'WHISPER_UNAVAILABLE':
      return localized(
        'El servicio de transcripción no está disponible. Intente de nuevo.',
        'The transcription service is unavailable. Please try again.'
      );
    case 'WHISPER_EMPTY_RESPONSE':
      return localized(
        'No se pudo transcribir el audio. Intente grabar de nuevo.',
        'The audio could not be transcribed. Try recording again.'
      );
    case 'WHISPER_NO_SPEECH':
      return localized(
        'No se detectó habla en el audio. Intente grabar de nuevo.',
        'No speech was detected in the audio. Try recording again.'
      );
    case 'EMPTY_TRANSCRIPTION':
      return localized('El texto no puede estar vacío.', 'The text cannot be empty.');
    case 'NO_CONFIRMED_SCHEMA':
      return localized(
        'Primero debe cargar y confirmar un archivo Excel.',
        'You must upload and confirm an Excel file first.'
      );
    case 'SESSION_NOT_FOUND':
      return localized(
        'La sesión de transcripción no fue encontrada.',
        'The transcription session was not found.'
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
