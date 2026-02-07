# Architecture & Planning Notes

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (TBD)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Routes: agents, batch, leads, monitoring, scripts,       │  │
│  │   webhooks, personas, competitors, call-brief, outcomes, │  │
│  │   call-session (WS + REST)                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────────┐  │
│  │  LangGraph    │  │  Enrichment   │  │   Integrations     │  │
│  │  5 Agents +   │  │  Apollo       │  │   HubSpot/Clari    │  │
│  │  Call Brief   │  │               │  │                    │  │
│  │  Assembler    │  │               │  │                    │  │
│  └───────────────┘  └───────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Supabase                                  │
│              (PostgreSQL + Auth + Phone Storage)                 │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints (Implemented)

### LangGraph Agents
- `POST /api/agents/research` - Lead research
- `POST /api/agents/scripts` - Script selection
- `POST /api/agents/competitors` - Competitor intel
- `POST /api/agents/emails` - Email generation
- `POST /api/agents/emails/with-approval` - Email with HITL
- `POST /api/agents/qualify` - Lead qualification
- `POST /api/agents/qualify/stream` - Streaming qualification
- `POST /api/agents/call-brief` - One-page call prep brief (composes research + qualify + script)

### Lead Management
- `POST /api/leads/ingest` - Harvester batch ingest
- `POST /api/leads/sync` - HubSpot sync
- `POST /api/leads/score` - Score unscored leads
- `GET /api/leads/prioritized` - Get by tier/persona
- `GET /api/leads/ready-to-dial` - Daily call list with tier/phone filtering
- `GET /api/leads/{id}` - Single lead

### Authentication
- `POST /api/auth/token` - Issue JWT (API key → bearer token exchange)

### Call Outcome Tracking
- `POST /api/call-outcomes` - Log a call outcome
- `POST /api/call-outcomes/batch` - Batch log (end-of-day catch-up)
- `GET /api/call-outcomes/stats` - Daily stats (?date=YYYY-MM-DD)
- `GET /api/call-outcomes/stats/range` - Date range stats (?start=&end=)
- `GET /api/call-outcomes/follow-ups` - Pending follow-ups (?date=&include_overdue=true)
- `GET /api/call-outcomes/brief-effectiveness` - Brief quality → conversion analytics (enhanced)
- `GET /api/call-outcomes/brief-effectiveness/persona/{persona_id}` - Per-persona deep dive
- `GET /api/call-outcomes/brief-effectiveness/scripts` - Script matrix (persona x trigger)
- `GET /api/call-outcomes/lead/{lead_id}` - Lead call history
- `POST /api/call-outcomes/{outcome_id}/hubspot-sync` - Manual HubSpot sync

### Monitoring & Webhooks
- `GET /api/monitoring/credits` - Credit usage
- `GET /api/monitoring/rate-limits` - API health
- `GET /api/monitoring/batches` - Batch list
- `GET /api/monitoring/batches/{id}` - Batch status
- `POST /api/webhooks/apollo/phone-reveal` - Apollo phones
- `POST /api/webhooks/harvester/lead-push` - Harvester sync
- `POST /api/webhooks/clay/enrichment` - Clay fallback enrichment (75+ providers)
- `GET /api/webhooks/phones/pending` - Pending approvals
- `POST /api/webhooks/phones/approve` - Approve sync

### Voice AI Call Session
- `GET /ws/call-session?token=xxx` - WebSocket for live call support
- `POST /api/call-session/start` - REST: Start session + get call brief
- `POST /api/call-session/{id}/competitor` - REST: Competitor query during call
- `POST /api/call-session/{id}/objection` - REST: Objection response
- `POST /api/call-session/{id}/end` - REST: End call + log outcome
- `GET /api/call-session/{id}` - REST: Get session state

### Scripts & Reference
- `GET /api/scripts/warm/{trigger}` - Warm scripts
- `GET /api/personas` - Persona list
- `GET /api/competitors/{name}` - Battlecards

## Design Decisions

### 1. Tiered Enrichment Strategy
- Phase 1 (1 credit): Basic enrichment for all leads
- Phase 2 (8 credits): Phone reveal ONLY for ATL decision-makers
- ~67% credit savings on typical batches

### 2. Async Phone Delivery
- Apollo phones delivered via webhook (2-10 min delay)
- Local storage first, HubSpot sync requires approval
- HMAC-SHA256 verification for security

### 3. Background Processing
- Harvester leads processed asynchronously
- In-memory batch tracking (MVP)
- Integration with monitoring endpoints

### 4. Call Brief Assembler (NOT a LangGraph agent)
- Composition layer using raw `asyncio.gather()` for parallel agent execution
- Avoids MasterOrchestrator overhead (no review gates, checkpointing, HubSpot sync)
- Graceful degradation: each agent wrapped in `_safe_*()` try/except returning None
- Enriches with playbook data: objections, discovery questions, competitor battlecards, reference stories
- Phone extraction from 3 sources: research result, lead record, webhook table
- Brief quality scoring: HIGH (8+), MEDIUM (4-7), LOW (<4) based on data completeness

### 5. Call Outcome Tracking (Pure Data Layer)
- Separate `call_outcomes` table (NOT extending `outreach_events` — different concern)
- VARCHAR for disposition/result (not PG enums) — matches existing project pattern
- Default follow-up rules applied automatically when Tim doesn't specify one
- Lead status auto-updated on meeting_booked, qualified_out, dead
- Business day calculation for follow-up dates (skips weekends)
- No AI/LLM calls — pure data tracking + auto-scheduling

### 6. Brief Effectiveness Deep Analytics
- `ConversionFunnel` as reusable building block (persona, tier, trigger, overall)
- Rates as percentages (0-100), not ratios (0-1)
- Connected-only duration (voicemails/no-answer excluded from avg)
- Top items with counts: `[{"budget": 5}, {"timing": 3}]`
- Sample size warnings (< 5 outcomes) to prevent over-indexing
- Python-side JSONB persona filtering (acceptable at ~20 calls/day scale)
- Backward compatible with original brief-effectiveness response shape

### 7. Clay.com Fallback Enrichment
- Webhook-based (no REST API): POST lead → Clay enriches → Clay POSTs back
- Feature-flagged: `CLAY_ENABLED=false` by default
- Phone priority: Apollo (primary) > Harvester (secondary) > Clay (tertiary fallback)
- HMAC-SHA256 verification, same pattern as Apollo/Harvester
- Supabase upsert by lead_id for idempotent webhook handling

### 8. Voice AI Call Session (WebSocket + REST)
- WebSocket for real-time bidirectional communication during live calls
- REST fallback endpoints using same `CallSessionManager` — zero logic duplication
- In-memory sessions (Tim makes ~20 calls/day, 1 active at a time)
- Session state is ephemeral; briefs + outcomes persisted to Supabase via existing code
- JWT auth via query parameter for WebSocket (`?token=xxx`)
- Reuses existing agents: CallBriefAssembler, CompetitorIntelAgent, CallOutcomeService

### 9. JWT API Authentication
- Bearer token required on all non-public endpoints
- 15-minute token expiry (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Constant-time API key comparison (timing-safe)
- Public routes: /health, /, /docs, /api/auth/token, webhooks (HMAC auth)
