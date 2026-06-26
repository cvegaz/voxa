# Implementation Plan: Excel Template Loader

## Overview

Implement the Excel template loading module that allows users to upload `.xlsx` files, validates their structure (extension, max 8 columns, rows 1-3 complete), extracts the column schema, converts the content to a pandas DataFrame, presents the schema for confirmation, collects a user-provided context description, and sends it to the OpenAI API for enrichment. The backend uses FastAPI with openpyxl and pandas; the frontend uses React with TypeScript.

## Tasks

- [x] 1. Set up database schema and repository layer
  - [x] 1.1 Create the `template_sessions` table migration
    - Create SQL migration file with `template_sessions` table (id UUID, status, schema_json JSONB, dataframe_json JSONB, user_context, enriched_context, file_name, column_count, created_at, confirmed_at, replaced_at)
    - Add CHECK constraints for status and column_count
    - Add index on status column
    - _Requirements: 1.8, 1.9, 1.10_

  - [x] 1.2 Implement `TemplateRepository` class
    - Implement `create_session()` to persist a new template session with status `pending`
    - Implement `confirm_session()` to update session with enriched_context and status `confirmed`
    - Implement `get_active_session()` to retrieve the latest confirmed session
    - Implement `replace_previous_sessions()` to mark previous pending/confirmed sessions as `replaced`
    - _Requirements: 1.8, 1.9, 1.10_

- [x] 2. Implement file validation and schema extraction services
  - [x] 2.1 Implement `ExcelValidator` service
    - Create `ExcelValidator` class with `validate()` method
    - Validate file extension is `.xlsx`
    - Load workbook with openpyxl and validate column count (1-8)
    - Validate row 1 has at least one non-empty column name
    - Validate row 2 has non-empty Tipo_Dato for all named columns
    - Validate row 3 has non-empty Ejemplo_Valor for all named columns
    - Return `ValidationResult` with error_code and affected columns on failure
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 1.7_

  - [ ]* 2.2 Write property test for column limit validation — Property 2
    - **Property 2: Files exceeding maximum columns are rejected**
    - Use Hypothesis to generate Excel files with more than 8 columns (random content)
    - Assert validator rejects every file and returns `TOO_MANY_COLUMNS` error code
    - **Validates: Requirements 1.3**

  - [ ]* 2.3 Write property test for incomplete header rows — Property 3
    - **Property 3: Files with incomplete header rows are rejected**
    - Use Hypothesis to generate Excel files where at least one named column has an empty cell in row 2 or row 3
    - Assert validator rejects and identifies the affected columns in the error
    - **Validates: Requirements 1.4, 1.5, 1.6**

  - [ ]* 2.4 Write property test for non-xlsx extension — Property 4
    - **Property 4: Non-xlsx files are rejected**
    - Use Hypothesis to generate filenames with extensions other than `.xlsx`
    - Assert validator rejects before attempting to read file contents
    - **Validates: Requirements 1.7**

  - [x] 2.5 Implement `SchemaExtractor` service
    - Create `SchemaExtractor` class with `extract()` method
    - Read rows 1-3 from the workbook and build `ColumnSchema` (list of `ColumnDef`)
    - Each `ColumnDef` contains index, name, data_type, and example_value
    - _Requirements: 1.2_

  - [ ]* 2.6 Write property test for schema extraction round-trip — Property 1
    - **Property 1: Schema extraction round-trip**
    - Use Hypothesis to generate valid Excel files (1-8 columns, rows 1-3 non-empty)
    - Extract schema and compare against original header data — assert same column names, types, and examples in same order
    - **Validates: Requirements 1.2**

  - [x] 2.7 Implement `DataFrameConverter` service
    - Create `DataFrameConverter` class with `convert()` method
    - Convert workbook content to pandas DataFrame using the extracted schema
    - Use column names from row 1 as DataFrame headers
    - Data starts from row 4
    - _Requirements: 1.2, 1.9_

- [x] 3. Implement context validation and LLM enrichment services
  - [x] 3.1 Implement `ContextValidator` service
    - Create `ContextValidator` class with `validate()` method
    - Validate context string length is between 50 and 3000 characters
    - Return appropriate error codes: `CONTEXT_TOO_SHORT` or `CONTEXT_TOO_LONG`
    - _Requirements: 3.2, 3.4, 3.5_

  - [ ]* 3.2 Write property test for context length validation — Property 7
    - **Property 7: Context length outside valid range is rejected**
    - Use Hypothesis to generate strings with length < 50 or > 3000
    - Assert validator rejects each and returns the appropriate error message
    - **Validates: Requirements 3.2, 3.4**

  - [x] 3.3 Implement `LLMEnrichmentService`
    - Create `LLMEnrichmentService` class with `enrich()` async method
    - Build prompt with user context + column schema (names, types, examples)
    - Call the OpenAI API using the `openai` Python SDK
    - Implement retry logic: max 2 retries with exponential backoff (1s, 3s) for transient errors
    - Return enriched context string
    - Handle errors: `LLM_UNAVAILABLE` for network/timeout, `LLM_INVALID_RESPONSE` for empty/invalid response
    - _Requirements: 3.6, 3.7, 3.8, 3.9_

