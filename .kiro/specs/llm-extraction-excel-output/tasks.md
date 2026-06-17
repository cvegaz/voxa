# Implementation Plan: LLM Extraction Excel Output

## Overview

Implement the extraction pipeline that receives transcribed text, sends it to Claude API with the column schema context, parses the structured JSON response, inserts the extracted record into the Excel file, persists it in PostgreSQL, and updates the frontend Vista_Excel component. The implementation uses FastAPI (backend), React/TypeScript (frontend), openpyxl for Excel I/O, pandas for DataFrame processing, and the Anthropic SDK for Claude API calls.

## Tasks

- [x] 1. Set up database schema and repository layer
  - [x] 1.1 Create the `extraction_records` table migration and alter `template_sessions`
    - Create SQL migration file with `extraction_records` table (id, session_id, row_number, record_json, transcribed_text, status, error_message, created_at)
    - Add indexes on session_id and created_at
    - Add `file_path` column to `template_sessions` table
    - _Requirements: 2.1, 2.2_

  - [x] 1.2 Implement `ExtractionRepository` class
    - Implement `save_extraction()` to persist extraction records
    - Implement `get_records()` to retrieve all records for a session
    - Implement `update_dataframe()` to update the DataFrame JSON in the session
    - Implement `get_session_with_context()` to fetch session with schema, enriched_context, and file_path
    - _Requirements: 2.1, 2.2, 3.4_

- [x] 2. Implement core extraction services
  - [x] 2.1 Implement `PromptBuilder` service
    - Create `PromptBuilder` class with `build()` method
    - Construct the system prompt with enriched context, column schema table (name, data_type, example_value), transcribed text, and JSON response instructions
    - Ensure all columns from schema are included in the prompt
    - _Requirements: 1.1, 1.2_

  - [ ]* 2.2 Write property test for PromptBuilder — Property 1: Prompt completeness
    - **Property 1: Prompt completeness**
    - Use Hypothesis to generate random ColumnSchema (1-8 columns) and random transcribed text
    - Assert the built prompt contains every column's name, data_type, and example_value, plus the full transcribed text
    - **Validates: Requirements 1.1**

  - [x] 2.3 Implement `ResponseParser` service
    - Create `ResponseParser` class with `parse()` method
    - Parse raw JSON string response from Claude
    - Validate keys against ColumnSchema — assign empty string for missing/null values
    - Ignore extra keys not present in schema
    - Raise appropriate errors for invalid JSON
    - _Requirements: 1.3, 1.4_

  - [ ]* 2.4 Write property test for ResponseParser — Property 2: Response parsing normalization
    - **Property 2: Response parsing normalization**
    - Use Hypothesis to generate random ColumnSchema and random JSON responses (with missing keys, null values, extra keys)
    - Assert output dict has exactly one entry per schema column, no extra keys, and missing/null values are empty strings
    - **Validates: Requirements 1.3, 1.4**

  - [x] 2.5 Implement `LLMExtractionService` with Claude API integration
    - Create `LLMExtractionService` class with `extract()` async method
    - Use the `anthropic` Python SDK to call Claude API
    - Implement retry logic: max 2 retries with exponential backoff (1s, 3s) for transient errors (timeout, 5xx)
    - Parse Claude's text response as JSON
    - _Requirements: 1.1, 1.2, 1.6_

  - [x] 2.6 Implement `ExcelWriter` service
    - Create `ExcelWriter` class with `write()` method
    - Export DataFrame to .xlsx using openpyxl engine
    - Preserve header rows (1-3) and write data starting from row 4
    - Overwrite the existing file on disk
    - _Requirements: 2.2_

  - [ ]* 2.7 Write property test for ExcelWriter — Property 4: Excel write/read round-trip
    - **Property 4: Excel write/read round-trip**
    - Use Hypothesis to generate random DataFrames with valid data and ColumnSchema
    - Write DataFrame to temp .xlsx file and read back rows 4+ — assert data equivalence
    - **Validates: Requirements 2.2**

