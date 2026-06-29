-- Karta SDR Database Schema
-- Supabase PostgreSQL

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Calls table: stores complete call session data
CREATE TABLE IF NOT EXISTS calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_call_id VARCHAR(255),
    phone_number VARCHAR(50),
    provider VARCHAR(50) NOT NULL DEFAULT 'vapi',
    status VARCHAR(50) NOT NULL DEFAULT 'initiated',
    current_state VARCHAR(50) NOT NULL DEFAULT 'INTRO',
    duration_seconds FLOAT,
    transcript TEXT,
    summary TEXT,
    lead_data JSONB,
    scoring JSONB,
    metrics JSONB,
    drop_off_stage VARCHAR(50),
    qualified BOOLEAN NOT NULL DEFAULT FALSE,
    booked BOOLEAN NOT NULL DEFAULT FALSE,
    human_handoff BOOLEAN NOT NULL DEFAULT FALSE,
    cost_usd FLOAT,
    avg_latency_ms FLOAT,
    interruption_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

CREATE INDEX idx_calls_status ON calls(status);
CREATE INDEX idx_calls_created_at ON calls(created_at DESC);
CREATE INDEX idx_calls_qualified ON calls(qualified);
CREATE INDEX idx_calls_drop_off ON calls(drop_off_stage);

-- Leads table: qualified lead records
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    call_id UUID NOT NULL REFERENCES calls(id),
    name VARCHAR(255),
    company_name VARCHAR(255),
    industry VARCHAR(255),
    employee_count INTEGER,
    email VARCHAR(255),
    phone VARCHAR(50),
    lead_score INTEGER,
    lead_tier VARCHAR(50),
    crm_synced BOOLEAN NOT NULL DEFAULT FALSE,
    booking_event_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_leads_call_id ON leads(call_id);
CREATE INDEX idx_leads_tier ON leads(lead_tier);
CREATE INDEX idx_leads_score ON leads(lead_score DESC);

-- Analytics snapshots: periodic aggregated metrics
CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    total_calls INTEGER NOT NULL DEFAULT 0,
    qualified_calls INTEGER NOT NULL DEFAULT 0,
    booked_calls INTEGER NOT NULL DEFAULT 0,
    avg_duration_seconds FLOAT,
    avg_latency_ms FLOAT,
    completion_rate FLOAT,
    total_cost_usd FLOAT,
    drop_off_stages JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_analytics_period ON analytics_snapshots(period_start, period_end);

-- Conversation turns: optional detailed turn-level logging
CREATE TABLE IF NOT EXISTS conversation_turns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    call_id UUID NOT NULL REFERENCES calls(id),
    turn_index INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    state VARCHAR(50),
    latency_ms FLOAT,
    interrupted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_turns_call_id ON conversation_turns(call_id);

-- Row Level Security (Supabase)
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_snapshots ENABLE ROW LEVEL SECURITY;

-- Service role bypass policy
CREATE POLICY "Service role full access on calls"
    ON calls FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on leads"
    ON leads FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on analytics"
    ON analytics_snapshots FOR ALL
    USING (auth.role() = 'service_role');
