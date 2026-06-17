import { useState, useCallback } from 'react';
import { templateApi } from '../services/templateApi';
import { TemplateApiError } from '../types/template';

const MIN_CHARS = 50;
const MAX_CHARS = 3000;

type ComponentState = 'idle' | 'processing' | 'error' | 'success';

export interface ContextInputProps {
  sessionId: string;
  onConfirmSuccess: (enrichedContext: string) => void;
}

/**
 * ContextInput component — textarea with character counter and validation.
 * Allows user to write context (50-3000 chars), confirm it,
 * and triggers LLM enrichment via the backend.
 */
export function ContextInput({ sessionId, onConfirmSuccess }: ContextInputProps) {
  const [context, setContext] = useState('');
  const [state, setState] = useState<ComponentState>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  const charCount = context.length;
  const isTooShort = charCount > 0 && charCount < MIN_CHARS;
  const isTooLong = charCount > MAX_CHARS;
  const isValid = charCount >= MIN_CHARS && charCount <= MAX_CHARS;
  const isButtonDisabled = !isValid || state === 'processing';

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContext(e.target.value);
    // Clear any previous API error when user edits text
    if (state === 'error') {
      setState('idle');
      setErrorMessage('');
    }
  }, [state]);

  const handleConfirm = useCallback(async () => {
    if (!isValid || state === 'processing') return;

    setState('processing');
    setErrorMessage('');

    try {
      const response = await templateApi.confirmTemplate(sessionId, context);
      setState('success');
      onConfirmSuccess(response.enrichedContext);
    } catch (err: unknown) {
      setState('error');
      if (err instanceof TemplateApiError) {
        setErrorMessage(err.userMessage);
      } else {
        setErrorMessage('Ha ocurrido un error inesperado. Intente de nuevo.');
      }
    }
  }, [sessionId, context, isValid, state, onConfirmSuccess]);

  const handleRetry = useCallback(() => {
    handleConfirm();
  }, [handleConfirm]);

  // Validation message logic
  let validationMessage = '';
  if (isTooShort) {
    validationMessage = `Escriba al menos 50 caracteres (${charCount} actualmente)`;
  } else if (isTooLong) {
    validationMessage = 'El texto supera el límite de 3000 caracteres';
  }

  return (
    <div className="context-input">
      {/* Textarea section — visible in idle and error states */}
      {(state === 'idle' || state === 'error') && (
        <>
          <label htmlFor="context-textarea" className="context-input__label">
            Descripción del contexto del Excel
          </label>

          <textarea
            id="context-textarea"
            className={`context-input__textarea${validationMessage ? ' context-input__textarea--invalid' : ''}`}
            value={context}
            onChange={handleChange}
            placeholder="Describa qué es este Excel, su historia y lo que contiene (mínimo 50 caracteres)..."
            rows={6}
            aria-describedby="context-char-count context-validation-message"
            aria-invalid={isTooShort || isTooLong || undefined}
          />

          {/* Character counter */}
          <div
            id="context-char-count"
            className="context-input__counter"
            aria-live="polite"
            aria-atomic="true"
          >
            {charCount}/{MAX_CHARS} caracteres
          </div>

          {/* Validation message */}
          {validationMessage && (
            <p
              id="context-validation-message"
              className="context-input__validation"
              role="alert"
            >
              {validationMessage}
            </p>
          )}

          {/* API error message */}
          {state === 'error' && errorMessage && (
            <div className="context-input__error" role="alert">
              <p className="context-input__error-text">{errorMessage}</p>
              <button
                type="button"
                className="context-input__retry-button"
                onClick={handleRetry}
              >
                Reintentar
              </button>
            </div>
          )}

          {/* Confirm button */}
          <button
            type="button"
            className="context-input__confirm-button"
            disabled={isButtonDisabled}
            onClick={handleConfirm}
            aria-label="Confirmar contexto y continuar"
          >
            Confirmar y Continuar
          </button>
        </>
      )}

      {/* Processing state — spinner */}
      {state === 'processing' && (
        <div className="context-input__processing" role="status" aria-live="polite">
          <div className="context-input__spinner" aria-hidden="true" />
          <p>Procesando contexto con inteligencia artificial...</p>
        </div>
      )}

      {/* Success state — brief confirmation (parent handles next step) */}
      {state === 'success' && (
        <div className="context-input__success" role="status" aria-live="polite">
          <p>Contexto enriquecido generado exitosamente.</p>
        </div>
      )}
    </div>
  );
}
