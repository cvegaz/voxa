import { useState } from 'react';
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
  onAccept,
  onReset,
}: ControlButtonsProps) {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const hasText = transcribedText.trim().length > 0;
  const isAcceptEnabled = hasText && hasConfirmedSchema && !isLLMProcessing && !isFinalized;

  const handleAccept = () => {
    if (isLLMProcessing || isFinalized) return;

    if (!hasText) {
      setErrorMessage('Primero debe grabar y transcribir un audio.');
      return;
    }

    if (!hasConfirmedSchema) {
      setErrorMessage('Primero debe cargar y confirmar un archivo Excel.');
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
          aria-label="Aceptar texto transcrito y enviar para procesamiento"
        >
          Aceptar
          {isLLMProcessing && <span className={styles.loadingIndicator} aria-hidden="true" />}
        </button>
        <button
          type="button"
          className={styles.resetButton}
          aria-disabled={isLLMProcessing || isFinalized}
          onClick={handleReset}
          aria-label="Agregar nuevo audio descartando el texto actual"
        >
          Agregar nuevo
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
