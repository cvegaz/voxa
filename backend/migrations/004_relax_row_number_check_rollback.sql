-- Rollback: 004_relax_row_number_check
-- Description: Restore the original ">= 4" constraint on extraction_records.row_number.

ALTER TABLE extraction_records DROP CONSTRAINT IF EXISTS chk_row_number;
ALTER TABLE extraction_records ADD CONSTRAINT chk_row_number CHECK (row_number >= 4);
