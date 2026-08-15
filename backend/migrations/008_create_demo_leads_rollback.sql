-- Rollback: 008_create_demo_leads
-- Description: Drop the demo_leads table and its index.

DROP INDEX IF EXISTS idx_demo_leads_created;
DROP TABLE IF EXISTS demo_leads;
