import { IconDownload } from './Icons';
import { useI18n } from '../i18n/LanguageContext';
import { DemoLeadForm } from './DemoLeadForm';
import styles from './SessionControls.module.css';

export interface SessionControlsProps {
  /** Number of records captured so far */
  totalRows: number;
  /** Maximum records before the session auto-finalizes */
  maxRows: number;
  /** Whether the session is closed */
  finalized: boolean;
  /** Whether a finalize/download request is in flight */
  isBusy: boolean;
  /** Finalize the session and download the Excel */
  onFinalize: () => void;
  /** Download the current Excel */
  onDownload: () => void;
  /** Session the capture belongs to, attached to a lead if one is left. */
  sessionId?: string;
}

/**
 * SessionControls shows the capture progress ("N / max") and the actions to
 * close the session:
 *
 * - While open: a "Finalizar" button (enabled once there is at least one row).
 * - Once finalized (manually or by reaching the cap): a closing message and a
 *   "Descargar Excel" button.
 */
export function SessionControls({
  totalRows,
  maxRows,
  finalized,
  isBusy,
  onFinalize,
  onDownload,
  sessionId,
}: SessionControlsProps) {
  const { t } = useI18n();
  const reachedCap = totalRows >= maxRows;

  return (
    <div className={styles.container}>
      <p className={styles.counter} aria-live="polite">
        {t('session.counter', { count: totalRows, max: maxRows })}
      </p>

      {finalized ? (
        <div className={styles.finalized}>
          <p className={styles.finalizedMessage} role="status">
            {reachedCap ? t('session.capReached', { max: maxRows }) : t('session.finalized')}
          </p>
          <button
            type="button"
            className={styles.downloadButton}
            onClick={onDownload}
            aria-disabled={isBusy}
            aria-label={t('session.ariaDownload')}
          >
            <IconDownload aria-hidden="true" />
            {t('session.download')}
          </button>

          {/* The soft gate, AFTER the download button — beside the value, never
              in front of it. Which of the two moments this is decides the copy
              and the recorded capture point: hitting the cap is the higher-intent
              one (they narrated and want more), finishing on their own terms is
              the satisfied one. */}
          <DemoLeadForm
            capturePoint={reachedCap ? 'wall' : 'download'}
            sessionId={sessionId}
          />
        </div>
      ) : (
        <button
          type="button"
          className={styles.finalizeButton}
          onClick={onFinalize}
          aria-disabled={isBusy || totalRows === 0}
          aria-label={t('session.ariaFinalize')}
        >
          <IconDownload aria-hidden="true" />
          {t('session.finalizeAndDownload')}
        </button>
      )}
    </div>
  );
}
