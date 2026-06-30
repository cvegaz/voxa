-- Migration: 006_add_session_language
-- Description: Add a per-session language ("es"/"en") to template_sessions. The
--              language is fixed when the template is confirmed and drives the
--              transcription, enrichment, and extraction language for that
--              session's records (ADR-0012, todo #8).

ALTER TABLE template_sessions
    ADD COLUMN language VARCHAR(5) NOT NULL DEFAULT 'es';
