-- Migration: 005_add_finalized_status
-- Description: Allow the 'finalized' status on template_sessions. A session is
--              finalized when the user finishes capturing (manually) or the row
--              cap is reached (ADR-0013); a finalized session accepts no more
--              extractions and its Excel can be downloaded.

ALTER TABLE template_sessions DROP CONSTRAINT IF EXISTS chk_status;
ALTER TABLE template_sessions ADD CONSTRAINT chk_status
    CHECK (status IN ('pending', 'confirmed', 'replaced', 'finalized'));
