-- Initial schema for Epiphan Sales Agent
-- Based on SQLAlchemy models from backend/app/models/

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- ENUMS
-- ============================================================================

CREATE TYPE lead_status AS ENUM (
    'new', 'contacted', 'qualified', 'meeting_scheduled', 'proposal_sent',
    'negotiation', 'won', 'lost', 'nurture'
);

CREATE TYPE lead_tier AS ENUM ('platinum', 'gold', 'silver', 'bronze');

CREATE TYPE vertical_type AS ENUM (
    'higher_ed', 'corporate', 'live_events', 'government',
    'house_of_worship', 'healthcare', 'industrial', 'legal', 'ux_research'
);

CREATE TYPE persona_type AS ENUM (
    'av_director', 'ld_director', 'technical_director', 'simulation_director',
    'court_administrator', 'corp_comms_director', 'ehs_manager', 'law_firm_it',
    'cio', 'provost'
);

CREATE TYPE product_fit AS ENUM (
    'pearl_nano', 'pearl_nexus', 'pearl_mini', 'pearl_2', 'ec20_ptz'
);

CREATE TYPE audit_event_type AS ENUM (
    'created', 'updated', 'qualified', 'enriched', 'contacted',
    'meeting_booked', 'status_changed', 'tier_changed', 'synced_hubspot'
);

CREATE TYPE linkedin_post_status AS ENUM (
    'draft', 'scheduled', 'published', 'failed'
);

-- ============================================================================
-- LEADS TABLE
-- ============================================================================

