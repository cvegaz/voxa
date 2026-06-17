-- Rollback: 001_create_template_sessions
-- Description: Drop the template_sessions table

DROP INDEX IF EXISTS idx_template_sessions_status;
DROP TABLE IF EXISTS template_sessions;