- [x] 3. Implement orchestrator and API endpoints
  - [x] 3.1 Implement `ExtractionOrchestrator` service
    - Create `ExtractionOrchestrator` class wiring PromptBuilder, LLMExtractionService, ResponseParser, ExcelWriter, and ExtractionRepository
    - Implement `process()` method: get session → build prompt → call LLM → parse response → insert row into DataFrame → write .xlsx → persist in DB → return result
    - Compute correct `row_number` (4 for first record, incrementing for subsequent)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2_

  - [ ]* 3.2 Write property test for record insertion — Property 3: Record insertion invariant
    - **Property 3: Record insertion invariant**
    - Use Hypothesis to generate random DataFrames (0+ rows) and random Record dicts
    - Assert inserting a Record increases row count by exactly 1 and the last row matches the Record values
    - **Validates: Requirements 2.1**

  - [x] 3.3 Implement `POST /api/extraction/process` endpoint
    - Accept `ExtractionRequest` body (session_id, transcribed_text)
    - Validate transcribed_text is non-empty (return 422 for empty text)
    - Validate session exists and is confirmed (return 404/422 otherwise)
    - Call `ExtractionOrchestrator.process()`
    - Return `ExtractionResult` (extraction_id, record, row_number)
    - Handle errors with appropriate HTTP codes and error_code responses
    - _Requirements: 1.1, 1.5, 1.6, 2.1, 2.3_

  - [x] 3.4 Implement `GET /api/extraction/records/{session_id}` endpoint
    - Accept session_id path parameter
    - Return `RecordsResponse` (records list + total_rows)
    - Return only data rows (not headers)
    - _Requirements: 3.1, 3.4_

- [x] 4. Checkpoint — Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement frontend extraction flow
  - [x] 5.1 Create `ExtractionService` API client
    - Implement `processExtraction(sessionId, transcribedText)` calling POST /api/extraction/process
    - Implement `getRecords(sessionId)` calling GET /api/extraction/records/{session_id}
    - Set 60s timeout for extraction calls
    - Handle error responses and map to user-friendly messages
    - _Requirements: 1.5, 1.6_

  - [x] 5.2 Implement `ExtractionStatus` component
    - Display states: idle, processing (spinner), success (row number), error (message + retry)
    - Show spinner on "Aceptar" button during processing
    - Disable buttons during processing
    - Show error inline (422) or as toast/banner (5xx) with "Reintentar" option
    - _Requirements: 1.5, 1.6_

  - [x] 5.3 Implement `VistaExcel` component
    - Render HTML table with columns from ColumnSchema
    - Show data rows only (row 4+), excluding header rows
    - Remain hidden or unchanged during processing
    - Update with full content (including new record) after successful extraction
    - Load and display pre-existing records on session load
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 5.4 Wire "Aceptar" button to extraction flow
    - On click: call `processExtraction` with current transcribed text and session_id
    - On success: refresh records via `getRecords`, update VistaExcel, show success status
    - On error: preserve transcribed text in textarea, show error status
    - _Requirements: 1.5, 1.6, 3.3_

  - [ ]* 5.5 Write frontend unit tests for VistaExcel and ExtractionStatus
    - Test VistaExcel renders data correctly with mocked records
    - Test VistaExcel stays unchanged during loading state
    - Test VistaExcel updates after successful extraction
    - Test ExtractionStatus shows correct states (idle, processing, success, error)
    - Test "Aceptar" button disabled during processing
    - Test transcribed text preserved after error
    - _Requirements: 3.1, 3.2, 3.3, 1.5, 1.6_

- [x] 6. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The backend uses FastAPI (Python), openpyxl, pandas, and the anthropic SDK
- The frontend uses React with TypeScript
- Retry logic for Claude API follows the same pattern as `excel-template-loader` (max 2 retries, 1s/3s backoff)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["2.1", "2.3", "2.5", "2.6"] },
    { "id": 3, "tasks": ["2.2", "2.4", "2.7", "3.1"] },
    { "id": 4, "tasks": ["3.2", "3.3", "3.4"] },
    { "id": 5, "tasks": ["5.1"] },
    { "id": 6, "tasks": ["5.2", "5.3"] },
    { "id": 7, "tasks": ["5.4"] },
    { "id": 8, "tasks": ["5.5"] }
  ]
}
```
