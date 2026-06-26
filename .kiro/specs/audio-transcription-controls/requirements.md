# Requirements Document

## Introduction

This module covers capturing audio from the user's microphone, transcribing it automatically to text, and the main-screen controls that let the user accept the transcribed text for processing or discard it to start a new recording. It depends on the `excel-template-loader` module having loaded and confirmed a valid Esquema_Columnas before it can operate.

## Glossary

- **Aplicacion**: The desktop/web system described in this document.
- **Esquema_Columnas**: Detected structure of the active Excel file. Provided by the `excel-template-loader` module. It must be confirmed before this module can operate.
- **Grabador**: Interface component that handles capturing audio from the user's microphone.
- **Audio**: Voice signal captured from the user's microphone during a recording session.
- **Transcriptor**: Component responsible for converting the recorded audio into readable text.
- **Texto_Transcrito**: Text resulting from the transcription of the recorded audio.
- **LLM_Processor**: Component of the `llm-extraction-excel-output` module that receives the Texto_Transcrito for analysis. Referenced here only as the destination of the flow.
- **Pantalla_Principal**: Main interface of the Aplicacion where all user interactions take place.

---

## Requirements

### Requirement 1: Audio recording

**User Story:** As a user, I want to record my voice through the microphone, so that the application captures what I say and processes it.

#### Acceptance Criteria

1. THE Grabador SHALL display a button labeled "Grabar" on the Pantalla_Principal.
2. IF microphone permission has not been granted previously, WHEN the user presses the "Grabar" button, THE Grabador SHALL request access to the device's microphone before starting capture.
3. WHEN microphone permission is granted and the user presses the "Grabar" button, THE Grabador SHALL start capturing audio from the microphone and display a visual indicator showing that recording is active.
4. WHEN the user presses the "Grabar" button a second time during an active session, THE Grabador SHALL stop capturing audio.
5. WHEN the Grabador stops capturing audio, THE Grabador SHALL send the Audio to the Transcriptor.
6. IF microphone access permission is denied, THEN THE Grabador SHALL display an error message indicating that microphone access is required to use this feature.
7. IF a hardware error occurs during audio capture, THEN THE Grabador SHALL stop recording and display an error message indicating that the audio device could not be accessed.

---

### Requirement 2: Audio-to-text transcription

**User Story:** As a user, I want the recorded audio to be converted automatically to text, so that I can review what I said before processing it.

#### Acceptance Criteria

1. WHEN the Grabador sends the Audio to the Transcriptor, THE Transcriptor SHALL process the audio and generate the Texto_Transcrito.
2. WHEN the Transcriptor generates the Texto_Transcrito, THE Aplicacion SHALL display the Texto_Transcrito in an editable text box located below the record button on the Pantalla_Principal.
3. WHILE the Transcriptor is processing the Audio, THE Aplicacion SHALL display a visual progress indicator on the Pantalla_Principal, and that indicator SHALL disappear when transcription finishes (whether successfully or with an error).
4. IF the Audio has a duration of less than 1 second, THEN THE Transcriptor SHALL reject the Audio before starting transcription and display a message indicating that the audio is too short to be processed.
5. IF the Audio has a duration longer than 30 seconds, THEN THE Grabador SHALL automatically stop capturing audio and send the Audio to the Transcriptor with the 30 seconds recorded.
6. IF the Transcriptor cannot process the Audio due to a service error, THEN THE Aplicacion SHALL display a descriptive error message, clear the Texto_Transcrito from the text box, and reset the Grabador to its initial state.
6. THE Aplicacion SHALL allow the user to manually edit the Texto_Transcrito in the text box before proceeding.

---

### Requirement 3: Main-screen controls

**User Story:** As a user, I want controls to accept the transcribed text or clear the screen and start over, so that I can manage the data entry flow.

#### Acceptance Criteria

1. THE Aplicacion SHALL display an "Aceptar" button on the Pantalla_Principal.
2. THE Aplicacion SHALL display an "Agregar nuevo" button on the Pantalla_Principal.
3. WHEN the user presses the "Aceptar" button and a non-empty Texto_Transcrito exists, THE Aplicacion SHALL verify that a confirmed Esquema_Columnas exists and, if so, send the Texto_Transcrito to the LLM_Processor for analysis.
4. IF the user presses the "Aceptar" button and no Texto_Transcrito exists, THEN THE Aplicacion SHALL display a message indicating that they must first record and transcribe audio.
5. IF the user presses the "Aceptar" button and no confirmed Esquema_Columnas exists, THEN THE Aplicacion SHALL display a message indicating that they must first load and confirm an Excel file.
6. WHEN the user presses the "Agregar nuevo" button, THE Aplicacion SHALL clear the text box of the Texto_Transcrito and reset the Grabador to its initial state, keeping the confirmed Esquema_Columnas.
7. WHEN the user presses the "Aceptar" button and the conditions are valid, THE Aplicacion SHALL disable the "Aceptar" and "Agregar nuevo" buttons while the LLM_Processor processes the Texto_Transcrito, and re-enable them once processing completes.
8. WHEN a transcription or recording error occurs, THE Aplicacion SHALL automatically reset the Grabador to its initial state.
