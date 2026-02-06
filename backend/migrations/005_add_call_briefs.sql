-- Migration 005: Call Briefs Storage + Outcome Linkage
-- Purpose: Persist call briefs and link them to outcomes for feedback loop
-- Depends on: 004_add_call_outcomes.sql
-- Run: psql $DATABASE_URL -f migrations/005_add_call_briefs.sql

-- 1. Create call_briefs table
CREATE TABLE IF NOT EXISTS call_briefs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    lead_id TEXT NOT NULL,
    brief_json JSONB NOT NULL,
    brief_quality TEXT NOT NULL DEFAULT 'medium',
    trigger TEXT,
    call_type TEXT NOT NULL DEFAULT 'warm',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Add call_brief_id to call_outcomes (optional FK)
ALTER TABLE call_outcomes
    ADD COLUMN IF NOT EXISTS call_brief_id UUID REFERENCES call_briefs(id);

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_call_briefs_lead_id ON call_briefs(lead_id);
CREATE INDEX IF NOT EXISTS idx_call_briefs_quality ON call_briefs(brief_quality);
CREATE INDEX IF NOT EXISTS idx_call_briefs_created_at ON call_briefs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_call_outcomes_brief_id ON call_outcomes(call_brief_id);
