-- Migration: 003_create_extraction_records
-- Description: Create the extraction_records table for persisting LLM extraction results
--              and add file_path column to template_sessions
-- Requirements: 2.1, 2.2

CREATE TABLE IF NOT EXISTS extraction_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES template_sessions(id),
    row_number INTEGER NOT NULL,
    record_json JSONB NOT NULL,
    transcribed_text TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT chk_extraction_status CHECK (status IN ('completed', 'failed')),
    CONSTRAINT chk_row_number CHECK (row_number >= 4)
);

CREATE INDEX idx_extraction_records_session ON extraction_records(session_id);
CREATE INDEX idx_extraction_records_created ON extraction_records(created_at);

-- Add file_path column to template_sessions for tracking the Excel file location on disk
ALTER TABLE template_sessions ADD COLUMN file_path VARCHAR(500);
