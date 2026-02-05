-- Migration: Add call_outcomes table for BDR call tracking
-- Closes the feedback loop: log what happened, update lead, schedule follow-ups.
--
-- Tim makes ~20 calls/day. This table captures every dial attempt and outcome
-- so we can track connection rates, phone type performance, and meeting conversion.
--
-- Run: psql -d epiphan_sales_agent -f migrations/004_add_call_outcomes.sql

CREATE TABLE IF NOT EXISTS call_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to the lead that was called
    lead_id UUID NOT NULL,

    -- When and how long
    called_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_seconds INTEGER DEFAULT 0,

    -- PHONE DETAILS - track which number and type worked
    phone_number_dialed VARCHAR(50) NOT NULL,
    phone_type VARCHAR(20),  -- direct, mobile, work, company

    -- What happened on the call
    disposition VARCHAR(30) NOT NULL,  -- connected, voicemail, no_answer, busy, wrong_number, gatekeeper, callback_requested, not_interested, no_longer_there
    result VARCHAR(30) NOT NULL,       -- meeting_booked, follow_up_needed, qualified_out, nurture, dead, no_contact

    -- Call intelligence (captured by BDR)
    notes TEXT,
    objections JSONB,         -- ["budget", "timing", "using_competitor"]
    buying_signals JSONB,     -- ["asked_about_pricing", "mentioned_deadline"]
    competitor_mentioned VARCHAR(100),

    -- Follow-up scheduling
    follow_up_date DATE,
    follow_up_type VARCHAR(50),   -- callback, send_email, schedule_demo, send_info, linkedin_connect
    follow_up_notes TEXT,

    -- HubSpot sync tracking
    hubspot_engagement_id TEXT,
    synced_to_hubspot BOOLEAN DEFAULT FALSE,
    synced_at TIMESTAMPTZ,

    -- Optional link to outreach sequence
    outreach_event_id UUID,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Primary query: all calls for a lead, most recent first
CREATE INDEX IF NOT EXISTS idx_call_outcomes_lead_called
    ON call_outcomes(lead_id, called_at DESC);

-- Daily stats queries
CREATE INDEX IF NOT EXISTS idx_call_outcomes_called_at
    ON call_outcomes(called_at);

-- Filter by result for pipeline reporting
CREATE INDEX IF NOT EXISTS idx_call_outcomes_result
    ON call_outcomes(result);

-- Find unsynced outcomes for batch HubSpot push
CREATE INDEX IF NOT EXISTS idx_call_outcomes_unsynced
    ON call_outcomes(synced_to_hubspot)
    WHERE synced_to_hubspot = FALSE;

-- Find pending follow-ups (what needs doing today?)
CREATE INDEX IF NOT EXISTS idx_call_outcomes_follow_up
    ON call_outcomes(follow_up_date)
    WHERE follow_up_date IS NOT NULL;

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_call_outcomes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER call_outcomes_updated_at
    BEFORE UPDATE ON call_outcomes
    FOR EACH ROW
    EXECUTE FUNCTION update_call_outcomes_updated_at();

COMMENT ON TABLE call_outcomes IS
    'BDR call outcome tracking. Logs every dial attempt to close the feedback loop on lead intelligence.';
