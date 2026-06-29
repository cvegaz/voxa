import type {
  ExtractionResult,
  FinalizeResponse,
  RecordsResponse,
} from '../types/extraction';
import { ExtractionApiError } from '../types/extraction';

/**
 * Base URL for the API. Defaults to '/api' which works with Vite proxy in dev,
 * or can be overridden via VITE_API_BASE_URL environment variable.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

/** Timeout for extraction process requests (60 seconds — includes LLM processing time) */
const PROCESS_TIMEOUT_MS = 60_000;

/** Timeout for get records requests (15 seconds) */
const RECORDS_TIMEOUT_MS = 15_000;

/**
 * Parses the response body and throws an ExtractionApiError if the response is not OK.
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

  throw new ExtractionApiError(response.status, errorCode, detail);
}

/**
 * Extracts the filename from a Content-Disposition header, falling back to a
 * default when the header is absent or unparseable.
 */
function parseFileName(header: string | null): string {
  if (header) {
    const match = /filename="?([^"]+)"?/.exec(header);
    if (match) {
      return match[1];
    }
  }
  return 'export.xlsx';
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
      throw new ExtractionApiError(
        408,
        'TIMEOUT',
        'La solicitud ha superado el tiempo de espera. Intente de nuevo.'
      );
    }
    throw new ExtractionApiError(
      0,
      'NETWORK_ERROR',
      'Error de conexión. Verifique su conexión a internet e intente de nuevo.'
    );
  }).finally(() => {
    clearTimeout(timeoutId);
  });
}

/**
 * API client service for extraction endpoints.
 *
 * Provides methods to process extraction from transcribed text
 * and retrieve extraction records for a session.
 */
export const extractionApi = {
  /**
   * Sends transcribed text for LLM extraction and Excel row insertion.
   *
   * @param sessionId - The active template session ID
   * @param transcribedText - The transcribed text to extract data from
   * @returns Extraction result with record values and row number
   * @throws ExtractionApiError on validation failure (422), session issues (404), or LLM/server error (502/500)
   *
   * Timeout: 60 seconds (accounts for LLM processing time)
   */
  async processExtraction(
    sessionId: string,
    transcribedText: string
  ): Promise<ExtractionResult> {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/extraction/process`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ sessionId, transcribedText }),
      },
      PROCESS_TIMEOUT_MS
    );

    return handleResponse<ExtractionResult>(response);
  },

  /**
   * Retrieves all extraction records for a given session.
   *
   * @param sessionId - The template session ID to get records for
   * @returns Records response containing all extracted records and total row count
   * @throws ExtractionApiError if session not found (404) or server error
   *
   * Timeout: 15 seconds
   */
  async getRecords(sessionId: string): Promise<RecordsResponse> {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/extraction/records/${sessionId}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      },
      RECORDS_TIMEOUT_MS
    );

    return handleResponse<RecordsResponse>(response);
  },

  /**
   * Closes a capture session so its Excel can be downloaded. Idempotent.
   *
   * @param sessionId - The session to finalize
   * @returns The finalize result (status + total rows)
   * @throws ExtractionApiError if the session is missing (404) or not confirmable (422)
   */
  async finalize(sessionId: string): Promise<FinalizeResponse> {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/extraction/finalize/${sessionId}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      },
      RECORDS_TIMEOUT_MS
    );

    return handleResponse<FinalizeResponse>(response);
  },

  /**
   * Downloads the session's data as an .xlsx blob, reconstructed by the backend
   * from the schema + records.
   *
   * @param sessionId - The session to export
   * @returns The file blob and the server-provided filename
   * @throws ExtractionApiError on server error (404/500)
   */
  async downloadExcel(
    sessionId: string
  ): Promise<{ blob: Blob; fileName: string }> {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/extraction/export/${sessionId}`,
      { method: 'GET' },
      PROCESS_TIMEOUT_MS
    );

    if (!response.ok) {
      let errorCode = 'UNKNOWN_ERROR';
      let detail = `Request failed with status ${response.status}`;
      try {
        const errorBody = await response.json();
        if (typeof errorBody?.errorCode === 'string') errorCode = errorBody.errorCode;
        if (typeof errorBody?.detail === 'string') detail = errorBody.detail;
      } catch {
        // keep defaults
      }
      throw new ExtractionApiError(response.status, errorCode, detail);
    }

    const blob = await response.blob();
    const fileName = parseFileName(response.headers.get('Content-Disposition'));
    return { blob, fileName };
  },
};
