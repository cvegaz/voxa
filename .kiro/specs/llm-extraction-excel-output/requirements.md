# Requirements Document

## Introduction

This module receives the transcribed text from the `audio-transcription-controls` module and, using the Esquema_Columnas confirmed by `excel-template-loader`, analyzes it with a large language model (LLM) to extract the values for each field. The extracted values are inserted as a new row in the Excel file and shown to the user in real time in a tabular view at the bottom of the main screen.

## Glossary

- **Aplicacion**: The desktop/web system described in this document.
- **Esquema_Columnas**: Detected structure of the active Excel file (name, Tipo_Dato, and Ejemplo_Valor per column). Provided by the `excel-template-loader` module.
- **Tipo_Dato**: Expected format of the value to be extracted for a column (e.g., `texto`, `número entero`, `fecha DD/MM/YYYY`, `booleano`).
- **Ejemplo_Valor**: Illustration of the type of content that may appear in an audio narration for a given field.
- **Texto_Transcrito**: Input text coming from the `audio-transcription-controls` module.
- **LLM_Processor**: Component that analyzes the Texto_Transcrito using the Esquema_Columnas to extract the values corresponding to each field.
- **Registro**: Set of extracted values corresponding to a row of the Archivo_Excel, with one value (or empty) for each column of the Esquema_Columnas.
- **Archivo_Excel**: Active `.xlsx` file loaded by the `excel-template-loader` module. The actual data is added starting from row 4.
- **Vista_Excel**: Component that displays the current content of the Archivo_Excel in the user interface.
- **Pantalla_Principal**: Main interface of the Aplicacion where all user interactions take place.

---

## Requirements

### Requirement 1: Field extraction using an LLM

**User Story:** As a user, I want the application to automatically analyze the transcribed text to extract the data corresponding to the columns of my Excel file, using the data types and examples defined in the template to improve extraction accuracy.

#### Acceptance Criteria

1. WHEN the LLM_Processor receives the Texto_Transcrito, THE LLM_Processor SHALL use the active Esquema_Columnas — including the name, Tipo_Dato, and Ejemplo_Valor of each column — to build the extraction context sent to the language model.
2. WHEN the LLM_Processor analyzes the Texto_Transcrito, THE LLM_Processor SHALL attempt to identify a value for each field of the Esquema_Columnas, using the Tipo_Dato as a format constraint and the Ejemplo_Valor as a reference for the expected type of content.
3. WHEN the LLM_Processor completes the analysis of the Texto_Transcrito, THE LLM_Processor SHALL build a Registro with the extracted values, assigning an empty value to any field of the Esquema_Columnas that it could not identify.
4. IF the LLM_Processor cannot identify the value of any field of the Registro, THEN THE LLM_Processor SHALL assign an empty value to that field and continue building the Registro.
5. IF the LLM_Processor receives an empty Texto_Transcrito, THEN THE Aplicacion SHALL display an error message indicating that the text contains no processable information and preserve the text box in its current state.
6. IF any failure occurs during LLM processing, including communication errors or internal processing errors, THEN THE Aplicacion SHALL display an error message indicating the cause of the failure and preserve the Texto_Transcrito in the text box so that the user can retry.

---

### Requirement 2: Insertion and saving into the Excel file

**User Story:** As a user, I want the extracted data to be saved automatically into the Excel file, so that all records accumulate in the same file I loaded as a template.

#### Acceptance Criteria

1. WHEN the LLM_Processor builds a Registro, THE Aplicacion SHALL add the Registro as a new row to the Archivo_Excel starting from row 4, respecting the column order of the Esquema_Columnas.
2. WHEN the Archivo_Excel is updated with a new Registro, THE Aplicacion SHALL save the changes to the Archivo_Excel on disk, overwriting the existing file.
3. IF an error occurs while saving the Archivo_Excel to disk, THEN THE Aplicacion SHALL display an error message indicating the cause of the failure and that the Registro was processed but not saved to the file.

---

### Requirement 3: Excel view

**User Story:** As a user, I want to see the state of the Excel file with the added records once processing finishes, so that I can verify that the data was saved correctly.

#### Acceptance Criteria

1. THE Vista_Excel SHALL display the content of the Archivo_Excel in a table at the bottom of the Pantalla_Principal, excluding the three header rows of the template.
2. WHILE the LLM_Processor is processing the Texto_Transcrito, THE Vista_Excel SHALL remain hidden or unchanged, without showing the user the processing progress.
3. WHEN the LLM_Processor completes processing and the Registro is successfully added to the Archivo_Excel, THE Aplicacion SHALL update the Vista_Excel with the full content of the Archivo_Excel (including the new Registro) and present it to the user.
4. WHEN the `excel-template-loader` module confirms a valid Archivo_Excel, THE Vista_Excel SHALL display all the existing data rows of the file (row 4 onward), including previously saved records.
