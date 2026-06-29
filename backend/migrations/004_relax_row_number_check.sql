-- Migration: 004_relax_row_number_check
-- Description: Relax the extraction_records.row_number constraint from ">= 4" to
--              ">= 2". See ADR-0013: the final Excel is reconstructed from the
--              schema with a single header row (row 1), so the first data record
--              lands on row 2 — not row 4 as the old 3-header-row template assumed.

ALTER TABLE extraction_records DROP CONSTRAINT IF EXISTS chk_row_number;
ALTER TABLE extraction_records ADD CONSTRAINT chk_row_number CHECK (row_number >= 2);
