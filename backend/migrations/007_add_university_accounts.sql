-- Migration 007: University Account Scoring
-- Adds university_accounts table for institution-level scoring and target account management.
--
-- University accounts are scored on 5 dimensions:
-- 1. Carnegie Classification (25%) - R1/R2 research intensity
-- 2. Enrollment Size (20%) - student count as AV room proxy
-- 3. Technology Signals (20%) - existing AV/LMS/video platforms
-- 4. Engagement Level (15%) - contacts, decision-makers, deals
-- 5. Strategic Fit (15%) - public/private, athletics
--
-- Account Tiers: A (75+), B (50-74), C (30-49), D (<30)

CREATE TABLE IF NOT EXISTS university_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Institution identity
    name VARCHAR(500) NOT NULL,
    domain VARCHAR(255),              -- Primary .edu domain
    ipeds_unitid VARCHAR(20),         -- Federal IPEDS ID (unique per institution)
    hubspot_company_id VARCHAR(50),   -- HubSpot company record ID

    -- Carnegie Classification
    carnegie_classification VARCHAR(30),  -- r1, r2, d_pu, m1, m2, m3, baccalaureate, etc.
    institution_type VARCHAR(30),         -- public, private_nonprofit, private_for_profit

    -- Size
    enrollment INTEGER,
    faculty_count INTEGER,
    employee_count INTEGER,

    -- Location
    city VARCHAR(100),
    state VARCHAR(2),
    zip_code VARCHAR(10),

    -- Technology (key for scoring)
    lms_platform VARCHAR(100),        -- Canvas, Blackboard, Moodle
    video_platform VARCHAR(100),      -- Panopto, Kaltura, YuJa (competitor = rip & replace)
    av_system VARCHAR(100),           -- Crestron, Extron, QSC
    tech_stack JSONB DEFAULT '[]',    -- Array of known technologies

    -- Athletics (streaming needs proxy)
    athletic_division VARCHAR(20),    -- ncaa_d1, ncaa_d2, ncaa_d3, naia, njcaa, none

    -- Relationship status
    is_existing_customer BOOLEAN DEFAULT FALSE,
    has_active_opportunity BOOLEAN DEFAULT FALSE,
    contact_count INTEGER DEFAULT 0,
    decision_maker_count INTEGER DEFAULT 0,

    -- Scoring
    total_score NUMERIC(5,2) DEFAULT 0,
    account_tier VARCHAR(1) DEFAULT 'D',  -- A, B, C, D
    score_breakdown JSONB,                -- Full AccountScoreBreakdown

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    scored_at TIMESTAMPTZ,

    -- Unique constraints
    CONSTRAINT uq_university_accounts_name_state UNIQUE (name, state),
    CONSTRAINT uq_university_accounts_ipeds UNIQUE (ipeds_unitid)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_university_accounts_tier
    ON university_accounts(account_tier);

CREATE INDEX IF NOT EXISTS idx_university_accounts_score
    ON university_accounts(total_score DESC);

CREATE INDEX IF NOT EXISTS idx_university_accounts_state
    ON university_accounts(state);

CREATE INDEX IF NOT EXISTS idx_university_accounts_carnegie
    ON university_accounts(carnegie_classification);

CREATE INDEX IF NOT EXISTS idx_university_accounts_tier_score
    ON university_accounts(account_tier, total_score DESC);

-- Gap analysis: A/B accounts with no contacts (need research)
CREATE INDEX IF NOT EXISTS idx_university_accounts_no_contacts
    ON university_accounts(account_tier, contact_count)
    WHERE account_tier IN ('A', 'B') AND contact_count = 0;

-- HubSpot linkage
CREATE INDEX IF NOT EXISTS idx_university_accounts_hubspot
    ON university_accounts(hubspot_company_id)
    WHERE hubspot_company_id IS NOT NULL;

-- Domain lookup (for matching .edu emails to accounts)
CREATE INDEX IF NOT EXISTS idx_university_accounts_domain
    ON university_accounts(domain)
    WHERE domain IS NOT NULL;
