-- Migration: Create outreach tracking tables
-- Tracks multi-channel outreach sequences (email, SMS, call)

-- Outreach sequences table (sequence definitions)
CREATE TABLE IF NOT EXISTS outreach_sequences (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  description TEXT,
  is_active BOOLEAN DEFAULT true,
  total_steps INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Outreach events table (individual touchpoints)
CREATE TABLE IF NOT EXISTS outreach_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  sequence_id UUID REFERENCES outreach_sequences(id) ON DELETE SET NULL,

  -- Event details
  channel TEXT NOT NULL,  -- email, sms, call
  step INTEGER NOT NULL,  -- 1, 2, 3, 4 within channel
  sequence_day INTEGER,   -- Day in overall sequence (1-15)

  -- Status tracking
  status TEXT NOT NULL DEFAULT 'scheduled',  -- scheduled, sent, opened, replied, completed, failed
  scheduled_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,
  clicked_at TIMESTAMPTZ,
  replied_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  failed_at TIMESTAMPTZ,
  failure_reason TEXT,

  -- Template reference
  template_id TEXT,
  template_version TEXT,
  personalization_data JSONB,

  -- External references
  hubspot_engagement_id TEXT,
  hubspot_sequence_id TEXT,
  salesmsg_message_id TEXT,

  -- Metadata
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Lead sequence enrollment (tracks which leads are in which sequences)
CREATE TABLE IF NOT EXISTS lead_sequence_enrollments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  sequence_id UUID NOT NULL REFERENCES outreach_sequences(id) ON DELETE CASCADE,

  -- Enrollment details
  enrolled_at TIMESTAMPTZ DEFAULT NOW(),
  current_step INTEGER DEFAULT 1,
  current_day INTEGER DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'active',  -- active, paused, completed, failed, cancelled

  -- Completion tracking
  completed_at TIMESTAMPTZ,
  cancelled_at TIMESTAMPTZ,
  cancel_reason TEXT,

  -- Next action
  next_event_at TIMESTAMPTZ,
  next_event_channel TEXT,
  next_event_step INTEGER,

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  -- Ensure one active enrollment per lead per sequence
  UNIQUE (lead_id, sequence_id)
);

-- Create indexes for outreach_events
CREATE INDEX idx_outreach_events_lead ON outreach_events(lead_id);
CREATE INDEX idx_outreach_events_sequence ON outreach_events(sequence_id);
CREATE INDEX idx_outreach_events_status ON outreach_events(status);
CREATE INDEX idx_outreach_events_channel ON outreach_events(channel);
CREATE INDEX idx_outreach_events_scheduled ON outreach_events(scheduled_at);
CREATE INDEX idx_outreach_events_sent ON outreach_events(sent_at);

-- Composite index for finding next actions
CREATE INDEX idx_outreach_events_status_scheduled ON outreach_events(status, scheduled_at)
  WHERE status = 'scheduled';

-- Create indexes for lead_sequence_enrollments
CREATE INDEX idx_enrollments_lead ON lead_sequence_enrollments(lead_id);
CREATE INDEX idx_enrollments_sequence ON lead_sequence_enrollments(sequence_id);
CREATE INDEX idx_enrollments_status ON lead_sequence_enrollments(status);
CREATE INDEX idx_enrollments_next_event ON lead_sequence_enrollments(next_event_at)
  WHERE status = 'active';

-- Triggers for updated_at
CREATE TRIGGER update_outreach_sequences_updated_at
    BEFORE UPDATE ON outreach_sequences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_outreach_events_updated_at
    BEFORE UPDATE ON outreach_events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_enrollments_updated_at
    BEFORE UPDATE ON lead_sequence_enrollments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE outreach_sequences IS 'Outreach sequence definitions (e.g., BDR Multi-Touch 15-day)';
COMMENT ON TABLE outreach_events IS 'Individual outreach touchpoints (emails, SMS, calls)';
COMMENT ON TABLE lead_sequence_enrollments IS 'Tracks which leads are enrolled in which sequences';
COMMENT ON COLUMN outreach_events.channel IS 'Outreach channel: email, sms, call';
COMMENT ON COLUMN outreach_events.status IS 'Event status: scheduled, sent, opened, replied, completed, failed';
