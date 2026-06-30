import type { ColumnSchema } from '../types/template';
import { IconDocument } from './Icons';
import { useI18n } from '../i18n/LanguageContext';
import styles from './SchemaConfirmation.module.css';

export interface SchemaConfirmationProps {
  /** The extracted column schema to display */
  schema: ColumnSchema;
  /** The name of the uploaded file */
  fileName: string;
  /** Callback when the user confirms the schema */
  onConfirm: () => void;
  /** Callback when the user wants to discard and pick a different file */
  onChangeFile: () => void;
}

/**
 * Displays the extracted column schema in a table for user review.
 * Provides actions to confirm the schema or go back to file selection.
 */
export function SchemaConfirmation({
  schema,
  fileName,
  onConfirm,
  onChangeFile,
}: SchemaConfirmationProps) {
  const { t } = useI18n();
  return (
    <section className={styles.section} aria-labelledby="schema-confirmation-title">
      <h2 id="schema-confirmation-title" className={styles.title}>
        {t('schema.title')}
      </h2>
      <p className={styles.fileLine}>
        <IconDocument aria-hidden="true" />
        <span className={styles.fileName}>{fileName}</span>
      </p>

      <div className={styles.tableWrap}>
        <table
          className={styles.table}
          aria-label={t('schema.ariaTable')}
        >
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">{t('schema.colName')}</th>
              <th scope="col">{t('schema.colType')}</th>
              <th scope="col">{t('schema.colExample')}</th>
            </tr>
          </thead>
          <tbody>
            {schema.columns.map((col) => (
              <tr key={col.index}>
                <td className={styles.indexCell}>{col.index}</td>
                <td>{col.name}</td>
                <td>{col.dataType}</td>
                <td>{col.exampleValue}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className={styles.actions}>
        <button type="button" className={styles.confirmButton} onClick={onConfirm}>
          {t('schema.confirm')}
        </button>
        <button
          type="button"
          className={styles.changeButton}
          onClick={onChangeFile}
        >
          {t('schema.changeFile')}
        </button>
      </div>
    </section>
  );
}
