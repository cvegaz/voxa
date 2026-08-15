import { useState, useEffect, useCallback } from 'react';
import { FileUpload } from './components/FileUpload';
import { SchemaConfirmation } from './components/SchemaConfirmation';
import { ContextInput } from './components/ContextInput';
import { TranscriptionPage } from './components/TranscriptionPage';
import { LanguageSwitcher } from './components/LanguageSwitcher';
import { PrivacyNotice } from './components/PrivacyNotice';
import { IconMic } from './components/Icons';
import { useI18n } from './i18n/LanguageContext';
import { templateApi } from './services/templateApi';
import type { UploadResponse } from './types/template';
import styles from './App.module.css';

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
  const { t } = useI18n();
  const [step, setStep] = useState<Step>('loading');
  // We keep the upload response so we can pass schema/sessionId to the
  // following steps of Module 1.
  const [upload, setUpload] = useState<UploadResponse | null>(null);
  // The privacy notice is reachable from every step, including the one where the
  // microphone is about to be used — the step where it matters most.
  const [showPrivacy, setShowPrivacy] = useState(false);

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

  const header = (
    <header className={styles.header}>
      <div className={styles.langBar}>
        <LanguageSwitcher />
      </div>
      <div className={styles.brand}>
        <span className={styles.brandMark}>
          <IconMic />
        </span>
        <h1 className={styles.brandName}>Voxa</h1>
      </div>
      <p className={styles.tagline}>{t('app.tagline')}</p>
    </header>
  );

  if (step === 'loading') {
    return (
      <main className={styles.page}>
        <div className={styles.shell}>
          {header}
          <div className={styles.card}>
            <div className={styles.loading} role="status" aria-live="polite">
              <div className={styles.loadingSpinner} aria-hidden="true" />
              <p>{t('app.loading')}</p>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        {header}

        <div className={styles.card}>
          {step === 'upload' && (
            <FileUpload onUploadSuccess={handleUploadSuccess} />
          )}

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
        </div>

        <footer className={styles.footer}>
          {t('app.footer')}
          {' · '}
          <button
            type="button"
            className={styles.privacyLink}
            onClick={() => setShowPrivacy(true)}
          >
            {t('privacy.link')}
          </button>
        </footer>
      </div>

      {showPrivacy && <PrivacyNotice onClose={() => setShowPrivacy(false)} />}
    </main>
  );
}
