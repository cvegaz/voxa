import { IconCheck } from './Icons';
import { useI18n } from '../i18n/LanguageContext';
import styles from './ExtractionStatus.module.css';

export type ExtractionState = 'idle' | 'processing' | 'success' | 'error';

export interface ExtractionStatusProps {
  /** Current state of the extraction process */
  state: ExtractionState;
  /** Row number where the record was inserted (shown on success) */
  rowNumber?: number;
  /** Error message to display (shown on error) */
  errorMessage?: string;
  /** Retry callback invoked when the user clicks "Reintentar" */
  onRetry?: () => void;
}

/**
 * ExtractionStatus displays the current state of the LLM extraction process.
 *
 * - idle: renders nothing
 * - processing: spinner with "Procesando extracción..." text
 * - success: green confirmation with the inserted row number
 * - error: red message with the error detail and a "Reintentar" button
 *
 * Validates: Requirements 1.5, 1.6
 */
export function ExtractionStatus({
  state,
  rowNumber,
  errorMessage,
  onRetry,
}: ExtractionStatusProps) {
  const { t } = useI18n();

  if (state === 'idle') {
    return null;
  }

  if (state === 'processing') {
    return (
      <div className={styles.container}>
        <div
          className={`${styles.statusMessage} ${styles.processing}`}
          role="status"
          aria-label={t('extraction.ariaProcessing')}
        >
          <div className={styles.spinner} aria-hidden="true" />
          <span>{t('extraction.processing')}</span>
        </div>
      </div>
    );
  }

  if (state === 'success') {
    return (
      <div className={styles.container}>
        <div
          className={`${styles.statusMessage} ${styles.success}`}
          role="status"
          aria-label={t('extraction.ariaSuccess')}
        >
          <IconCheck aria-hidden="true" />
          <span>{t('extraction.success', { row: rowNumber ?? '' })}</span>
        </div>
      </div>
    );
  }

  // state === 'error'
  return (
    <div className={styles.container}>
      <div
        className={`${styles.statusMessage} ${styles.error}`}
        role="alert"
      >
        <span>{errorMessage || t('common.unexpectedError')}</span>
        {onRetry && (
          <button
            type="button"
            className={styles.retryButton}
            onClick={onRetry}
            aria-label={t('extraction.ariaRetry')}
          >
            {t('common.retry')}
          </button>
        )}
      </div>
    </div>
  );
}
