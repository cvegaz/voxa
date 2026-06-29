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
}: SessionControlsProps) {
  const reachedCap = totalRows >= maxRows;

  return (
    <div className={styles.container}>
      <p className={styles.counter} aria-live="polite">
        {totalRows} / {maxRows} registros
      </p>

      {finalized ? (
        <div className={styles.finalized}>
          <p className={styles.finalizedMessage} role="status">
            {reachedCap
              ? `Límite de ${maxRows} registros alcanzado. La sesión se finalizó.`
              : 'Sesión finalizada.'}
          </p>
          <button
            type="button"
            className={styles.downloadButton}
            onClick={onDownload}
            aria-disabled={isBusy}
            aria-label="Descargar el archivo Excel"
          >
            Descargar Excel
          </button>
        </div>
      ) : (
        <button
          type="button"
          className={styles.finalizeButton}
          onClick={onFinalize}
          aria-disabled={isBusy || totalRows === 0}
          aria-label="Finalizar la sesión y descargar el Excel"
        >
          Finalizar y descargar
        </button>
      )}
    </div>
  );
}
