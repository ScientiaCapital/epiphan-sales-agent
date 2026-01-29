-- Migration: Add table for Apollo webhook phone data
-- PHONES ARE GOLD! This table stores async-delivered phone numbers from Apollo.
--
-- Apollo delivers mobile/direct phones asynchronously (2-10 minutes after request).
-- This table captures those phones for later sync to HubSpot and lead records.
--
-- Run: psql -d epiphan_sales_agent -f migrations/003_add_webhook_phone_data.sql

-- Store phone numbers received via Apollo webhook
CREATE TABLE IF NOT EXISTS apollo_phone_webhooks (
    id SERIAL PRIMARY KEY,

    -- Lead identifiers
    email VARCHAR(255) NOT NULL,
    person_id VARCHAR(255),

    -- PHONE NUMBERS - THE GOLD!
    -- Priority: direct > mobile > work
    direct_phone VARCHAR(50),    -- Best: direct dial to decision-maker
    mobile_phone VARCHAR(50),    -- Good: personal, high answer rate
    work_phone VARCHAR(50),      -- OK: may go to voicemail/assistant

    -- Raw data for debugging and audit
    raw_phones JSONB,

    -- Tracking timestamps
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- HubSpot sync status
    synced_to_hubspot BOOLEAN DEFAULT FALSE,
    synced_at TIMESTAMP,

    -- Optional link to lead record if exists
    lead_id INTEGER
);

-- Index for quick lookups by email (most common query)
CREATE INDEX IF NOT EXISTS idx_apollo_webhooks_email
    ON apollo_phone_webhooks(email);

-- Index for finding unsynced records (for batch HubSpot sync job)
CREATE INDEX IF NOT EXISTS idx_apollo_webhooks_unsynced
    ON apollo_phone_webhooks(synced_to_hubspot)
    WHERE synced_to_hubspot = FALSE;

-- Index for finding recent webhooks (monitoring/debugging)
CREATE INDEX IF NOT EXISTS idx_apollo_webhooks_received
    ON apollo_phone_webhooks(received_at DESC);

-- Comment on table
COMMENT ON TABLE apollo_phone_webhooks IS
    'PHONES ARE GOLD! Stores async phone delivery from Apollo webhooks for BDR outreach.';

COMMENT ON COLUMN apollo_phone_webhooks.direct_phone IS
    'Direct dial - BEST phone type. Reaches decision-maker directly.';

COMMENT ON COLUMN apollo_phone_webhooks.mobile_phone IS
    'Mobile phone - GOOD. Personal number with high answer rate.';

COMMENT ON COLUMN apollo_phone_webhooks.work_phone IS
    'Work line - OK. May go to voicemail or assistant.';
