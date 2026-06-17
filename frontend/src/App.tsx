import { useState, useEffect, useCallback } from 'react';
import { FileUpload } from './components/FileUpload';
import { SchemaConfirmation } from './components/SchemaConfirmation';
import { ContextInput } from './components/ContextInput';
import { TranscriptionPage } from './components/TranscriptionPage';
import { templateApi } from './services/templateApi';
import type { UploadResponse } from './types/template';

/**
 * Pasos del flujo de la aplicación. Cada uno corresponde a una pantalla:
 *
 *   loading      → comprobando si ya hay una sesión confirmada en el backend
 *   upload       → [Módulo 1] cargar el .xlsx
 *   schema       → [Módulo 1] revisar el esquema detectado
 *   context      → [Módulo 1] describir el contexto (se enriquece con LLM)
 *   transcription→ [Módulos 2+3] grabar audio, transcribir y extraer a Excel
 */
type Step = 'loading' | 'upload' | 'schema' | 'context' | 'transcription';

export function App() {
  const [step, setStep] = useState<Step>('loading');
  // Guardamos la respuesta de la carga para pasar schema/sessionId a los
  // siguientes pasos del Módulo 1.
  const [upload, setUpload] = useState<UploadResponse | null>(null);

  // --- Al montar: ¿ya existe una sesión confirmada? ---
  // Así, si el usuario recarga la página tras haber confirmado un Excel,
  // saltamos directo a la pantalla de transcripción en vez de pedirle
  // que vuelva a subir el archivo. Esta es la "interacción" clave entre
  // módulos: el estado vive en el backend, no en el navegador.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await templateApi.getActiveSession();
        if (!cancelled) setStep('transcription');
      } catch {
        // 404 = no hay sesión activa → empezamos desde la carga
        if (!cancelled) setStep('upload');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Módulo 1, paso 1 → 2: la carga tuvo éxito, mostramos el esquema.
  const handleUploadSuccess = useCallback((response: UploadResponse) => {
    setUpload(response);
    setStep('schema');
  }, []);

  // Módulo 1, paso 2 → 3: el usuario aceptó el esquema, pedimos contexto.
  const handleSchemaConfirm = useCallback(() => {
    setStep('context');
  }, []);

  // Módulo 1, paso 2 → 1: el usuario quiere otro archivo. Descartamos la
  // sesión en el backend (best-effort) y volvemos a la carga.
  const handleChangeFile = useCallback(() => {
    if (upload) {
      templateApi.deleteSession(upload.sessionId).catch(() => {
        /* best-effort: si falla, igual reiniciamos la UI */
      });
    }
    setUpload(null);
    setStep('upload');
  }, [upload]);

  // Módulo 1, paso 3 → fin: el contexto se confirmó y enriqueció en el
  // backend. La sesión queda "confirmed"; pasamos a transcripción, que
  // recuperará la sesión activa por su cuenta.
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
      <h1 style={{ marginBottom: '0.25rem' }}>Audio → Excel</h1>
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
