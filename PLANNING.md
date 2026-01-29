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
│  │         webhooks, personas, competitors                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────────┐  │
│  │  LangGraph    │  │  Enrichment   │  │   Integrations     │  │
│  │  5 Agents     │  │  Apollo/      │  │   HubSpot/Clari    │  │
│  │               │  │  Clearbit     │  │                    │  │
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

### Lead Management
- `POST /api/leads/ingest` - Harvester batch ingest
- `POST /api/leads/sync` - HubSpot sync
- `POST /api/leads/score` - Score unscored leads
- `GET /api/leads/prioritized` - Get by tier/persona
- `GET /api/leads/{id}` - Single lead

### Monitoring & Webhooks
- `GET /api/monitoring/credits` - Credit usage
- `GET /api/monitoring/rate-limits` - API health
- `GET /api/monitoring/batches` - Batch list
- `GET /api/monitoring/batches/{id}` - Batch status
- `POST /api/webhooks/apollo/phone-reveal` - Apollo phones
- `POST /api/webhooks/harvester/lead-push` - Harvester sync
- `GET /api/webhooks/phones/pending` - Pending approvals
- `POST /api/webhooks/phones/approve` - Approve sync

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
