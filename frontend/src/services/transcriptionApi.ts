import type {
  TranscribeResponse,
  AcceptResponse,
  ResetResponse,
  TranscriptionApiErrorResponse,
} from '../types/transcription';
import { TranscriptionApiError } from '../types/transcription';

/**
 * Base URL for the API. Defaults to '/api' which works with Vite proxy in dev,
 * or can be overridden via VITE_API_BASE_URL environment variable.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

/** Timeout for transcription requests (30 seconds) */
const TRANSCRIBE_TIMEOUT_MS = 30_000;

/** Timeout for acceptance requests (60 seconds) */
const ACCEPT_TIMEOUT_MS = 60_000;

/** Timeout for reset requests (15 seconds) */
const RESET_TIMEOUT_MS = 15_000;

/**
 * Parses the response body and throws a TranscriptionApiError if the response is not OK.
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    if (response.status === 204) {
      return undefined as T;
    }
    return response.json() as Promise<T>;
  }

  // Try to parse error response body
  let errorCode = 'UNKNOWN_ERROR';
  let detail = `Request failed with status ${response.status}`;

  try {
    const errorBody: TranscriptionApiErrorResponse = await response.json();
    if (errorBody.errorCode) {
      errorCode = errorBody.errorCode;
    }
    if (errorBody.detail) {
      detail = errorBody.detail;
    }
  } catch {
    // If JSON parsing fails, use defaults based on status
  }

  throw new TranscriptionApiError(response.status, errorCode, detail);
}

/**
 * Creates a fetch request with an AbortController timeout.
 */
function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  return fetch(url, {
    ...options,
    signal: controller.signal,
  }).catch((error: unknown) => {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new TranscriptionApiError(
        408,
        'TIMEOUT',
        'La solicitud ha superado el tiempo de espera. Intente de nuevo.'
      );
    }
    throw new TranscriptionApiError(
      0,
      'NETWORK_ERROR',
      'Error de conexión. Verifique su conexión a internet e intente de nuevo.'
    );
  }).finally(() => {
    clearTimeout(timeoutId);
  });
}

/**
 * API client service for audio transcription endpoints.
 *
 * Provides methods to transcribe audio, accept transcriptions,
 * and reset transcription sessions.
 */
export const transcriptionApi = {
  /**
   * Sends an audio blob to the backend for transcription via Whisper API.
   *
   * @param file - The audio blob to transcribe
   * @param duration - The duration of the recording in seconds
   * @returns Transcription response containing transcription ID and transcribed text
   * @throws TranscriptionApiError on validation failure (422), Whisper error (502), or timeout
   *
   * Timeout: 30 seconds
   */
  async transcribeAudio(file: Blob, duration: number): Promise<TranscribeResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('duration', String(duration));

    const response = await fetchWithTimeout(
      `${API_BASE_URL}/transcriptions/transcribe`,
      {
        method: 'POST',
        body: formData,
      },
      TRANSCRIBE_TIMEOUT_MS
    );

    return handleResponse<TranscribeResponse>(response);
  },

  /**
   * Accepts a transcription with the final (possibly edited) text.
   * Triggers downstream LLM extraction processing.
   *
   * @param transcriptionId - The transcription session ID
   * @param text - The final text to accept (may have been edited by the user)
   * @returns Accept response with status 'accepted'
   * @throws TranscriptionApiError on validation failure (422), missing schema (409), or session not found (404)
   *
   * Timeout: 60 seconds (accounts for downstream LLM processing)
   */
  async acceptTranscription(transcriptionId: string, text: string): Promise<AcceptResponse> {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/transcriptions/accept`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          transcription_id: transcriptionId,
          text,
        }),
      },
      ACCEPT_TIMEOUT_MS
    );

    return handleResponse<AcceptResponse>(response);
  },

  /**
   * Resets a transcription session, marking it as discarded.
   * Clears the transcription text and restores the recorder to idle state.
   *
   * @param transcriptionId - The transcription session ID to reset
   * @returns Reset response with status 'reset'
   * @throws TranscriptionApiError on session not found (404) or server error
   *
   * Timeout: 15 seconds
   */
  async resetTranscription(transcriptionId: string): Promise<ResetResponse> {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/transcriptions/reset`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          transcription_id: transcriptionId,
        }),
      },
      RESET_TIMEOUT_MS
    );

    return handleResponse<ResetResponse>(response);
  },
};
