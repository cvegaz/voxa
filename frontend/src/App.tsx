import { useState, useEffect, useCallback } from 'react';
import { FileUpload } from './components/FileUpload';
import { SchemaConfirmation } from './components/SchemaConfirmation';
import { ContextInput } from './components/ContextInput';
import { TranscriptionPage } from './components/TranscriptionPage';
import { templateApi } from './services/templateApi';
import type { UploadResponse } from './types/template';

/**
 * Steps in the application flow. Each one maps to a screen:
 *
 *   loading      → checking whether a confirmed session already exists in the backend
 *   upload       → [Module 1] upload the .xlsx file
 *   schema       → [Module 1] review the detected schema
 *   context      → [Module 1] describe the context (enriched with an LLM)
 *   transcription→ [Modules 2+3] record audio, transcribe, and extract to Excel
 */
type Step = 'loading' | 'upload' | 'schema' | 'context' | 'transcription';

export function App() {
  const [step, setStep] = useState<Step>('loading');
  // We keep the upload response so we can pass schema/sessionId to the
  // following steps of Module 1.
  const [upload, setUpload] = useState<UploadResponse | null>(null);

  // --- On mount: does a confirmed session already exist? ---
  // This way, if the user reloads the page after having confirmed an Excel
  // file, we jump straight to the transcription screen instead of asking
  // them to upload the file again. This is the key "interaction" between
  // modules: the state lives in the backend, not in the browser.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await templateApi.getActiveSession();
        if (!cancelled) setStep('transcription');
      } catch {
        // 404 = no active session → start from the upload step
        if (!cancelled) setStep('upload');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Module 1, step 1 → 2: the upload succeeded, so we show the schema.
  const handleUploadSuccess = useCallback((response: UploadResponse) => {
    setUpload(response);
    setStep('schema');
  }, []);

  // Module 1, step 2 → 3: the user accepted the schema, so we ask for context.
  const handleSchemaConfirm = useCallback(() => {
    setStep('context');
  }, []);

  // Module 1, step 2 → 1: the user wants a different file. We discard the
  // session in the backend (best-effort) and return to the upload step.
  const handleChangeFile = useCallback(() => {
    if (upload) {
      templateApi.deleteSession(upload.sessionId).catch(() => {
        /* best-effort: if it fails, we reset the UI anyway */
      });
    }
    setUpload(null);
    setStep('upload');
  }, [upload]);

  // Module 1, step 3 → end: the context was confirmed and enriched in the
  // backend. The session is now "confirmed"; we move on to transcription,
  // which will retrieve the active session on its own.
  const handleContextConfirmed = useCallback(() => {
    setStep('transcription');
  }, []);

  if (step === 'loading') {
    return (
      <main style={pageStyle}>
        <p>Cargando…</p>
      </main>
    );
  }

  return (
    <main style={pageStyle}>
      <h1 style={{ marginBottom: '0.25rem' }}>Voxa</h1>
      <p style={{ marginTop: 0, color: '#666' }}>
        Captura de datos por voz con extracción mediante IA
      </p>

      {step === 'upload' && <FileUpload onUploadSuccess={handleUploadSuccess} />}

      {step === 'schema' && upload && (
        <SchemaConfirmation
          schema={upload.schema}
          fileName={upload.fileName}
          onConfirm={handleSchemaConfirm}
          onChangeFile={handleChangeFile}
        />
      )}

      {step === 'context' && upload && (
        <ContextInput
          sessionId={upload.sessionId}
          onConfirmSuccess={handleContextConfirmed}
        />
      )}

      {step === 'transcription' && <TranscriptionPage />}
    </main>
  );
}

const pageStyle: React.CSSProperties = {
  maxWidth: 720,
  margin: '0 auto',
  padding: '2rem 1.5rem',
};
