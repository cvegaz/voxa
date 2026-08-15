-- Migration: 010_create_contact_messages
-- Description: Create the contact_messages table for leads submitted from the
--              public landing page (POST /api/contact).
-- Requirements: landing page contact form (portfolio / sales hook)
--
-- RENUMBERED 2026-08-14, from 006. It shared that number with
-- 006_add_session_language: the runner sorts by filename, so both applied in a
-- deterministic order and nothing was broken — but a number that no longer
-- identifies a single migration cannot express order, and a rollback would have
-- had to guess which "006" was meant.
--
-- The number is an APPLY-ORDER sequence, not a historical record; git holds the
-- history. This table was in fact created before 007-009 and depends on none of
-- them, so taking the next free number is safe. `scripts/migrate.py` now refuses
-- to run when two migrations share a number, so this cannot recur silently.

CREATE TABLE IF NOT EXISTS contact_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    email VARCHAR(254) NOT NULL,
    company VARCHAR(120),
    message TEXT NOT NULL,
    source_lang VARCHAR(5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- IF NOT EXISTS so the renumbering above is survivable: a database that already
-- applied this file under its old name sees the new name as unapplied and runs
-- it again. The CREATE TABLE was already idempotent; now the index is too.
CREATE INDEX IF NOT EXISTS idx_contact_messages_created ON contact_messages(created_at);
