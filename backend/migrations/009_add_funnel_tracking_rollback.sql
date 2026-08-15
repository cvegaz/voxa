-- Rollback: 009_add_funnel_tracking
-- Description: Drop the funnel milestone columns and their index.

DROP INDEX IF EXISTS idx_template_sessions_created;

ALTER TABLE template_sessions
    DROP COLUMN IF EXISTS first_narration_at,
    DROP COLUMN IF EXISTS downloaded_at,
    DROP COLUMN IF EXISTS wall_hit_at,
    DROP COLUMN IF EXISTS wall_kind,
    DROP COLUMN IF EXISTS client_browser,
    DROP COLUMN IF EXISTS client_platform;
