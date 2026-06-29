-- Rollback: 005_add_finalized_status
-- Description: Restore the status constraint without 'finalized'. Any rows
--              already in 'finalized' must be migrated back first, or this fails.

ALTER TABLE template_sessions DROP CONSTRAINT IF EXISTS chk_status;
ALTER TABLE template_sessions ADD CONSTRAINT chk_status
    CHECK (status IN ('pending', 'confirmed', 'replaced'));
