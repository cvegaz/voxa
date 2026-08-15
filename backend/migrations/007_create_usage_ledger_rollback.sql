-- Rollback: 007_create_usage_ledger
-- Description: Drop the usage_ledger table and its index.

DROP INDEX IF EXISTS idx_usage_ledger_created;
DROP TABLE IF EXISTS usage_ledger;
