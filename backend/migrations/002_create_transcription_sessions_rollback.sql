-- Rollback: 002_create_transcription_sessions
-- Description: Drop the transcription_sessions table

DROP INDEX IF EXISTS idx_transcription_sessions_template;
DROP INDEX IF EXISTS idx_transcription_sessions_status;
DROP TABLE IF EXISTS transcription_sessions;
