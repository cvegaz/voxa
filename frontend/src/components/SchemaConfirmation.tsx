import type { ColumnSchema } from '../types/template';

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
  return (
    <section aria-labelledby="schema-confirmation-title">
      <h2 id="schema-confirmation-title">Esquema detectado</h2>
      <p>
        Archivo: <strong>{fileName}</strong>
      </p>

      <table aria-label="Esquema de columnas del archivo cargado">
        <thead>
          <tr>
            <th scope="col">#</th>
            <th scope="col">Nombre</th>
            <th scope="col">Tipo de Dato</th>
            <th scope="col">Ejemplo</th>
          </tr>
        </thead>
        <tbody>
          {schema.columns.map((col) => (
            <tr key={col.index}>
              <td>{col.index}</td>
              <td>{col.name}</td>
              <td>{col.dataType}</td>
              <td>{col.exampleValue}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div>
        <button type="button" onClick={onConfirm}>
          Confirmar
        </button>
        <button type="button" onClick={onChangeFile}>
          Cambiar archivo
        </button>
      </div>
    </section>
  );
}
