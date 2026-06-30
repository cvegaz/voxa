import { useState } from 'react';
import { useI18n } from '../i18n/LanguageContext';
import styles from './ControlButtons.module.css';

export interface ControlButtonsProps {
  /** The current transcribed text */
  transcribedText: string;
  /** Whether the user has confirmed an Excel schema */
  hasConfirmedSchema: boolean;
  /** Whether the LLM is currently processing */
  isLLMProcessing: boolean;
  /** Whether the session is finalized (closed); disables capture controls */
  isFinalized?: boolean;
  /** Whether the shown text was already accepted (kept on screen for verification);
   * disables "Aceptar" so the same narration is not submitted twice. */
  isAccepted?: boolean;
  /** Callback when the user accepts the transcription */
  onAccept: () => void;
  /** Callback when the user wants to reset and start a new recording */
  onReset: () => void;
}

/**
 * Renders "Aceptar" and "Agregar nuevo" control buttons.
 * Handles precondition validation and shows contextual error messages.
 */
export function ControlButtons({
  transcribedText,
  hasConfirmedSchema,
  isLLMProcessing,
  isFinalized = false,
  isAccepted = false,
  onAccept,
  onReset,
}: ControlButtonsProps) {
  const { t } = useI18n();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const hasText = transcribedText.trim().length > 0;
  const isAcceptEnabled =
    hasText && hasConfirmedSchema && !isLLMProcessing && !isFinalized && !isAccepted;

  const handleAccept = () => {
    if (isLLMProcessing || isFinalized || isAccepted) return;

    if (!hasText) {
      setErrorMessage(t('controls.errNoText'));
      return;
    }

    if (!hasConfirmedSchema) {
      setErrorMessage(t('controls.errNoSchema'));
      return;
    }

    setErrorMessage(null);
    onAccept();
  };

  const handleReset = () => {
    if (isLLMProcessing || isFinalized) return;
    setErrorMessage(null);
    onReset();
  };

  return (
    <div className={styles.container}>
      <div className={styles.buttonRow}>
        <button
          type="button"
          className={styles.acceptButton}
          aria-disabled={!isAcceptEnabled}
          onClick={handleAccept}
          aria-label={t('controls.ariaAccept')}
        >
          {t('controls.accept')}
          {isLLMProcessing && <span className={styles.loadingIndicator} aria-hidden="true" />}
        </button>
        <button
          type="button"
          className={styles.resetButton}
          aria-disabled={isLLMProcessing || isFinalized}
          onClick={handleReset}
          aria-label={t('controls.ariaAddNew')}
        >
          {t('controls.addNew')}
        </button>
      </div>
      {errorMessage && (
        <p className={styles.errorMessage} role="alert">
          {errorMessage}
        </p>
      )}
    </div>
  );
}
