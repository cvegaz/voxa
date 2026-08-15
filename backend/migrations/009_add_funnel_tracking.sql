-- Migration: 009_add_funnel_tracking
-- Description: Per-session funnel milestones, so the month's data can tell
--              "nobody cared" apart from "it broke silently" (ADR-0019 §7).
-- Requirements: public demo traceability.
--
-- Columns on the session row rather than an events table. There is exactly one
-- row per session and six known milestones, so the whole funnel reads as a flat
-- SELECT instead of a GROUP BY over subqueries. The cost is a wider row that
-- mixes domain state with analytics; the day arbitrary events are needed, that
-- migration can be made with real data to justify its shape instead of guessing
-- at it now.
--
-- Two milestones are NOT added here because they already exist:
--   * "session started"   -> created_at / confirmed_at
--   * the industry signal -> schema_json already holds the column names, so a
--     separate column would be a second copy free to drift from the first.

ALTER TABLE template_sessions
    -- The headline metric of the month: did this session reach the "aha" moment?
    ADD COLUMN IF NOT EXISTS first_narration_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS downloaded_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS wall_hit_at TIMESTAMP WITH TIME ZONE,
    -- 'trial' (ran out of narrations) or 'budget' (the demo's spend ceiling).
    -- Very different stories: the first is a healthy visitor we should convert,
    -- the second is a cap that may need widening.
    ADD COLUMN IF NOT EXISTS wall_kind VARCHAR(16),
    -- Coarse buckets parsed from the User-Agent. Untrustworthy as a basis for
    -- CONTROL decisions (Phase 2 refuses to sniff it for that reason), perfectly
    -- serviceable as an aggregate diagnostic: if twenty Safari/iOS sessions die
    -- before the first narration, something is broken regardless of whether one
    -- of them lied.
    ADD COLUMN IF NOT EXISTS client_browser VARCHAR(40),
    ADD COLUMN IF NOT EXISTS client_platform VARCHAR(40);

-- The report always filters by when the session started.
CREATE INDEX IF NOT EXISTS idx_template_sessions_created
    ON template_sessions(created_at);
