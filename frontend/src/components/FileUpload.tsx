import { useCallback, useRef, useState } from 'react';
import type { UploadResponse } from '../types/template';
import { TemplateApiError } from '../types/template';
import { templateApi } from '../services/templateApi';
import { IconUpload, IconAlert } from './Icons';
import { useI18n } from '../i18n/LanguageContext';
import styles from './FileUpload.module.css';

type UploadState = 'idle' | 'uploading' | 'error';

export interface FileUploadProps {
  /** Called when a file upload succeeds with the backend response */
  onUploadSuccess: (response: UploadResponse) => void;
}

/**
 * FileUpload component providing drag & drop and click-to-select
 * file upload for .xlsx Excel template files.
 *
 * States:
 * - idle: shows the drop zone with instructions
 * - uploading: shows a spinner while the file is being processed
 * - error: shows the error message with a retry button
 */
export function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const { t } = useI18n();
  const [state, setState] = useState<UploadState>('idle');
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = useCallback(
    async (file: File) => {
      setState('uploading');
      setErrorMessage('');

      try {
        const response = await templateApi.uploadTemplate(file);
        setState('idle');
        onUploadSuccess(response);
      } catch (error: unknown) {
        if (error instanceof TemplateApiError) {
          setErrorMessage(error.userMessage);
        } else {
          setErrorMessage(t('common.unexpectedError'));
        }
        setState('error');
      }
    },
    [onUploadSuccess, t]
  );

  const validateAndUpload = useCallback(
    (file: File) => {
      // Client-side extension check for immediate feedback
      if (!file.name.toLowerCase().endsWith('.xlsx')) {
        setErrorMessage(t('upload.invalidExtension'));
        setState('error');
        return;
      }
      handleUpload(file);
    },
    [handleUpload, t]
  );

  const handleFileChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (file) {
        validateAndUpload(file);
      }
      // Reset input so the same file can be re-selected
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    [validateAndUpload]
  );

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setIsDragOver(false);

      const file = event.dataTransfer.files[0];
      if (file) {
        validateAndUpload(file);
      }
    },
    [validateAndUpload]
  );

  const handleDragOver = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setIsDragOver(true);
    },
    []
  );

  const handleDragLeave = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setIsDragOver(false);
    },
    []
  );

  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        fileInputRef.current?.click();
      }
    },
    []
  );

  const handleRetry = useCallback(() => {
    setState('idle');
    setErrorMessage('');
  }, []);

  if (state === 'uploading') {
    return (
      <div className={styles.container}>
        <div
          className={styles.uploading}
          role="status"
          aria-label={t('upload.ariaUploading')}
        >
          <div className={styles.spinner} aria-hidden="true" />
          <p className={styles.uploadingText}>{t('upload.processing')}</p>
        </div>
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div className={styles.container}>
        <div
          className={styles.errorContainer}
          role="alert"
          aria-live="assertive"
        >
          <span className={styles.errorIcon} aria-hidden="true">
            <IconAlert size={32} />
          </span>
          <p className={styles.errorMessage}>{errorMessage}</p>
          <button
            type="button"
            className={styles.retryButton}
            onClick={handleRetry}
            aria-label={t('upload.ariaRetry')}
          >
            {t('common.retry')}
          </button>
        </div>
      </div>
    );
  }

  // idle state
  const dropZoneClasses = [
    styles.dropZone,
    isDragOver ? styles.dropZoneDragOver : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={styles.container}>
      <div
        className={dropZoneClasses}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
        aria-label={t('upload.ariaDropzone')}
      >
        <span className={styles.icon} aria-hidden="true">
          <IconUpload size={28} />
        </span>
        <p className={styles.label}>
          {t('upload.dropPrefix')}
          <span className={styles.labelHighlight}>{t('upload.dropHighlight')}</span>
        </p>
        <p className={styles.hint}>{t('upload.hint')}</p>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx"
        onChange={handleFileChange}
        className={styles.hiddenInput}
        aria-hidden="true"
        tabIndex={-1}
      />
    </div>
  );
}
