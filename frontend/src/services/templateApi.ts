import type {
  UploadResponse,
  ConfirmResponse,
  ActiveSessionResponse,
} from '../types/template';
import { TemplateApiError } from '../types/template';
import { localized } from '../i18n/LanguageContext';

/**
 * Base URL for the API. Defaults to '/api' which works with Vite proxy in dev,
 * or can be overridden via VITE_API_BASE_URL environment variable.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

/** Timeout for file upload requests (30 seconds) */
const UPLOAD_TIMEOUT_MS = 30_000;

/** Timeout for confirm/enrichment requests (60 seconds) */
const CONFIRM_TIMEOUT_MS = 60_000;

/** Default timeout for other requests (15 seconds) */
const DEFAULT_TIMEOUT_MS = 15_000;

/**
 * Parses the response body and throws a TemplateApiError if the response is not OK.
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }
    return response.json() as Promise<T>;
  }

  // Try to parse error response body
  let errorCode = 'UNKNOWN_ERROR';
  let detail = `Request failed with status ${response.status}`;

  try {
    const errorBody = await response.json();
    const rawCode: unknown = errorBody?.errorCode;
    const rawDetail: unknown = errorBody?.detail;
    if (typeof rawCode === 'string') {
      errorCode = rawCode;
    }
    // `detail` must be a string before it reaches React. The backend returns a
    // flat string, but we defend against arrays/objects (e.g. raw FastAPI
    // validation errors) so a bad shape can never blank the screen.
    if (typeof rawDetail === 'string') {
      detail = rawDetail;
    } else if (Array.isArray(rawDetail) && typeof rawDetail[0]?.msg === 'string') {
      detail = rawDetail[0].msg;
    }
  } catch {
    // If JSON parsing fails, use defaults based on status
  }

  throw new TemplateApiError(response.status, errorCode, detail);
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
      throw new TemplateApiError(
        408,
        'TIMEOUT',
        localized(
          'La solicitud ha superado el tiempo de espera. Intente de nuevo.',
          'The request timed out. Please try again.'
        )
      );
    }
    throw new TemplateApiError(
      0,
      'NETWORK_ERROR',
      localized(
        'Error de conexión. Verifique su conexión a internet e intente de nuevo.',
        'Connection error. Check your internet connection and try again.'
      )
    );
  }).finally(() => {
    clearTimeout(timeoutId);
  });
}

/**
 * API client service for template management endpoints.
 *
 * Provides methods to upload Excel templates, confirm sessions with context,
 * retrieve active sessions, and delete sessions.
 */
export const templateApi = {
  /**
   * Uploads an Excel template file to the backend for validation and schema extraction.
   *
   * @param file - The .xlsx file to upload
   * @returns Upload response containing session ID, extracted schema, and file name
   * @throws TemplateApiError on validation failure (422) or server error
   *
   * Timeout: 30 seconds
   */
  async uploadTemplate(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetchWithTimeout(
      `${API_BASE_URL}/templates/upload`,
      {
        method: 'POST',
        body: formData,
      },
      UPLOAD_TIMEOUT_MS
    );

    return handleResponse<UploadResponse>(response);
  },

  /**
   * Confirms a template session with user-provided context description.
   * Triggers LLM enrichment of the context on the backend.
   *
   * @param sessionId - The session ID from the upload step
   * @param context - User's context description (50-3000 characters)
   * @returns Confirm response containing the enriched context
   * @throws TemplateApiError on validation failure (422), session not found (404), or LLM error (502)
   *
   * Timeout: 60 seconds (accounts for LLM processing time)
   */
  async confirmTemplate(
    sessionId: string,
    context: string
  ): Promise<ConfirmResponse> {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/templates/confirm`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ sessionId, context }),
      },
      CONFIRM_TIMEOUT_MS
    );

    return handleResponse<ConfirmResponse>(response);
  },

  /**
   * Retrieves the currently active (confirmed) template session.
   *
   * @returns Active session data including schema and enriched context
   * @throws TemplateApiError if no active session exists (404) or server error
   *
   * Timeout: 15 seconds
   */
  async getActiveSession(): Promise<ActiveSessionResponse> {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/templates/active`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      },
      DEFAULT_TIMEOUT_MS
    );

    return handleResponse<ActiveSessionResponse>(response);
  },

  /**
   * Deletes a template session by its ID.
   *
   * @param sessionId - The session ID to delete
   * @throws TemplateApiError if session not found (404) or server error
   *
   * Timeout: 15 seconds
   */
  async deleteSession(sessionId: string): Promise<void> {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/templates/${sessionId}`,
      {
        method: 'DELETE',
      },
      DEFAULT_TIMEOUT_MS
    );

    return handleResponse<void>(response);
  },
};
