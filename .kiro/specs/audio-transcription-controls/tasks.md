# Implementation Plan: Audio Transcription Controls

## Overview

Implement the audio recording module, transcription via the OpenAI Whisper API, and the main-screen controls (Accept / Add new). The backend uses FastAPI with PostgreSQL, and the frontend uses React with TypeScript. It follows an incremental approach: first data models and backend services, then API endpoints, then frontend components, and finally full integration.

## Tasks

- [x] 1. Set up database schema and backend data models
  - [x] 1.1 Create the database migration for `transcription_sessions` table
    - Create SQL migration with the table definition, constraints (`chk_status`, `chk_duration`), and indexes (`idx_transcription_sessions_status`, `idx_transcription_sessions_template`)
    - Include foreign key reference to `template_sessions(id)`
    - _Requirements: 2.1, 3.3_

  - [x] 1.2 Create Pydantic models for request/response schemas
    - Implement `TranscribeResponse`, `AcceptRequest`, `AcceptResponse`, `ResetRequest`, `ResetResponse`, `TranscriptionSession`, and `ErrorResponse` models
    - Include field validations (e.g., `min_length=1` on `AcceptRequest.text`)
    - _Requirements: 2.1, 3.3, 3.4_

  - [x] 1.3 Implement `TranscriptionRepository` class
    - Implement `create_session`, `accept_session`, `discard_session`, and `get_session` methods
    - Use async database access with proper UUID handling
    - Handle timestamp updates for `accepted_at` and `discarded_at`
    - _Requirements: 2.1, 3.3, 3.6_

- [x] 2. Implement backend services
  - [x] 2.1 Implement `AudioValidator` service
    - Validate MIME type against allowed types: `audio/webm`, `audio/ogg`, `audio/mp4`, `audio/mpeg`, `audio/wav`
    - Validate duration between 1.0s and 30.0s
    - Return structured `ValidationResult` with appropriate error codes
    - _Requirements: 2.4, 2.5, 1.7_

  - [ ]* 2.2 Write property test for AudioValidator — minimum duration rejection
    - **Property 1: Audio below minimum duration is always rejected**
    - **Validates: Requirements 2.4**

  - [x] 2.3 Implement `WhisperTranscriptionService`
    - Configure OpenAI client with `whisper-1` model
    - Send audio file with correct MIME type to Whisper API
    - Implement retry logic: max 2 retries with exponential backoff (1s, 3s) for 5xx/timeout errors
    - Handle empty response and no-speech errors
    - _Requirements: 2.1, 2.6_

  - [x] 2.4 Implement `AcceptanceValidator` service
    - Verify transcription session exists and is in `pending` status
    - Verify text is non-empty and not whitespace-only
    - Verify that a confirmed `Esquema_Columnas` exists (query `excel-template-loader` module)
    - Return structured `ValidationResult` with error codes `EMPTY_TRANSCRIPTION`, `NO_CONFIRMED_SCHEMA`, `SESSION_NOT_FOUND`
    - _Requirements: 3.3, 3.4, 3.5_

  - [ ]* 2.5 Write property test for AcceptanceValidator — non-empty text and confirmed schema
    - **Property 2: Acceptance requires non-empty text and confirmed schema**
    - **Validates: Requirements 3.3**

  - [ ]* 2.6 Write property test for AcceptanceValidator — empty/whitespace rejection
    - **Property 3: Empty or whitespace-only text is always rejected on acceptance**
    - **Validates: Requirements 3.4**

- [x] 3. Implement API endpoints
  - [x] 3.1 Implement `POST /api/transcriptions/transcribe` endpoint
    - Accept `multipart/form-data` with audio file and duration
    - Call `AudioValidator`, then `WhisperTranscriptionService`, then `TranscriptionRepository.create_session`
    - Return `TranscribeResponse` with `transcription_id` and `text`
    - Handle errors with structured `ErrorResponse` (422, 502)
    - _Requirements: 1.5, 2.1, 2.4, 2.5, 2.6_

  - [x] 3.2 Implement `POST /api/transcriptions/accept` endpoint
    - Accept JSON body with `transcription_id` and `text`
    - Call `AcceptanceValidator`, then `TranscriptionRepository.accept_session`
    - Return `AcceptResponse` with `status: "accepted"`
    - Handle errors: 422 (empty text, no schema), 404 (session not found), 409 (no confirmed schema)
    - _Requirements: 3.3, 3.4, 3.5, 3.7_

  - [x] 3.3 Implement `POST /api/transcriptions/reset` endpoint
    - Accept JSON body with `transcription_id`
    - Call `TranscriptionRepository.discard_session`
    - Return `ResetResponse` with `status: "reset"`
    - _Requirements: 3.6_

  - [x] 3.4 Implement `GET /api/transcriptions/{id}` endpoint
    - Return full `TranscriptionSession` data
    - Handle 404 if session not found
    - _Requirements: 2.1_

  - [ ]* 3.5 Write property test for reset — preserves schema while clearing state
    - **Property 4: Reset preserves schema while clearing transcription state**
    - **Validates: Requirements 3.6**

