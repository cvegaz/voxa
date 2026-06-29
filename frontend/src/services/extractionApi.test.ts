import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { extractionApi } from './extractionApi';
import { ExtractionApiError } from '../types/extraction';

// Mock global fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function createMockResponse(status: number, body?: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    headers: new Headers(),
    redirected: false,
    statusText: '',
    type: 'basic',
    url: '',
    clone: () => ({}) as Response,
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    text: () => Promise.resolve(''),
  } as Response;
}

describe('extractionApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('processExtraction', () => {
    it('sends session ID and transcribed text as JSON and returns extraction result', async () => {
      const mockResponse = {
        extractionId: 'ext-001',
        record: [
          { columnName: 'Nombre', value: 'Juan Pérez' },
          { columnName: 'Edad', value: '35' },
        ],
        rowNumber: 4,
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(200, mockResponse));

      const result = await extractionApi.processExtraction('session-123', 'Mi nombre es Juan Pérez y tengo 35 años');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/extraction/process');
      expect(options.method).toBe('POST');
      expect(options.headers).toEqual({ 'Content-Type': 'application/json' });
      expect(JSON.parse(options.body)).toEqual({
        sessionId: 'session-123',
        transcribedText: 'Mi nombre es Juan Pérez y tengo 35 años',
      });
      expect(result).toEqual(mockResponse);
    });

    it('throws ExtractionApiError on 422 validation error (empty transcription)', async () => {
      const errorBody = {
        detail: 'El texto transcrito está vacío',
        errorCode: 'EMPTY_TRANSCRIPTION',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(422, errorBody));

      await expect(
        extractionApi.processExtraction('session-123', '')
      ).rejects.toMatchObject({
        statusCode: 422,
        errorCode: 'EMPTY_TRANSCRIPTION',
        userMessage: 'El texto transcrito está vacío. Grabe audio antes de extraer datos.',
      });
    });

    it('throws ExtractionApiError on 404 when session not found', async () => {
      const errorBody = {
        detail: 'Session not found',
        errorCode: 'SESSION_NOT_FOUND',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(404, errorBody));

      await expect(
        extractionApi.processExtraction('bad-session', 'some text')
      ).rejects.toMatchObject({
        statusCode: 404,
        errorCode: 'SESSION_NOT_FOUND',
        userMessage: 'La sesión no fue encontrada. Puede que haya expirado.',
      });
    });

    it('throws ExtractionApiError on 502 LLM unavailable error', async () => {
      const errorBody = {
        detail: 'Claude API unavailable',
        errorCode: 'LLM_UNAVAILABLE',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(502, errorBody));

      await expect(
        extractionApi.processExtraction('session-123', 'some text')
      ).rejects.toMatchObject({
        statusCode: 502,
        errorCode: 'LLM_UNAVAILABLE',
        userMessage: 'El servicio de extracción no está disponible en este momento. Intente de nuevo.',
      });
    });

    it('has 60s timeout for process extraction requests', async () => {
      mockFetch.mockImplementationOnce((_url: string, options: RequestInit) => {
        return new Promise((_resolve, reject) => {
          options.signal?.addEventListener('abort', () => {
            const err = new Error('Aborted');
            err.name = 'AbortError';
            reject(err);
          });
        });
      });

      const promise = extractionApi.processExtraction('session-123', 'some text');

      // 30s should NOT trigger timeout
      vi.advanceTimersByTime(30_000);

      // 60s+ SHOULD trigger timeout
      vi.advanceTimersByTime(31_000);

      await expect(promise).rejects.toMatchObject({
        errorCode: 'TIMEOUT',
      });
    });
  });

  describe('getRecords', () => {
    it('makes GET request and returns records response', async () => {
      const mockResponse = {
        records: [
          {
            extractionId: 'ext-001',
            rowNumber: 4,
            record: [
              { columnName: 'Nombre', value: 'Juan Pérez' },
              { columnName: 'Edad', value: '35' },
            ],
            transcribedText: 'Mi nombre es Juan Pérez y tengo 35 años',
            createdAt: '2024-01-15T10:00:00Z',
          },
        ],
        totalRows: 1,
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(200, mockResponse));

      const result = await extractionApi.getRecords('session-123');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/extraction/records/session-123');
      expect(options.method).toBe('GET');
      expect(result).toEqual(mockResponse);
    });

    it('throws ExtractionApiError on 404 when session not found', async () => {
      const errorBody = {
        detail: 'Session not found',
        errorCode: 'SESSION_NOT_FOUND',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(404, errorBody));

      await expect(
        extractionApi.getRecords('bad-session')
      ).rejects.toMatchObject({
        statusCode: 404,
        errorCode: 'SESSION_NOT_FOUND',
        userMessage: 'La sesión no fue encontrada. Puede que haya expirado.',
      });
    });

    it('has 15s timeout for get records requests', async () => {
      mockFetch.mockImplementationOnce((_url: string, options: RequestInit) => {
        return new Promise((_resolve, reject) => {
          options.signal?.addEventListener('abort', () => {
            const err = new Error('Aborted');
            err.name = 'AbortError';
            reject(err);
          });
        });
      });

      const promise = extractionApi.getRecords('session-123');

      // 10s should NOT trigger timeout
      vi.advanceTimersByTime(10_000);

      // 15s+ SHOULD trigger timeout
      vi.advanceTimersByTime(6_000);

      await expect(promise).rejects.toMatchObject({
        errorCode: 'TIMEOUT',
      });
    });
  });

  describe('error handling', () => {
    it('handles network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      await expect(
        extractionApi.processExtraction('session-123', 'text')
      ).rejects.toMatchObject({
        errorCode: 'NETWORK_ERROR',
        userMessage: 'Error de conexión. Verifique su conexión a internet e intente de nuevo.',
      });
    });

    it('handles unparseable error response body', async () => {
      const response = {
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error('Invalid JSON')),
        headers: new Headers(),
        redirected: false,
        statusText: '',
        type: 'basic',
        url: '',
        clone: () => ({}) as Response,
        body: null,
        bodyUsed: false,
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
        blob: () => Promise.resolve(new Blob()),
        formData: () => Promise.resolve(new FormData()),
        text: () => Promise.resolve(''),
      } as Response;
      mockFetch.mockResolvedValueOnce(response);

      await expect(
        extractionApi.getRecords('session-123')
      ).rejects.toMatchObject({
        statusCode: 500,
        errorCode: 'UNKNOWN_ERROR',
      });
    });

    it('throws ExtractionApiError instance for all error scenarios', async () => {
      const errorBody = {
        detail: 'Database connection failed',
        errorCode: 'DATABASE_ERROR',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(500, errorBody));

      try {
        await extractionApi.processExtraction('session-123', 'text');
        expect.fail('Should have thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(ExtractionApiError);
        expect(error).toMatchObject({
          statusCode: 500,
          errorCode: 'DATABASE_ERROR',
          // Backend detail is surfaced (no longer masked by a generic message).
          userMessage: 'Database connection failed',
        });
      }
    });
  });

  describe('finalize', () => {
    it('POSTs to the finalize endpoint and returns the result', async () => {
      mockFetch.mockResolvedValueOnce(
        createMockResponse(200, { status: 'finalized', totalRows: 3 })
      );

      const result = await extractionApi.finalize('session-123');

      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/extraction/finalize/session-123');
      expect(options.method).toBe('POST');
      expect(result).toEqual({ status: 'finalized', totalRows: 3 });
    });

    it('throws ExtractionApiError when the session is missing', async () => {
      mockFetch.mockResolvedValueOnce(
        createMockResponse(404, { detail: 'no', errorCode: 'SESSION_NOT_FOUND' })
      );

      await expect(extractionApi.finalize('session-123')).rejects.toMatchObject({
        statusCode: 404,
        errorCode: 'SESSION_NOT_FOUND',
      });
    });
  });

  describe('downloadExcel', () => {
    it('GETs the export and returns the blob with the server filename', async () => {
      const blob = new Blob(['xlsx-bytes']);
      const headers = new Headers({
        'Content-Disposition': 'attachment; filename="partido.xlsx"',
      });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers,
        blob: () => Promise.resolve(blob),
        json: () => Promise.reject(new Error('not json')),
      } as unknown as Response);

      const result = await extractionApi.downloadExcel('session-123');

      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/extraction/export/session-123');
      expect(options.method).toBe('GET');
      expect(result.fileName).toBe('partido.xlsx');
      expect(result.blob).toBe(blob);
    });

    it('falls back to a default filename when the header is absent', async () => {
      const blob = new Blob(['xlsx-bytes']);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers(),
        blob: () => Promise.resolve(blob),
        json: () => Promise.reject(new Error('not json')),
      } as unknown as Response);

      const result = await extractionApi.downloadExcel('session-123');
      expect(result.fileName).toBe('export.xlsx');
    });

    it('throws ExtractionApiError on a server error', async () => {
      mockFetch.mockResolvedValueOnce(
        createMockResponse(404, { detail: 'no', errorCode: 'SESSION_NOT_FOUND' })
      );

      await expect(extractionApi.downloadExcel('session-123')).rejects.toMatchObject({
        statusCode: 404,
        errorCode: 'SESSION_NOT_FOUND',
      });
    });
  });
});
