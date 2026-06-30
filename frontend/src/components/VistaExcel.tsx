import type { ColumnDef } from '../types/template';
import type { ExtractionRecord } from '../types/extraction';
import { useI18n } from '../i18n/LanguageContext';
import styles from './VistaExcel.module.css';

export interface VistaExcelProps {
  /** Column definitions from the active ColumnSchema */
  columns: ColumnDef[];
  /** Extraction records (data rows, row 4+) */
  records: ExtractionRecord[];
  /** Whether extraction processing is in progress */
  isLoading: boolean;
}

/**
 * VistaExcel renders an HTML table showing the Excel file contents (row 4+).
 *
 * - Displays column headers from the ColumnSchema.
 * - Shows one row per extraction record with values mapped by columnName.
 * - Remains unchanged during processing (does not show progress).
 * - Updates with full content (including new record) after successful extraction.
 * - Shows pre-existing records on session load.
 *
 * Validates: Requirements 3.1, 3.2, 3.3, 3.4
 */
export function VistaExcel({ columns, records, isLoading }: VistaExcelProps) {
  const { t } = useI18n();
  // During loading, the view remains unchanged (requirement 3.2).
  // aria-busy communicates the processing state to assistive technologies.

  if (records.length === 0) {
    return (
      <div className={styles.container} aria-busy={isLoading}>
        <p className={styles.emptyMessage}>{t('vista.empty')}</p>
      </div>
    );
  }

  return (
    <div className={styles.container} aria-busy={isLoading}>
      <table className={styles.table} aria-label={t('vista.ariaTable')}>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.index} scope="col">
                {col.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.extractionId}>
              {columns.map((col) => {
                const cellValue =
                  record.record.find((rv) => rv.columnName === col.name)?.value ?? '';
                return <td key={col.index}>{cellValue}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
