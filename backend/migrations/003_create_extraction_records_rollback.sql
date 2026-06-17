-- Rollback: 003_create_extraction_records
-- Description: Drop the extraction_records table and remove file_path column from template_sessions

ALTER TABLE template_sessions DROP COLUMN IF EXISTS file_path;

DROP INDEX IF EXISTS idx_extraction_records_created;
DROP INDEX IF EXISTS idx_extraction_records_session;
DROP TABLE IF EXISTS extraction_records;
