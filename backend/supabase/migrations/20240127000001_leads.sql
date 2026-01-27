-- Migration: Create leads table for synced HubSpot contacts
-- This table stores leads from HubSpot with local scoring and persona matching

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Leads table (synced from HubSpot)
CREATE TABLE IF NOT EXISTS leads (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  hubspot_id TEXT UNIQUE NOT NULL,
  email TEXT NOT NULL,
  first_name TEXT,
  last_name TEXT,
  company TEXT,
  title TEXT,
  phone TEXT,
  linkedin_url TEXT,
  city TEXT,
  state TEXT,
  country TEXT,
  industry TEXT,

  -- Scoring fields (computed locally)
  persona_match TEXT,  -- av_director, ld_director, etc.
  persona_confidence DECIMAL(3,2) DEFAULT 0.00,
  vertical TEXT,  -- higher_ed, corporate, etc.

  -- Score breakdown (0-25 each)
  persona_score INTEGER DEFAULT 0,
  vertical_score INTEGER DEFAULT 0,
  company_score INTEGER DEFAULT 0,
  engagement_score INTEGER DEFAULT 0,

  -- Total score (computed)
  total_score INTEGER GENERATED ALWAYS AS (
    persona_score + vertical_score + company_score + engagement_score
  ) STORED,

  -- Tier assignment based on total_score
  tier TEXT DEFAULT 'cold',  -- hot (85+), warm (70-84), nurture (50-69), cold (<50)

  -- HubSpot metadata
  hubspot_owner_id TEXT,
  lifecycle_stage TEXT,
  lead_status TEXT,
  last_activity_date TIMESTAMPTZ,
  contact_count INTEGER DEFAULT 0,
  last_contacted TIMESTAMPTZ,

  -- Sync tracking
  synced_at TIMESTAMPTZ DEFAULT NOW(),
  scored_at TIMESTAMPTZ,
  hubspot_created_at TIMESTAMPTZ,
  hubspot_updated_at TIMESTAMPTZ,

  -- Local timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX idx_leads_total_score ON leads(total_score DESC);
CREATE INDEX idx_leads_tier ON leads(tier);
CREATE INDEX idx_leads_persona ON leads(persona_match);
CREATE INDEX idx_leads_vertical ON leads(vertical);
CREATE INDEX idx_leads_email ON leads(email);
CREATE INDEX idx_leads_hubspot_id ON leads(hubspot_id);
CREATE INDEX idx_leads_synced_at ON leads(synced_at);
CREATE INDEX idx_leads_scored_at ON leads(scored_at);

-- Composite index for prioritized queries
CREATE INDEX idx_leads_tier_persona_score ON leads(tier, persona_match, total_score DESC);

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for auto-updating updated_at
CREATE TRIGGER update_leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to auto-assign tier based on total_score
CREATE OR REPLACE FUNCTION assign_lead_tier()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate tier based on total_score
    IF NEW.total_score >= 85 THEN
        NEW.tier = 'hot';
    ELSIF NEW.total_score >= 70 THEN
        NEW.tier = 'warm';
    ELSIF NEW.total_score >= 50 THEN
        NEW.tier = 'nurture';
    ELSE
        NEW.tier = 'cold';
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for auto-assigning tier
CREATE TRIGGER assign_lead_tier_trigger
    BEFORE INSERT OR UPDATE ON leads
    FOR EACH ROW
    EXECUTE FUNCTION assign_lead_tier();

-- Add comments for documentation
COMMENT ON TABLE leads IS 'Leads synced from HubSpot with local scoring and persona matching';
COMMENT ON COLUMN leads.persona_match IS 'Matched persona type: av_director, ld_director, technical_director, simulation_director, court_administrator, corp_comms_director, ehs_manager, law_firm_it';
COMMENT ON COLUMN leads.tier IS 'Lead tier: hot (85+), warm (70-84), nurture (50-69), cold (<50)';
COMMENT ON COLUMN leads.total_score IS 'Computed total score (0-100) from four 25-point dimensions';
