import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { transcriptionApi } from './transcriptionApi';

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

describe('transcriptionApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('transcribeAudio', () => {
    it('sends audio blob as multipart/form-data with duration and returns parsed response', async () => {
      const mockResponse = {
        transcriptionId: 'trans-123',
        text: 'Texto transcrito del audio.',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(200, mockResponse));

      const audioBlob = new Blob(['audio-data'], { type: 'audio/webm' });
      const result = await transcriptionApi.transcribeAudio(audioBlob, 5.5);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/transcriptions/transcribe');
      expect(options.method).toBe('POST');
      expect(options.body).toBeInstanceOf(FormData);

      const formData = options.body as FormData;
      expect(formData.get('file')).toBeInstanceOf(Blob);
      expect(formData.get('duration')).toBe('5.5');

      expect(result).toEqual(mockResponse);
    });

    it('throws TranscriptionApiError with AUDIO_TOO_SHORT on 422', async () => {
      const errorBody = {
        detail: 'Audio duration too short',
        errorCode: 'AUDIO_TOO_SHORT',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(422, errorBody));

      const audioBlob = new Blob(['short'], { type: 'audio/webm' });

      await expect(
        transcriptionApi.transcribeAudio(audioBlob, 0.5)
      ).rejects.toMatchObject({
        statusCode: 422,
        errorCode: 'AUDIO_TOO_SHORT',
        userMessage: 'El audio es demasiado corto. Grabe al menos 1 segundo.',
      });
    });

    it('throws TranscriptionApiError with AUDIO_TOO_LONG on 422', async () => {
      const errorBody = {
        detail: 'Audio duration too long',
        errorCode: 'AUDIO_TOO_LONG',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(422, errorBody));

      const audioBlob = new Blob(['long-audio'], { type: 'audio/webm' });

      await expect(
        transcriptionApi.transcribeAudio(audioBlob, 35)
      ).rejects.toMatchObject({
        statusCode: 422,
        errorCode: 'AUDIO_TOO_LONG',
        userMessage: 'El audio es demasiado largo. Máximo 20 segundos.',
      });
    });

    it('throws TranscriptionApiError with UNSUPPORTED_AUDIO_FORMAT on 422', async () => {
      const errorBody = {
        detail: 'Unsupported audio format',
        errorCode: 'UNSUPPORTED_AUDIO_FORMAT',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(422, errorBody));

      const audioBlob = new Blob(['data'], { type: 'audio/flac' });

      await expect(
        transcriptionApi.transcribeAudio(audioBlob, 5)
      ).rejects.toMatchObject({
        statusCode: 422,
        errorCode: 'UNSUPPORTED_AUDIO_FORMAT',
        userMessage: 'El formato de audio no es compatible.',
      });
    });

    it('throws TranscriptionApiError with EMPTY_AUDIO_FILE on 422', async () => {
      const errorBody = {
        detail: 'Audio file is empty',
        errorCode: 'EMPTY_AUDIO_FILE',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(422, errorBody));

      const audioBlob = new Blob([], { type: 'audio/webm' });

      await expect(
        transcriptionApi.transcribeAudio(audioBlob, 0)
      ).rejects.toMatchObject({
        statusCode: 422,
        errorCode: 'EMPTY_AUDIO_FILE',
        userMessage: 'El archivo de audio está vacío.',
      });
    });

    it('throws TranscriptionApiError with WHISPER_UNAVAILABLE on 502', async () => {
      const errorBody = {
        detail: 'Whisper API unavailable',
        errorCode: 'WHISPER_UNAVAILABLE',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(502, errorBody));

      const audioBlob = new Blob(['audio'], { type: 'audio/webm' });

      await expect(
        transcriptionApi.transcribeAudio(audioBlob, 5)
      ).rejects.toMatchObject({
        statusCode: 502,
        errorCode: 'WHISPER_UNAVAILABLE',
        userMessage: 'El servicio de transcripción no está disponible. Intente de nuevo.',
      });
    });

    it('throws TranscriptionApiError with WHISPER_NO_SPEECH on 422', async () => {
      const errorBody = {
        detail: 'No speech detected in audio',
        errorCode: 'WHISPER_NO_SPEECH',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(422, errorBody));

      const audioBlob = new Blob(['silence'], { type: 'audio/webm' });

      await expect(
        transcriptionApi.transcribeAudio(audioBlob, 5)
      ).rejects.toMatchObject({
        statusCode: 422,
        errorCode: 'WHISPER_NO_SPEECH',
        userMessage: 'No se detectó habla en el audio. Intente grabar de nuevo.',
      });
    });

    it('throws TranscriptionApiError with WHISPER_EMPTY_RESPONSE on 502', async () => {
      const errorBody = {
        detail: 'Whisper returned empty response',
        errorCode: 'WHISPER_EMPTY_RESPONSE',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(502, errorBody));

      const audioBlob = new Blob(['audio'], { type: 'audio/webm' });

      await expect(
        transcriptionApi.transcribeAudio(audioBlob, 5)
      ).rejects.toMatchObject({
        statusCode: 502,
        errorCode: 'WHISPER_EMPTY_RESPONSE',
        userMessage: 'No se pudo transcribir el audio. Intente grabar de nuevo.',
      });
    });

    it('throws TranscriptionApiError with TIMEOUT code when request exceeds 30s', async () => {
      mockFetch.mockImplementationOnce((_url: string, options: RequestInit) => {
        return new Promise((_resolve, reject) => {
          options.signal?.addEventListener('abort', () => {
            const err = new Error('Aborted');
            err.name = 'AbortError';
            reject(err);
          });
        });
      });

      const audioBlob = new Blob(['audio'], { type: 'audio/webm' });
      const promise = transcriptionApi.transcribeAudio(audioBlob, 5);

      vi.advanceTimersByTime(31_000);

      await expect(promise).rejects.toMatchObject({
        errorCode: 'TIMEOUT',
        userMessage: 'La solicitud ha superado el tiempo de espera. Intente de nuevo.',
      });
    });
  });

  describe('acceptTranscription', () => {
    it('sends transcription_id and text as JSON and returns parsed response', async () => {
      const mockResponse = { status: 'accepted' };
      mockFetch.mockResolvedValueOnce(createMockResponse(200, mockResponse));

      const result = await transcriptionApi.acceptTranscription('trans-123', 'Texto final editado');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/transcriptions/accept');
      expect(options.method).toBe('POST');
      expect(options.headers).toEqual({ 'Content-Type': 'application/json' });
      expect(JSON.parse(options.body)).toEqual({
        transcription_id: 'trans-123',
        text: 'Texto final editado',
      });
      expect(result).toEqual(mockResponse);
    });

    it('throws TranscriptionApiError with EMPTY_TRANSCRIPTION on 422', async () => {
      const errorBody = {
        detail: 'Transcription text is empty',
        errorCode: 'EMPTY_TRANSCRIPTION',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(422, errorBody));

      await expect(
        transcriptionApi.acceptTranscription('trans-123', '')
      ).rejects.toMatchObject({
        statusCode: 422,
        errorCode: 'EMPTY_TRANSCRIPTION',
        userMessage: 'El texto no puede estar vacío.',
      });
    });

    it('throws TranscriptionApiError with NO_CONFIRMED_SCHEMA on 409', async () => {
      const errorBody = {
        detail: 'No confirmed schema exists',
        errorCode: 'NO_CONFIRMED_SCHEMA',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(409, errorBody));

      await expect(
        transcriptionApi.acceptTranscription('trans-123', 'Texto válido')
      ).rejects.toMatchObject({
        statusCode: 409,
        errorCode: 'NO_CONFIRMED_SCHEMA',
        userMessage: 'Primero debe cargar y confirmar un archivo Excel.',
      });
    });

    it('throws TranscriptionApiError with SESSION_NOT_FOUND on 404', async () => {
      const errorBody = {
        detail: 'Session not found',
        errorCode: 'SESSION_NOT_FOUND',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(404, errorBody));

      await expect(
        transcriptionApi.acceptTranscription('bad-id', 'Texto')
      ).rejects.toMatchObject({
        statusCode: 404,
        errorCode: 'SESSION_NOT_FOUND',
        userMessage: 'La sesión de transcripción no fue encontrada.',
      });
    });

    it('has 60s timeout for acceptance requests', async () => {
      mockFetch.mockImplementationOnce((_url: string, options: RequestInit) => {
        return new Promise((_resolve, reject) => {
          options.signal?.addEventListener('abort', () => {
            const err = new Error('Aborted');
            err.name = 'AbortError';
            reject(err);
          });
        });
      });

      const promise = transcriptionApi.acceptTranscription('trans-123', 'Texto');

      // 30s should NOT trigger timeout
      vi.advanceTimersByTime(30_000);

      // 60s+ SHOULD trigger timeout
      vi.advanceTimersByTime(31_000);

      await expect(promise).rejects.toMatchObject({
        errorCode: 'TIMEOUT',
      });
    });
  });

  describe('resetTranscription', () => {
    it('sends transcription_id as JSON and returns parsed response', async () => {
      const mockResponse = { status: 'reset' };
      mockFetch.mockResolvedValueOnce(createMockResponse(200, mockResponse));

      const result = await transcriptionApi.resetTranscription('trans-456');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/transcriptions/reset');
      expect(options.method).toBe('POST');
      expect(options.headers).toEqual({ 'Content-Type': 'application/json' });
      expect(JSON.parse(options.body)).toEqual({
        transcription_id: 'trans-456',
      });
      expect(result).toEqual(mockResponse);
    });

    it('throws TranscriptionApiError with SESSION_NOT_FOUND on 404', async () => {
      const errorBody = {
        detail: 'Session not found',
        errorCode: 'SESSION_NOT_FOUND',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(404, errorBody));

      await expect(
        transcriptionApi.resetTranscription('bad-id')
      ).rejects.toMatchObject({
        statusCode: 404,
        errorCode: 'SESSION_NOT_FOUND',
        userMessage: 'La sesión de transcripción no fue encontrada.',
      });
    });

    it('has 15s timeout for reset requests', async () => {
      mockFetch.mockImplementationOnce((_url: string, options: RequestInit) => {
        return new Promise((_resolve, reject) => {
          options.signal?.addEventListener('abort', () => {
            const err = new Error('Aborted');
            err.name = 'AbortError';
            reject(err);
          });
        });
      });

      const promise = transcriptionApi.resetTranscription('trans-123');

      vi.advanceTimersByTime(16_000);

      await expect(promise).rejects.toMatchObject({
        errorCode: 'TIMEOUT',
      });
    });
  });

  describe('error handling', () => {
    it('handles network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      const audioBlob = new Blob(['audio'], { type: 'audio/webm' });

      await expect(
        transcriptionApi.transcribeAudio(audioBlob, 5)
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

      const audioBlob = new Blob(['audio'], { type: 'audio/webm' });

      await expect(
        transcriptionApi.transcribeAudio(audioBlob, 5)
      ).rejects.toMatchObject({
        statusCode: 500,
        errorCode: 'UNKNOWN_ERROR',
      });
    });

    it('maps DATABASE_ERROR to user-friendly message', async () => {
      const errorBody = {
        detail: 'Connection refused',
        errorCode: 'DATABASE_ERROR',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(500, errorBody));

      await expect(
        transcriptionApi.acceptTranscription('trans-123', 'Texto')
      ).rejects.toMatchObject({
        statusCode: 500,
        errorCode: 'DATABASE_ERROR',
        userMessage: 'Error interno del servidor. Intente de nuevo más tarde.',
      });
    });
  });
});