- [x] 4. Checkpoint - Backend verification
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement frontend components
  - [x] 5.1 Implement `AudioRecorder` component
    - Render "Grabar" button with states: idle, recording, processing, error
    - Request microphone permission via `navigator.mediaDevices.getUserMedia` on first press
    - Start `MediaRecorder` with `audio/webm;codecs=opus` (fallback `audio/ogg`)
    - Toggle recording on button press (start/stop)
    - Show red pulse animation and timer during recording
    - Auto-stop at 30 seconds
    - Client-side duration validation (reject < 1s with error message)
    - Handle permission denied and hardware errors with appropriate messages
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 2.5_

  - [x] 5.2 Implement `TranscriptionDisplay` component
    - Render editable textarea below the recorder
    - Show spinner during transcription processing (`isLoading` state)
    - Display transcribed text once received
    - Allow user to edit text before accepting
    - Clear text on error or reset
    - _Requirements: 2.2, 2.3, 2.6, 2.6_

  - [x] 5.3 Implement `ControlButtons` component
    - Render "Aceptar" and "Agregar nuevo" buttons
    - "Aceptar" enabled only when text is non-empty and schema is confirmed
    - "Agregar nuevo" enabled always except during LLM processing
    - Both disabled during LLM processing
    - Show contextual error messages when preconditions not met
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.7_

  - [x] 5.4 Implement API service layer (frontend)
    - Create `transcriptionApi` module with functions: `transcribeAudio`, `acceptTranscription`, `resetTranscription`
    - Handle multipart/form-data for audio upload
    - Configure timeouts: 30s for transcription, 60s for acceptance
    - Map error responses to user-facing messages
    - _Requirements: 2.1, 3.3, 3.6_

- [x] 6. Integrate frontend components and wire state management
  - [x] 6.1 Compose main transcription page with all components
    - Wire `AudioRecorder` → `TranscriptionDisplay` → `ControlButtons` in a parent component
    - Manage shared state: recorder status, transcription text, transcription ID, loading states
    - Connect "Aceptar" to trigger LLM module (downstream dependency)
    - Connect "Agregar nuevo" to reset all component states
    - Implement error-driven auto-reset of recorder to idle state
    - _Requirements: 1.5, 2.2, 3.3, 3.6, 3.7, 3.8_

  - [ ]* 6.2 Write property test for error reset behavior
    - **Property 5: Any error resets recorder to initial state**
    - **Validates: Requirements 1.7, 2.6, 3.8**

  - [ ]* 6.3 Write frontend unit tests
    - Test component rendering (AudioRecorder, TranscriptionDisplay, ControlButtons)
    - Test button interactions: Grabar toggle, Aceptar, Agregar nuevo
    - Test error states and loading indicators
    - Mock `navigator.mediaDevices` for permission scenarios
    - Test timer and auto-stop at 30s
    - Test text editing in TranscriptionDisplay
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.2, 2.3, 3.1, 3.2_

- [x] 7. Final checkpoint - Full integration verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Backend uses Python (FastAPI + pytest + Hypothesis), frontend uses TypeScript (React + Vitest + React Testing Library)
- The `excel-template-loader` module must be operational for the acceptance flow to work end-to-end
- Audio is processed in-memory and never persisted; only the transcribed text is stored in PostgreSQL

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3"] },
    { "id": 2, "tasks": ["2.1", "2.3", "2.4"] },
    { "id": 3, "tasks": ["2.2", "2.5", "2.6", "3.1", "3.2", "3.3", "3.4"] },
    { "id": 4, "tasks": ["3.5", "5.1", "5.2", "5.3", "5.4"] },
    { "id": 5, "tasks": ["6.1"] },
    { "id": 6, "tasks": ["6.2", "6.3"] }
  ]
}
```
