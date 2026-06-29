import { useState, useEffect, useCallback } from 'react';
import { AudioRecorder } from './AudioRecorder';
import { TranscriptionDisplay } from './TranscriptionDisplay';
import { ControlButtons } from './ControlButtons';
import { ExtractionStatus } from './ExtractionStatus';
import type { ExtractionState } from './ExtractionStatus';
import { SessionControls } from './SessionControls';
import { VistaExcel } from './VistaExcel';
import { transcriptionApi } from '../services/transcriptionApi';
import { templateApi } from '../services/templateApi';
import { extractionApi } from '../services/extractionApi';
import { TranscriptionApiError } from '../types/transcription';
import { ExtractionApiError } from '../types/extraction';
import type { ExtractionRecord } from '../types/extraction';
import type { ColumnDef } from '../types/template';
import styles from './TranscriptionPage.module.css';

type RecorderStatus = 'idle' | 'recording' | 'processing' | 'error';

interface TranscriptionPageState {
  recorderStatus: RecorderStatus;
  transcriptionId: string | null;
  transcribedText: string;
  isTranscribing: boolean;
  isLLMProcessing: boolean;
  hasConfirmedSchema: boolean;
  error: string | null;
  sessionId: string | null;
  extractionState: ExtractionState;
  extractionRowNumber: number | undefined;
  extractionError: string | undefined;
  records: ExtractionRecord[];
  columns: ColumnDef[];
  isRecordsLoading: boolean;
  maxRows: number;
  finalized: boolean;
  isClosing: boolean;
}

const initialState: TranscriptionPageState = {
  recorderStatus: 'idle',
  transcriptionId: null,
  transcribedText: '',
  isTranscribing: false,
  isLLMProcessing: false,
  hasConfirmedSchema: false,
  error: null,
  sessionId: null,
  extractionState: 'idle',
  extractionRowNumber: undefined,
  extractionError: undefined,
  records: [],
  columns: [],
  isRecordsLoading: false,
  // Corrected by the backend on the first records fetch; 5 is the current cap.
  maxRows: 5,
  finalized: false,
  isClosing: false,
};

/**
 * TranscriptionPage composes the AudioRecorder, TranscriptionDisplay, and ControlButtons
 * components, managing shared state and orchestrating the transcription workflow.
 *
 * Flow:
 * 1. User records audio via AudioRecorder
 * 2. Audio is sent to backend for transcription
 * 3. Transcribed text appears in editable TranscriptionDisplay
 * 4. User accepts (sends to LLM) or resets to start over
 *
 * Validates: Requirements 1.5, 2.2, 3.3, 3.6, 3.7, 3.8
 */
