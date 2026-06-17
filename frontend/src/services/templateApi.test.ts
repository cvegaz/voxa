import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { templateApi } from './templateApi';
import { TemplateApiError } from '../types/template';

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

describe('templateApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('uploadTemplate', () => {
    it('sends file as multipart/form-data and returns parsed response', async () => {
      const mockResponse = {
        sessionId: 'abc-123',
        schema: {
          columns: [
            { index: 1, name: 'Nombre', dataType: 'texto', exampleValue: 'Juan' },
          ],
        },
        fileName: 'template.xlsx',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(200, mockResponse));

      const file = new File(['content'], 'template.xlsx', {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const result = await templateApi.uploadTemplate(file);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/templates/upload');
      expect(options.method).toBe('POST');
      expect(options.body).toBeInstanceOf(FormData);
      expect(result).toEqual(mockResponse);
    });

    it('throws TemplateApiError on 422 validation error', async () => {
      const errorBody = {
        detail: 'El archivo supera el límite de 8 columnas.',
        errorCode: 'TOO_MANY_COLUMNS',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(422, errorBody));

      const file = new File(['content'], 'bad.xlsx');

      try {
        await templateApi.uploadTemplate(file);
        expect.fail('Should have thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(TemplateApiError);
        expect(error).toMatchObject({
          statusCode: 422,
          errorCode: 'TOO_MANY_COLUMNS',
        });
      }
    });

    it('throws TemplateApiError with TIMEOUT code when request exceeds 30s', async () => {
      // Mock fetch that never resolves but respects AbortSignal
      mockFetch.mockImplementationOnce((_url: string, options: RequestInit) => {
        return new Promise((_resolve, reject) => {
          options.signal?.addEventListener('abort', () => {
            const err = new Error('Aborted');
            err.name = 'AbortError';
            reject(err);
          });
        });
      });

      const file = new File(['content'], 'template.xlsx');
      const promise = templateApi.uploadTemplate(file);

      // Advance time past 30s timeout
      vi.advanceTimersByTime(31_000);

      await expect(promise).rejects.toThrow(TemplateApiError);
      await expect(promise).rejects.toMatchObject({
        errorCode: 'TIMEOUT',
      });
    });
  });

  describe('confirmTemplate', () => {
    it('sends session ID and context as JSON body', async () => {
      const mockResponse = { enrichedContext: 'Enriched context text here.' };
      mockFetch.mockResolvedValueOnce(createMockResponse(200, mockResponse));

      const result = await templateApi.confirmTemplate('session-123', 'A'.repeat(100));

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/templates/confirm');
      expect(options.method).toBe('POST');
      expect(options.headers).toEqual({ 'Content-Type': 'application/json' });
      expect(JSON.parse(options.body)).toEqual({
        sessionId: 'session-123',
        context: 'A'.repeat(100),
      });
      expect(result).toEqual(mockResponse);
    });

    it('throws TemplateApiError on 502 LLM error', async () => {
      const errorBody = {
        detail: 'Claude API unavailable',
        errorCode: 'LLM_UNAVAILABLE',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(502, errorBody));

      await expect(
        templateApi.confirmTemplate('session-123', 'A'.repeat(100))
      ).rejects.toMatchObject({
        statusCode: 502,
        errorCode: 'LLM_UNAVAILABLE',
        userMessage: 'El servicio de procesamiento no está disponible en este momento. Intente de nuevo.',
      });
    });

    it('has 60s timeout for confirm requests (LLM processing)', async () => {
      mockFetch.mockImplementationOnce((_url: string, options: RequestInit) => {
        return new Promise((_resolve, reject) => {
          options.signal?.addEventListener('abort', () => {
            const err = new Error('Aborted');
            err.name = 'AbortError';
            reject(err);
          });
        });
      });

      const promise = templateApi.confirmTemplate('session-123', 'A'.repeat(100));

      // 30s should NOT trigger timeout
      vi.advanceTimersByTime(30_000);

      // 60s+ SHOULD trigger timeout
      vi.advanceTimersByTime(31_000);

      await expect(promise).rejects.toMatchObject({
        errorCode: 'TIMEOUT',
      });
    });
  });

  describe('getActiveSession', () => {
    it('makes GET request and returns active session', async () => {
      const mockResponse = {
        sessionId: 'session-456',
        schema: {
          columns: [
            { index: 1, name: 'Col1', dataType: 'texto', exampleValue: 'ex1' },
          ],
        },
        enrichedContext: 'Enriched text',
        fileName: 'data.xlsx',
        confirmedAt: '2024-01-15T10:00:00Z',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(200, mockResponse));

      const result = await templateApi.getActiveSession();

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/templates/active');
      expect(options.method).toBe('GET');
      expect(result).toEqual(mockResponse);
    });

    it('throws TemplateApiError on 404 when no active session', async () => {
      const errorBody = {
        detail: 'No active session found',
        errorCode: 'SESSION_NOT_FOUND',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(404, errorBody));

      await expect(templateApi.getActiveSession()).rejects.toMatchObject({
        statusCode: 404,
        errorCode: 'SESSION_NOT_FOUND',
        userMessage: 'La sesión no fue encontrada. Puede que haya expirado.',
      });
    });
  });

  describe('deleteSession', () => {
    it('makes DELETE request and returns void on 204', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(204));

      const result = await templateApi.deleteSession('session-789');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/templates/session-789');
      expect(options.method).toBe('DELETE');
      expect(result).toBeUndefined();
    });

    it('throws TemplateApiError on 404 when session not found', async () => {
      const errorBody = {
        detail: 'Session not found',
        errorCode: 'SESSION_NOT_FOUND',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(404, errorBody));

      await expect(templateApi.deleteSession('bad-id')).rejects.toMatchObject({
        statusCode: 404,
        errorCode: 'SESSION_NOT_FOUND',
      });
    });
  });

  describe('error handling', () => {
    it('handles network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      await expect(templateApi.getActiveSession()).rejects.toMatchObject({
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

      await expect(templateApi.getActiveSession()).rejects.toMatchObject({
        statusCode: 500,
        errorCode: 'UNKNOWN_ERROR',
      });
    });
  });
});
