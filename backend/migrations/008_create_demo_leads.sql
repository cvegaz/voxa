-- Migration: 008_create_demo_leads
-- Description: Emails volunteered from inside the demo, at the two moments of
--              demonstrated interest (ADR-0019 §5).
-- Requirements: lead capture for the public demo.
--
-- Deliberately SEPARATE from contact_messages even though both hold an email.
-- They answer different questions and carry different confidence: a contact
-- message is somebody who wrote to you on purpose; a demo lead is somebody who
-- used the product and volunteered an address on the way out. Merging them would
-- average away exactly the signal worth measuring — cost per captured lead, and
-- which of the two moments converts.
--
-- Every address here is UNVERIFIED by construction (verification needs a sending
-- domain that does not exist yet). The table name and this comment are the record
-- of that: these are leads to qualify, never confirmed contacts.

CREATE TABLE IF NOT EXISTS demo_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(254) NOT NULL,
    -- Where the address was volunteered: 'download' | 'wall'. Kept so the two
    -- capture points can be compared instead of guessed at.
    capture_point VARCHAR(16) NOT NULL,
    -- Template session it came from, when there is one. Nullable and NOT a
    -- foreign key on purpose: the lead must outlive the session that produced it.
    session_id UUID,
    source_lang VARCHAR(5),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Only ever read as "leads over a period", grouped by capture point.
CREATE INDEX idx_demo_leads_created ON demo_leads(created_at);
