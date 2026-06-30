import { useState, useCallback } from 'react';
import { templateApi } from '../services/templateApi';
import { TemplateApiError } from '../types/template';
import { useI18n } from '../i18n/LanguageContext';

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
  const { t } = useI18n();
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
        setErrorMessage(t('common.unexpectedError'));
      }
    }
  }, [sessionId, context, isValid, state, onConfirmSuccess, t]);

  const handleRetry = useCallback(() => {
    handleConfirm();
  }, [handleConfirm]);

  // Validation message logic
  let validationMessage = '';
  if (isTooShort) {
    validationMessage = t('context.tooShort', { count: charCount });
  } else if (isTooLong) {
    validationMessage = t('context.tooLong');
  }

  return (
    <div className="context-input">
      {/* Textarea section — visible in idle and error states */}
      {(state === 'idle' || state === 'error') && (
        <>
          <label htmlFor="context-textarea" className="context-input__label">
            {t('context.label')}
          </label>

          <textarea
            id="context-textarea"
            className={`context-input__textarea${validationMessage ? ' context-input__textarea--invalid' : ''}`}
            value={context}
            onChange={handleChange}
            placeholder={t('context.placeholder')}
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
            {t('context.counter', { count: charCount, max: MAX_CHARS })}
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
                {t('common.retry')}
              </button>
            </div>
          )}

          {/* Confirm button */}
          <button
            type="button"
            className="context-input__confirm-button"
            disabled={isButtonDisabled}
            onClick={handleConfirm}
            aria-label={t('context.ariaConfirm')}
          >
            {t('context.confirm')}
          </button>
        </>
      )}

      {/* Processing state — spinner */}
      {state === 'processing' && (
        <div className="context-input__processing" role="status" aria-live="polite">
          <div className="context-input__spinner" aria-hidden="true" />
          <p>{t('context.processing')}</p>
        </div>
      )}

      {/* Success state — brief confirmation (parent handles next step) */}
      {state === 'success' && (
        <div className="context-input__success" role="status" aria-live="polite">
          <p>{t('context.success')}</p>
        </div>
      )}
    </div>
  );
}