- [x] 4. Implement API endpoints
  - [x] 4.1 Implement `POST /api/templates/upload` endpoint
    - Accept `multipart/form-data` with file field
    - Call `ExcelValidator.validate()` — return 422 with error details on failure
    - Call `SchemaExtractor.extract()` to build schema
    - Call `DataFrameConverter.convert()` to get DataFrame
    - Call `TemplateRepository.replace_previous_sessions()` to mark old sessions as replaced
    - Call `TemplateRepository.create_session()` to persist new session
    - Return `UploadResponse` (session_id, schema, file_name)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.10_

  - [ ]* 4.2 Write property test for session replacement — Property 5
    - **Property 5: Replacing a file marks the previous session as replaced**
    - Use Hypothesis to generate sequences of two valid file uploads
    - Assert first session has status `replaced` and second has status `pending` or `confirmed`
    - **Validates: Requirements 1.10**

  - [x] 4.3 Implement `POST /api/templates/confirm` endpoint
    - Accept `ConfirmRequest` body (session_id, context)
    - Validate session exists and is in `pending` state — return 404 if not found
    - Call `ContextValidator.validate()` — return 422 with error details on failure
    - Call `LLMEnrichmentService.enrich()` with context and schema
    - Call `TemplateRepository.confirm_session()` to persist enriched context
    - Return `ConfirmResponse` (enriched_context)
    - _Requirements: 3.2, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

  - [x] 4.4 Implement `GET /api/templates/active` endpoint
    - Call `TemplateRepository.get_active_session()`
    - Return `ActiveSessionResponse` (session_id, schema, enriched_context, file_name, confirmed_at)
    - Return 404 if no active session exists
    - _Requirements: 1.8_

  - [x] 4.5 Implement `DELETE /api/templates/{session_id}` endpoint
    - Mark session as `replaced`
    - Return 204 No Content
    - Return 404 if session not found
    - _Requirements: 1.10_

- [x] 5. Checkpoint — Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement frontend components
  - [x] 6.1 Create API client service for template endpoints
    - Implement `uploadTemplate(file)` calling POST /api/templates/upload
    - Implement `confirmTemplate(sessionId, context)` calling POST /api/templates/confirm
    - Implement `getActiveSession()` calling GET /api/templates/active
    - Implement `deleteSession(sessionId)` calling DELETE /api/templates/{session_id}
    - Set 30s timeout for upload, 60s timeout for confirm
    - Handle error responses and map to user-friendly messages
    - _Requirements: 1.1, 3.8_

  - [x] 6.2 Implement `FileUpload` component
    - Create file input with `.xlsx` filter
    - Implement drag & drop zone
    - Display upload states: idle, uploading (spinner), error (inline message)
    - Show validation error messages from backend (422 responses)
    - On successful upload: store session_id and schema in state, navigate to schema confirmation
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 6.3 Implement `SchemaConfirmation` component
    - Render table with columns: #, Nombre, Tipo de Dato, Ejemplo
    - Display one row per column from the ColumnSchema
    - Include "Confirmar" button and "Cambiar archivo" button
    - "Cambiar archivo" discards current session and returns to FileUpload
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 6.4 Write property test for schema table rendering — Property 6
    - **Property 6: Schema table renders all column information**
    - Use fast-check to generate valid ColumnSchema (1-8 columns)
    - Render SchemaConfirmation and assert output contains every column's index, name, dataType, and exampleValue
    - **Validates: Requirements 2.2**

  - [x] 6.5 Implement `ContextInput` component
    - Create textarea with character counter (50-3000)
    - Real-time validation: show error if < 50 or > 3000 characters
    - Disable "Confirmar y Continuar" button until context is valid
    - On confirm: call `confirmTemplate()` API
    - Show progress indicator during the enrichment call
    - Show error with retry option on failure (5xx)
    - On success: store enriched context and enable recording controls
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.8, 3.9_

  - [ ]* 6.6 Write frontend unit tests for FileUpload, SchemaConfirmation, and ContextInput
    - Test FileUpload renders drag & drop zone and file input
    - Test FileUpload displays error messages on invalid file
    - Test SchemaConfirmation renders correct table data
    - Test SchemaConfirmation buttons trigger correct actions
    - Test ContextInput character counter updates in real time
    - Test ContextInput disables button when text is too short/long
    - Test ContextInput shows loading state during enrichment
    - _Requirements: 1.1, 2.2, 2.3, 2.5, 3.1, 3.2, 3.8_

- [x] 7. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The backend uses FastAPI (Python), openpyxl, pandas, and the `openai` SDK
- The frontend uses React with TypeScript
- Property-based tests use Hypothesis (Python backend) and fast-check (TypeScript frontend)
- Retry logic for the OpenAI API: max 2 retries with exponential backoff (1s, 3s)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "2.5", "2.7", "3.1"] },
    { "id": 3, "tasks": ["2.6", "3.2", "3.3"] },
    { "id": 4, "tasks": ["4.1"] },
    { "id": 5, "tasks": ["4.2", "4.3", "4.4", "4.5"] },
    { "id": 6, "tasks": ["6.1"] },
    { "id": 7, "tasks": ["6.2", "6.3", "6.5"] },
    { "id": 8, "tasks": ["6.4", "6.6"] }
  ]
}
```