export function TranscriptionPage() {
  const [state, setState] = useState<TranscriptionPageState>(initialState);

  // Check for confirmed schema on mount, store sessionId and columns, fetch records
  useEffect(() => {
    let cancelled = false;

    async function checkSchema() {
      try {
        const session = await templateApi.getActiveSession();
        if (!cancelled) {
          setState((prev) => ({
            ...prev,
            hasConfirmedSchema: true,
            sessionId: session.sessionId,
            columns: session.schema.columns,
          }));

          // Fetch existing records for the session
          try {
            const recordsResponse = await extractionApi.getRecords(session.sessionId);
            if (!cancelled) {
              setState((prev) => ({
                ...prev,
                records: recordsResponse.records,
                maxRows: recordsResponse.maxRows,
                finalized: recordsResponse.finalized,
              }));
            }
          } catch {
            // Non-critical: records will be empty until first extraction
          }
        }
      } catch {
        // No active session or error — schema not confirmed
        if (!cancelled) {
          setState((prev) => ({ ...prev, hasConfirmedSchema: false }));
        }
      }
    }

    checkSchema();
    return () => { cancelled = true; };
  }, []);

  /**
   * Called when the AudioRecorder finishes recording a valid audio blob.
   * Sends the audio to the backend transcription endpoint.
   */
  const handleRecordingComplete = useCallback(
    async (audioBlob: Blob, duration: number) => {
      setState((prev) => ({
        ...prev,
        isTranscribing: true,
        recorderStatus: 'processing',
        error: null,
      }));

      try {
        const response = await transcriptionApi.transcribeAudio(audioBlob, duration);
        setState((prev) => ({
          ...prev,
          transcribedText: response.text,
          transcriptionId: response.transcriptionId,
          isTranscribing: false,
          recorderStatus: 'idle',
        }));
      } catch (err: unknown) {
        const errorMessage =
          err instanceof TranscriptionApiError
            ? err.userMessage
            : 'Error al transcribir el audio. Intente de nuevo.';

        // On error: clear text, reset recorder to idle (req 2.6, 3.8)
        setState((prev) => ({
          ...prev,
          error: errorMessage,
          isTranscribing: false,
          recorderStatus: 'idle',
          transcribedText: '',
          transcriptionId: null,
        }));
      }
    },
    []
  );

  /**
   * Called when the AudioRecorder encounters an error (permission denied, hardware failure).
   * Resets recorder to idle (req 1.7, 3.8).
   */
  const handleRecorderError = useCallback((errorMsg: string) => {
    setState((prev) => ({
      ...prev,
      error: errorMsg,
      recorderStatus: 'idle',
    }));
  }, []);

  /**
   * Called when the user edits the transcribed text in the TranscriptionDisplay.
   */
  const handleTextChange = useCallback((text: string) => {
    setState((prev) => ({ ...prev, transcribedText: text }));
  }, []);

  /**
   * Called when the user presses "Aceptar".
   * Sends the transcription to the backend for acceptance, then triggers extraction.
   */
  const handleAccept = useCallback(async () => {
    if (!state.transcriptionId || !state.sessionId) return;

    setState((prev) => ({ ...prev, isLLMProcessing: true, error: null, extractionState: 'idle' }));

    try {
      await transcriptionApi.acceptTranscription(
        state.transcriptionId,
        state.transcribedText
      );
    } catch (err: unknown) {
      const errorMessage =
        err instanceof TranscriptionApiError
          ? err.userMessage
          : 'Error al procesar la transcripción. Intente de nuevo.';

      setState((prev) => ({
        ...prev,
        error: errorMessage,
        isLLMProcessing: false,
      }));
      return;
    }

    // Transcription accepted — now run extraction
    setState((prev) => ({ ...prev, extractionState: 'processing' }));

    try {
      const result = await extractionApi.processExtraction(
        state.sessionId,
        state.transcribedText
      );

      // On extraction success: refresh records, show success, clear text
      const recordsResponse = await extractionApi.getRecords(state.sessionId);

      setState((prev) => ({
        ...prev,
        isLLMProcessing: false,
        extractionState: 'success',
        extractionRowNumber: result.rowNumber,
        extractionError: undefined,
        records: recordsResponse.records,
        maxRows: recordsResponse.maxRows,
        finalized: recordsResponse.finalized,
        transcribedText: '',
        transcriptionId: null,
      }));
    } catch (err: unknown) {
      const errorMessage =
        err instanceof ExtractionApiError
          ? err.userMessage
          : 'Error al extraer datos. Intente de nuevo.';

      // On extraction error: preserve transcribed text, show error
      setState((prev) => ({
        ...prev,
        isLLMProcessing: false,
        extractionState: 'error',
        extractionError: errorMessage,
        // Text and transcriptionId are preserved for retry
      }));
    }
  }, [state.transcriptionId, state.transcribedText, state.sessionId]);

  /**
   * Called when the user presses "Reintentar" on the ExtractionStatus error.
   * Re-triggers extraction without re-accepting the transcription.
   */
  const handleRetry = useCallback(async () => {
    if (!state.sessionId || !state.transcribedText.trim()) return;

    setState((prev) => ({
      ...prev,
      isLLMProcessing: true,
      error: null,
      extractionState: 'processing',
      extractionError: undefined,
    }));

    try {
      const result = await extractionApi.processExtraction(
        state.sessionId,
        state.transcribedText
      );

      // On extraction success: refresh records, show success, clear text
      const recordsResponse = await extractionApi.getRecords(state.sessionId);

      setState((prev) => ({
        ...prev,
        isLLMProcessing: false,
        extractionState: 'success',
        extractionRowNumber: result.rowNumber,
        extractionError: undefined,
        records: recordsResponse.records,
        maxRows: recordsResponse.maxRows,
        finalized: recordsResponse.finalized,
        transcribedText: '',
        transcriptionId: null,
      }));
    } catch (err: unknown) {
      const errorMessage =
        err instanceof ExtractionApiError
          ? err.userMessage
          : 'Error al extraer datos. Intente de nuevo.';

      setState((prev) => ({
        ...prev,
        isLLMProcessing: false,
        extractionState: 'error',
        extractionError: errorMessage,
      }));
    }
  }, [state.sessionId, state.transcribedText]);

  /**
   * Called when the user presses "Agregar nuevo".
   * Resets transcription state while keeping the confirmed schema (req 3.6).
   */
  const handleReset = useCallback(async () => {
    // If there is an existing transcription session, notify the backend
    if (state.transcriptionId) {
      try {
        await transcriptionApi.resetTranscription(state.transcriptionId);
      } catch {
        // Best-effort: even if backend reset fails, clear local state
      }
    }

    setState((prev) => ({
      ...prev,
      transcribedText: '',
      transcriptionId: null,
      error: null,
      recorderStatus: 'idle',
      // hasConfirmedSchema is preserved (req 3.6)
    }));
  }, [state.transcriptionId]);

  /**
   * Downloads the session's Excel (reconstructed by the backend) and saves it
   * via a temporary object URL.
   */
  const handleDownload = useCallback(async () => {
    if (!state.sessionId) return;

    setState((prev) => ({ ...prev, isClosing: true, error: null }));

    try {
      const { blob, fileName } = await extractionApi.downloadExcel(state.sessionId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = fileName;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setState((prev) => ({ ...prev, isClosing: false }));
    } catch (err: unknown) {
      const errorMessage =
        err instanceof ExtractionApiError
          ? err.userMessage
          : 'Error al descargar el archivo. Intente de nuevo.';
      setState((prev) => ({ ...prev, isClosing: false, error: errorMessage }));
    }
  }, [state.sessionId]);

  /**
   * Called when the user presses "Finalizar y descargar".
   * Closes the session in the backend, then downloads the Excel.
   */
  const handleFinalize = useCallback(async () => {
    if (!state.sessionId) return;

    setState((prev) => ({ ...prev, isClosing: true, error: null }));

    try {
      await extractionApi.finalize(state.sessionId);
      setState((prev) => ({ ...prev, finalized: true, isClosing: false }));
      await handleDownload();
    } catch (err: unknown) {
      const errorMessage =
        err instanceof ExtractionApiError
          ? err.userMessage
          : 'Error al finalizar la sesión. Intente de nuevo.';
      setState((prev) => ({ ...prev, isClosing: false, error: errorMessage }));
    }
  }, [state.sessionId, handleDownload]);

  return (
    <div className={styles.container}>
      {state.error && (
        <div className={styles.errorBanner} role="alert" aria-live="assertive">
          <span className={styles.errorIcon} aria-hidden="true">⚠️</span>
          <p className={styles.errorText}>{state.error}</p>
        </div>
      )}

      <AudioRecorder
        onRecordingComplete={handleRecordingComplete}
        onError={handleRecorderError}
        isDisabled={state.isLLMProcessing || state.finalized}
        status={state.recorderStatus}
      />

      <TranscriptionDisplay
        text={state.transcribedText}
        isLoading={state.isTranscribing}
        isDisabled={state.isLLMProcessing || state.finalized}
        onChange={handleTextChange}
      />

      <ControlButtons
        transcribedText={state.transcribedText}
        hasConfirmedSchema={state.hasConfirmedSchema}
        isLLMProcessing={state.isLLMProcessing}
        isFinalized={state.finalized}
        onAccept={handleAccept}
        onReset={handleReset}
      />

      <ExtractionStatus
        state={state.extractionState}
        rowNumber={state.extractionRowNumber}
        errorMessage={state.extractionError}
        onRetry={handleRetry}
      />

      {state.hasConfirmedSchema && (
        <SessionControls
          totalRows={state.records.length}
          maxRows={state.maxRows}
          finalized={state.finalized}
          isBusy={state.isClosing}
          onFinalize={handleFinalize}
          onDownload={handleDownload}
        />
      )}

      <VistaExcel
        columns={state.columns}
        records={state.records}
        isLoading={state.extractionState === 'processing'}
      />
    </div>
  );
}
