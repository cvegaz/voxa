-- Migration: 001_create_template_sessions
-- Description: Create the template_sessions table for persisting Excel template upload sessions
-- Requirements: 1.8, 1.9, 1.10

CREATE TABLE IF NOT EXISTS template_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    schema_json JSONB NOT NULL,
    dataframe_json JSONB NOT NULL,
    user_context TEXT,
    enriched_context TEXT,
    file_name VARCHAR(255) NOT NULL,
    column_count INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confirmed_at TIMESTAMP WITH TIME ZONE,
    replaced_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_status CHECK (status IN ('pending', 'confirmed', 'replaced')),
    CONSTRAINT chk_columns CHECK (column_count BETWEEN 1 AND 8)
);

CREATE INDEX idx_template_sessions_status ON template_sessions(status);
