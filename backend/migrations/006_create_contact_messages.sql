-- Migration: 006_create_contact_messages
-- Description: Create the contact_messages table for leads submitted from the
--              public landing page (POST /api/contact).
-- Requirements: landing page contact form (portfolio / sales hook)

CREATE TABLE IF NOT EXISTS contact_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    email VARCHAR(254) NOT NULL,
    company VARCHAR(120),
    message TEXT NOT NULL,
    source_lang VARCHAR(5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_contact_messages_created ON contact_messages(created_at);
