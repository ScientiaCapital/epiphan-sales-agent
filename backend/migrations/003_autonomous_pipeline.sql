-- Autonomous BDR Pipeline tables
-- Supports nightly prospect-to-outreach loop with human approval queue

-- Track each pipeline execution
CREATE TABLE IF NOT EXISTS autonomous_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    config JSONB NOT NULL DEFAULT '{}',
    summary JSONB DEFAULT '{}',
    error_log TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_autonomous_runs_status ON autonomous_runs(status);
CREATE INDEX IF NOT EXISTS idx_autonomous_runs_started ON autonomous_runs(started_at DESC);

-- Individual outreach items awaiting approval
CREATE TABLE IF NOT EXISTS outreach_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES autonomous_runs(id),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'sent', 'failed')),

    -- Lead data
    lead_email TEXT NOT NULL,
    lead_name TEXT,
    lead_title TEXT,
    lead_company TEXT,
    lead_industry TEXT,
    lead_phone TEXT,
    lead_source TEXT NOT NULL CHECK (lead_source IN ('apollo', 'hubspot', 'clay')),
    lead_data JSONB DEFAULT '{}',

    -- Agent results
    qualification_tier TEXT,
    qualification_score REAL DEFAULT 0,
    qualification_confidence REAL DEFAULT 0,
    persona_match TEXT,
    is_atl BOOLEAN DEFAULT false,

    -- Drafted outreach
    email_subject TEXT,
    email_body TEXT,
    email_pain_point TEXT,
    email_methodology TEXT DEFAULT 'challenger',
    call_brief JSONB DEFAULT '{}',

    -- Approval workflow
    rejection_reason TEXT,
    reviewer_notes TEXT,
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,

    -- Learning signals (populated post-send)
    email_opened BOOLEAN,
    email_replied BOOLEAN,
    meeting_booked BOOLEAN,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_outreach_queue_status ON outreach_queue(status);
CREATE INDEX IF NOT EXISTS idx_outreach_queue_run ON outreach_queue(run_id);
CREATE INDEX IF NOT EXISTS idx_outreach_queue_tier ON outreach_queue(qualification_tier);
CREATE INDEX IF NOT EXISTS idx_outreach_queue_email ON outreach_queue(lead_email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_outreach_queue_dedup ON outreach_queue(lead_email, run_id);

-- Aggregated learning data from approval history
CREATE TABLE IF NOT EXISTS approval_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type TEXT NOT NULL
        CHECK (pattern_type IN ('industry', 'title', 'company_size', 'persona', 'vertical', 'email_style')),
    pattern_key TEXT NOT NULL,
    approved_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,
    approval_rate REAL DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT now(),
    UNIQUE(pattern_type, pattern_key)
);

CREATE INDEX IF NOT EXISTS idx_approval_patterns_type ON approval_patterns(pattern_type);
