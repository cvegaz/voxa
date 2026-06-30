import { useI18n } from '../i18n/LanguageContext';
import styles from './TranscriptionDisplay.module.css';

export interface TranscriptionDisplayProps {
  /** The transcribed text (controlled) */
  text: string;
  /** Whether transcription is currently in progress */
  isLoading: boolean;
  /** Whether the textarea should be disabled (e.g. during LLM processing) */
  isDisabled: boolean;
  /** Called on every keystroke to update parent state */
  onChange: (text: string) => void;
  /** Optional note shown below the textarea (e.g. a verification hint after accept) */
  notice?: string;
}

/**
 * TranscriptionDisplay renders an editable textarea showing the transcribed text.
 *
 * - Shows a spinner overlay while transcription is processing.
 * - Disables input while loading or when explicitly disabled (LLM processing).
 * - Allows the user to edit the text before accepting it.
 *
 * Validates: Requirements 2.2, 2.3, 2.6
 */
export function TranscriptionDisplay({
  text,
  isLoading,
  isDisabled,
  onChange,
  notice,
}: TranscriptionDisplayProps) {
  const { t } = useI18n();
  return (
    <div className={styles.container} aria-busy={isLoading}>
      <textarea
        className={styles.textarea}
        value={text}
        onChange={(e) => onChange(e.target.value)}
        disabled={isLoading || isDisabled}
        placeholder={t('display.placeholder')}
        aria-label={t('display.ariaTextarea')}
        rows={4}
      />
      {isLoading && (
        <div className={styles.loadingOverlay} role="status" aria-label={t('display.ariaTranscribing')}>
          <div className={styles.spinner} aria-hidden="true" />
        </div>
      )}
      {notice && !isLoading && (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      )}
    </div>
  );
}