CREATE TABLE leads (
    id BIGSERIAL PRIMARY KEY,

    -- HubSpot Reference
    hubspot_id VARCHAR(50) UNIQUE,
    hubspot_contact_vid VARCHAR(50),
    hubspot_company_id VARCHAR(50),
    hubspot_last_sync TIMESTAMPTZ,

    -- Basic Info
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    title VARCHAR(200),
    company_name VARCHAR(255),
    company_website VARCHAR(500),
    company_size VARCHAR(50),
    industry VARCHAR(100),

    -- Location
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    timezone VARCHAR(50),

    -- LinkedIn Info
    linkedin_url VARCHAR(500),
    linkedin_connected BOOLEAN DEFAULT FALSE,
    linkedin_last_activity TIMESTAMPTZ,

    -- Qualification
    status lead_status DEFAULT 'new',
    tier lead_tier,
    qualification_score FLOAT,
    qualification_reasoning TEXT,
    qualified_at TIMESTAMPTZ,
    qualified_by VARCHAR(100),

    -- Epiphan-Specific Scoring
    video_production_score FLOAT,
    broadcast_score FLOAT,
    education_score FLOAT,
    enterprise_score FLOAT,

    -- ICP Fit
    primary_vertical vertical_type,
    primary_persona persona_type,
    recommended_product product_fit,

    -- Engagement
    last_contacted TIMESTAMPTZ,
    last_responded TIMESTAMPTZ,
    touch_count INTEGER DEFAULT 0,

    -- Source
    lead_source VARCHAR(100),
    lead_source_detail VARCHAR(255),
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Lead indexes
CREATE INDEX idx_leads_hubspot_id ON leads(hubspot_id);
CREATE INDEX idx_leads_email ON leads(email);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_tier ON leads(tier);
CREATE INDEX idx_leads_vertical ON leads(primary_vertical);
CREATE INDEX idx_leads_qualification_score ON leads(qualification_score);
CREATE INDEX idx_leads_created_at ON leads(created_at);

-- ============================================================================
-- LEAD AUDIT LOG
-- ============================================================================

CREATE TABLE lead_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id BIGINT REFERENCES leads(id) ON DELETE CASCADE,

    event_type audit_event_type NOT NULL,
    event_data JSONB DEFAULT '{}',

    -- Decision tracking
    decision_reasoning TEXT,
    confidence FLOAT,

    -- Performance
    latency_ms INTEGER,
    cost_usd NUMERIC(10, 6),

    -- Agent tracking
    agent_type VARCHAR(50),
    session_id UUID,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_lead_id ON lead_audit_logs(lead_id);
CREATE INDEX idx_audit_event_type ON lead_audit_logs(event_type);
CREATE INDEX idx_audit_created_at ON lead_audit_logs(created_at);

-- ============================================================================
-- CONVERSATIONS (Clari Copilot)
-- ============================================================================

CREATE TABLE conversations (
    id BIGSERIAL PRIMARY KEY,

    -- Clari Reference
    clari_conversation_id VARCHAR(100) UNIQUE,
    clari_last_sync TIMESTAMPTZ,

    -- Lead Reference
    lead_id BIGINT REFERENCES leads(id) ON DELETE SET NULL,
    hubspot_contact_vid VARCHAR(50),

    -- Participants
    ae_name VARCHAR(100),
    ae_email VARCHAR(255),
    participant_name VARCHAR(200),
    participant_title VARCHAR(200),
    participant_company VARCHAR(255),

    -- Call Details
    call_date TIMESTAMPTZ,
    duration_seconds INTEGER,
    call_type VARCHAR(50), -- discovery, demo, follow_up, etc.

    -- Content
    transcript TEXT,
    summary TEXT,

    -- Analysis
    sentiment_score FLOAT,
    topics JSONB DEFAULT '[]',
    objections_raised JSONB DEFAULT '[]',
    buying_signals JSONB DEFAULT '[]',
    next_steps TEXT,

    -- Competitive Intel
    competitors_mentioned JSONB DEFAULT '[]',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_clari_id ON conversations(clari_conversation_id);
CREATE INDEX idx_conversations_lead_id ON conversations(lead_id);
CREATE INDEX idx_conversations_call_date ON conversations(call_date);
CREATE INDEX idx_conversations_ae ON conversations(ae_email);

-- ============================================================================
-- CONVERSATION INSIGHTS
-- ============================================================================

CREATE TABLE conversation_insights (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT REFERENCES conversations(id) ON DELETE CASCADE,

    insight_type VARCHAR(50), -- pain_point, objection, buying_signal, competitor, next_step
    insight_text TEXT NOT NULL,
    confidence FLOAT,

    -- Context
    timestamp_seconds INTEGER,
    speaker VARCHAR(100),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_insights_conversation ON conversation_insights(conversation_id);
CREATE INDEX idx_insights_type ON conversation_insights(insight_type);

-- ============================================================================
-- PATTERNS (ML Learning)
-- ============================================================================

CREATE TABLE lead_patterns (
    id BIGSERIAL PRIMARY KEY,

    pattern_name VARCHAR(200) NOT NULL,
    pattern_type VARCHAR(50), -- qualification, objection, buying_signal, conversion

    -- Pattern Definition
    conditions JSONB NOT NULL,
    outcome VARCHAR(100),
    confidence FLOAT,

    -- Statistics
    occurrences INTEGER DEFAULT 0,
    success_rate FLOAT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_patterns_type ON lead_patterns(pattern_type);

-- ============================================================================
-- WIN/LOSS PATTERNS
-- ============================================================================

CREATE TABLE win_loss_patterns (
    id BIGSERIAL PRIMARY KEY,

    outcome VARCHAR(10) NOT NULL CHECK (outcome IN ('win', 'loss')),

    -- Factors
    vertical vertical_type,
    persona persona_type,
    product product_fit,
    competitor VARCHAR(100),

    -- Pattern Data
    factors JSONB NOT NULL,
    frequency INTEGER DEFAULT 1,

    -- Analysis
    reasoning TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_win_loss_outcome ON win_loss_patterns(outcome);
CREATE INDEX idx_win_loss_vertical ON win_loss_patterns(vertical);

-- ============================================================================
-- ICP SCORES
-- ============================================================================

CREATE TABLE icp_scores (
    id BIGSERIAL PRIMARY KEY,
    lead_id BIGINT REFERENCES leads(id) ON DELETE CASCADE,
    hubspot_id VARCHAR(50),

    -- Vertical Classification
    primary_vertical vertical_type,
    secondary_verticals vertical_type[],
    vertical_confidence FLOAT,

    -- Persona Match
    primary_persona persona_type,
    persona_confidence FLOAT,

    -- Product Fit
    recommended_product product_fit,
    product_fit_reasoning TEXT,

    -- ICP Attribute Scores (0-100)
    company_size_score FLOAT,
    budget_authority_score FLOAT,
    tech_maturity_score FLOAT,
    buying_intent_score FLOAT,

    -- Higher Ed Specific
    student_count INTEGER,
    classroom_count INTEGER,
    has_lms BOOLEAN DEFAULT FALSE,
    lms_platform VARCHAR(50),

    -- Corporate Specific
    employee_count INTEGER,
    is_fortune_1000 BOOLEAN DEFAULT FALSE,
    has_hybrid_workforce BOOLEAN DEFAULT FALSE,
    uses_zoom_teams BOOLEAN DEFAULT FALSE,

    -- Healthcare Specific
    is_academic_medical_center BOOLEAN DEFAULT FALSE,
    has_simulation_center BOOLEAN DEFAULT FALSE,
    ssh_accredited BOOLEAN DEFAULT FALSE,

    -- Government Specific
    is_government BOOLEAN DEFAULT FALSE,
    population_served INTEGER,

    -- Overall
    overall_icp_score FLOAT,
    icp_reasoning TEXT,
    buying_signals TEXT[],

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_icp_lead_id ON icp_scores(lead_id);
CREATE INDEX idx_icp_vertical ON icp_scores(primary_vertical);
CREATE INDEX idx_icp_overall_score ON icp_scores(overall_icp_score);

-- ============================================================================
-- BUYING TRIGGERS
-- ============================================================================

CREATE TABLE buying_triggers (
    id BIGSERIAL PRIMARY KEY,
    lead_id BIGINT REFERENCES leads(id) ON DELETE CASCADE,

    trigger_type VARCHAR(50) NOT NULL,
    trigger_source VARCHAR(50),

    intent_level VARCHAR(20),
    confidence FLOAT,

    description TEXT,
    source_url VARCHAR(500),
    detected_date TIMESTAMPTZ DEFAULT NOW(),

    requires_action BOOLEAN DEFAULT TRUE,
    action_taken BOOLEAN DEFAULT FALSE,
    action_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_triggers_lead_id ON buying_triggers(lead_id);
CREATE INDEX idx_triggers_type ON buying_triggers(trigger_type);
CREATE INDEX idx_triggers_intent ON buying_triggers(intent_level);

-- ============================================================================
-- COMPETITOR INTEL
-- ============================================================================

CREATE TABLE competitor_intel (
    id BIGSERIAL PRIMARY KEY,
    lead_id BIGINT REFERENCES leads(id) ON DELETE SET NULL,
    conversation_id BIGINT REFERENCES conversations(id) ON DELETE SET NULL,

    competitor_name VARCHAR(100) NOT NULL,
    context_type VARCHAR(30), -- incumbent, evaluating, mentioned, replaced

    notes TEXT,
    win_message TEXT,

    displaced_competitor BOOLEAN DEFAULT FALSE,
    lost_to_competitor BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_competitor_name ON competitor_intel(competitor_name);
CREATE INDEX idx_competitor_lead ON competitor_intel(lead_id);

-- ============================================================================
-- LINKEDIN POSTS
-- ============================================================================

CREATE TABLE linkedin_posts (
    id BIGSERIAL PRIMARY KEY,

    content TEXT NOT NULL,
    post_type VARCHAR(50), -- thought_leadership, case_study, engagement, company_update

    vertical vertical_type,
    persona persona_type,

    status linkedin_post_status DEFAULT 'draft',
    scheduled_for TIMESTAMPTZ,
    published_at TIMESTAMPTZ,

    -- Performance
    impressions INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    engagement_rate FLOAT,

    linkedin_post_id VARCHAR(100),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_linkedin_status ON linkedin_posts(status);
CREATE INDEX idx_linkedin_scheduled ON linkedin_posts(scheduled_for);

-- ============================================================================
-- LINKEDIN CADENCES
-- ============================================================================

CREATE TABLE linkedin_cadences (
    id BIGSERIAL PRIMARY KEY,

    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,

    posting_days INTEGER[] DEFAULT '{1, 3}', -- Tuesday, Thursday (0=Sunday)
    posting_times VARCHAR[] DEFAULT '{"08:00", "12:00"}',
    timezone VARCHAR(50) DEFAULT 'America/New_York',

    content_mix JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- LINKEDIN ENGAGEMENTS
-- ============================================================================

CREATE TABLE linkedin_engagements (
    id BIGSERIAL PRIMARY KEY,
    lead_id BIGINT REFERENCES leads(id) ON DELETE SET NULL,

    engagement_type VARCHAR(50), -- connection_request, message, comment, like
    content TEXT,

    status VARCHAR(30) DEFAULT 'pending',
    sent_at TIMESTAMPTZ,
    response_received BOOLEAN DEFAULT FALSE,
    response_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_engagement_lead ON linkedin_engagements(lead_id);
CREATE INDEX idx_engagement_type ON linkedin_engagements(engagement_type);

-- ============================================================================
-- LINKEDIN TEMPLATES
-- ============================================================================

CREATE TABLE linkedin_templates (
    id BIGSERIAL PRIMARY KEY,

    name VARCHAR(100) NOT NULL,
    template_type VARCHAR(50), -- connection_request, message, inmail

    vertical vertical_type,
    persona persona_type,
    trigger VARCHAR(100),

    content TEXT NOT NULL,

    -- Performance
    times_used INTEGER DEFAULT 0,
    response_rate FLOAT,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_template_type ON linkedin_templates(template_type);

-- ============================================================================
-- SEED DATA TABLES (for playbook data)
-- ============================================================================

CREATE TABLE seed_personas (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    title_variations TEXT[],
    reports_to VARCHAR(255),
    team_size VARCHAR(50),
    budget_authority VARCHAR(100),
    verticals vertical_type[],
    day_to_day TEXT[],
    kpis TEXT[],
    pain_points JSONB,
    hot_buttons TEXT[],
    discovery_questions TEXT[],
    objections JSONB,
    buying_signals JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE seed_competitors (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    company VARCHAR(100),
    price_range VARCHAR(100),
    positioning TEXT,
    market_context TEXT,
    status VARCHAR(20),
    target_verticals vertical_type[],
    when_to_compete TEXT[],
    when_to_walk_away TEXT[],
    key_differentiators JSONB,
    claims JSONB,
    proof_points TEXT[],
    talk_track JSONB,
    call_mentions INTEGER,
    rank INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE seed_stories (
    id VARCHAR(50) PRIMARY KEY,
    customer VARCHAR(200) NOT NULL,
    stats VARCHAR(255),
    quote TEXT,
    quote_person VARCHAR(100),
    quote_title VARCHAR(100),
    vertical vertical_type,
    product VARCHAR(50),
    challenge TEXT,
    solution TEXT,
    results TEXT[],
    talking_points TEXT[],
    case_study_url VARCHAR(500),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE icp_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE buying_triggers ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitor_intel ENABLE ROW LEVEL SECURITY;
ALTER TABLE linkedin_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE linkedin_engagements ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to access all data (adjust for multi-tenant later)
CREATE POLICY "Allow authenticated access" ON leads FOR ALL USING (true);
CREATE POLICY "Allow authenticated access" ON lead_audit_logs FOR ALL USING (true);
CREATE POLICY "Allow authenticated access" ON conversations FOR ALL USING (true);
CREATE POLICY "Allow authenticated access" ON conversation_insights FOR ALL USING (true);
CREATE POLICY "Allow authenticated access" ON icp_scores FOR ALL USING (true);
CREATE POLICY "Allow authenticated access" ON buying_triggers FOR ALL USING (true);
CREATE POLICY "Allow authenticated access" ON competitor_intel FOR ALL USING (true);
CREATE POLICY "Allow authenticated access" ON linkedin_posts FOR ALL USING (true);
CREATE POLICY "Allow authenticated access" ON linkedin_engagements FOR ALL USING (true);

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables with updated_at
CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_icp_scores_updated_at BEFORE UPDATE ON icp_scores
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_competitor_intel_updated_at BEFORE UPDATE ON competitor_intel
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_linkedin_posts_updated_at BEFORE UPDATE ON linkedin_posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
