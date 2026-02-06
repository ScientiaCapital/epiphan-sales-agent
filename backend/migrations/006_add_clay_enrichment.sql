-- Migration 006: Add Clay.com enrichment results table
-- Clay is a FALLBACK enrichment source (75+ provider waterfall)
-- that fills gaps when Apollo can't find phones/emails.
-- PHONES ARE GOLD!

CREATE TABLE IF NOT EXISTS clay_enrichment_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id TEXT NOT NULL,
    -- Phone data (PHONES ARE GOLD)
    phones JSONB DEFAULT '[]',          -- [{number, type, provider}]
    -- Email data
    emails JSONB DEFAULT '[]',          -- [{email, type, provider}]
    -- Company firmographics
    company_name TEXT,
    industry TEXT,
    employee_count INTEGER,
    revenue_range TEXT,
    -- Tech stack + LinkedIn
    technologies JSONB DEFAULT '[]',
    linkedin_url TEXT,
    funding_info JSONB,
    -- Raw + sync tracking
    raw_payload JSONB NOT NULL,
    synced_to_hubspot BOOLEAN DEFAULT FALSE,
    synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_clay_lead_id ON clay_enrichment_results(lead_id);
CREATE INDEX idx_clay_unsynced ON clay_enrichment_results(synced_to_hubspot) WHERE NOT synced_to_hubspot;
