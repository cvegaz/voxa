-- Rollback: 006_add_session_language

ALTER TABLE template_sessions
    DROP COLUMN IF EXISTS language;
