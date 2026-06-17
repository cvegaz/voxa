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
}: TranscriptionDisplayProps) {
  return (
    <div className={styles.container} aria-busy={isLoading}>
      <textarea
        className={styles.textarea}
        value={text}
        onChange={(e) => onChange(e.target.value)}
        disabled={isLoading || isDisabled}
        placeholder="El texto transcrito aparecerá aquí..."
        aria-label="Texto transcrito"
        rows={4}
      />
      {isLoading && (
        <div className={styles.loadingOverlay} role="status" aria-label="Transcribiendo audio">
          <div className={styles.spinner} aria-hidden="true" />
        </div>
      )}
    </div>
  );
}
