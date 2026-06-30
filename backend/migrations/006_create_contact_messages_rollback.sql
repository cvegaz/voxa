-- Rollback: 006_create_contact_messages
-- Description: Drop the contact_messages table and its index.

DROP INDEX IF EXISTS idx_contact_messages_created;
DROP TABLE IF EXISTS contact_messages;
