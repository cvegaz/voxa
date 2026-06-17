-- Migration: 002_create_transcription_sessions
-- Description: Create the transcription_sessions table for persisting audio transcription sessions
-- Requirements: 2.1, 3.3

CREATE TABLE IF NOT EXISTS transcription_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_session_id UUID NOT NULL REFERENCES template_sessions(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    original_text TEXT NOT NULL,
    final_text TEXT,
    duration_seconds NUMERIC(5, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accepted_at TIMESTAMP WITH TIME ZONE,
    discarded_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_status CHECK (status IN ('pending', 'accepted', 'discarded')),
    CONSTRAINT chk_duration CHECK (duration_seconds BETWEEN 1.0 AND 30.0)
);

CREATE INDEX idx_transcription_sessions_status ON transcription_sessions(status);
CREATE INDEX idx_transcription_sessions_template ON transcription_sessions(template_session_id);
