# Epiphan Sales Agent - Claude Code Project Memory

## Core Business Principle: Phone Numbers Are GOLD

**ALWAYS prioritize phone enrichment in every lead processing workflow.**

This is how Tim feeds his family, hits his goals, and earns bonuses:
- More phones → More dials → More conversations → More deals → Food on the table

When building lead processing features:
1. ALWAYS enrich phone numbers, even if other enrichment is disabled
2. Return ALL phone types: direct, mobile, work, company
3. Track phone enrichment success rates in metrics
4. Flag leads without phones for manual research

Phone priority order (best to worst):
1. **Direct dial** (`work_direct`) - Best: reaches decision-maker directly
2. **Mobile** (`mobile`) - Good: personal, high answer rate
3. **Work line** (`work`) - OK: may go to voicemail/assistant
4. **Company switchboard** (`work_hq`) - Fallback: requires asking for person

---

## Project Overview
AI-powered sales assistant for Epiphan Video, providing BDR warm call scripts, persona-specific messaging, and CRM integration.

## Tech Stack
- **Backend**: Python 3.10+, FastAPI, Pydantic
- **Database**: Supabase (PostgreSQL)
- **Package Manager**: uv
- **Testing**: pytest
- **Linting**: ruff, mypy

## Key Commands
```bash
# Run tests
cd backend && uv run pytest tests/ -v

# Lint check
cd backend && uv run ruff check .

# Auto-fix lint issues
cd backend && uv run ruff check . --fix

# Type checking
cd backend && uv run mypy app/

# Start server
cd backend && uv run uvicorn app.main:app --reload --port 8001
```

## Project Structure
```
backend/
├── app/
│   ├── main.py              # FastAPI app entry
│   ├── middleware/
│   │   └── auth.py          # JWT authentication (require_auth dependency)
│   ├── api/routes/
│   │   ├── auth.py          # Token issuance endpoint
│   │   ├── agents.py        # LangGraph agent endpoints
│   │   ├── batch.py         # Batch processing endpoint
│   │   ├── call_outcomes.py  # BDR call outcome tracking
│   │   ├── call_session.py  # Voice AI call session (WebSocket + REST)
│   │   ├── monitoring.py    # Observability (credits, rate-limits, batches)
│   │   ├── scripts.py       # Script endpoints
│   │   ├── leads.py         # Lead scoring endpoints
│   │   └── webhooks.py      # Apollo & Harvester webhooks
│   ├── data/
│   │   ├── schemas.py       # Pydantic models
│   │   ├── call_outcome_schemas.py  # Call outcome Pydantic models
│   │   ├── call_session_schemas.py  # Voice AI session Pydantic models
│   │   ├── scripts.py       # Script lookup functions
│   │   ├── competitors.py   # Competitor battlecards
│   │   └── persona_warm_scripts.py  # Persona-specific scripts
│   └── services/
│       ├── enrichment/      # Data enrichment clients
│       │   ├── apollo.py    # Apollo.io API (primary enrichment)
│       │   ├── clay.py      # Clay.com fallback (75+ provider waterfall)
│       │   ├── audit.py     # Enrichment audit logging & HubSpot mapping
│       │   ├── pipeline.py  # Background processing pipeline
│       │   └── scraper.py   # Web scraping
│       ├── call_outcomes/    # BDR call outcome tracking service
│       ├── call_session/     # Voice AI call session management
│       ├── scoring/         # Lead scoring services
│       │   └── atl_detector.py  # ATL decision-maker detection (8 personas)
│       ├── langgraph/       # AI Agents
│       │   ├── agents/      # LangGraph agents
│       │   ├── tools/       # Agent tools
│       │   ├── memory/      # Memory management (trimmer, semantic store)
│       │   ├── middleware.py # Middleware layer (PII, rate limit, model select)
│       │   ├── tracing.py   # LangSmith observability
│       │   └── states.py    # State schemas
│       ├── llm/             # LLM clients
│       │   └── clients.py   # Multi-model router
│       └── integrations/
│           └── hubspot/     # HubSpot CRM client
├── tests/
│   ├── unit/                # Unit tests (1206+)
│   └── integration/         # Integration tests
└── pyproject.toml
```

## Key Personas (8 total)
1. AV Director
2. L&D Director  
3. Technical Director
4. Simulation Director
5. Court Administrator
6. Corporate Communications Director
7. EHS Manager
8. Law Firm IT

## Trigger Types
- content_download
- demo_request
- pricing_request
- trial_signup

## LangGraph Agents
Five AI agents + Call Brief Assembler powered by LangGraph + Claude/Cerebras:

1. **Lead Research Agent** - Enriches leads via Apollo, web scraping
2. **Script Selection Agent** - Selects and personalizes call scripts
3. **Competitor Intelligence Agent** - Provides battlecard responses
4. **Email Personalization Agent** - Generates personalized outreach emails
5. **Qualification Agent** - Scores leads against 5-dimension weighted ICP criteria
6. **Call Brief Assembler** - Composes research + qualify + script agents in parallel into one-page call prep brief

### ICP Qualification Scoring
| Dimension | Weight | Scoring |
|-----------|--------|---------|
| Company Size | 25% | Enterprise (10), Mid-market (8), SMB (4), Too small (0) |
| Industry Vertical | 20% | Higher Ed (10), Healthcare (9), Corporate (8), Broadcast (7), Other (3) |
| Use Case Fit | 25% | Live streaming (10), Lecture capture (9), Recording (6), Consumer (0) |
| Tech Stack Signals | 15% | Competitive (10), LMS need (8), No solution (5) |
| Buying Authority | 15% | Budget holder (10), Influencer (7), End user (4), Student (0) |

**Tier Thresholds**: Tier 1 (70+), Tier 2 (50-69), Tier 3 (30-49), Not ICP (<30)

## API Endpoints

### Authentication (public)
- `POST /api/auth/token` - Issue JWT (API key → bearer token exchange)

**All endpoints below require `Authorization: Bearer <token>` header.**
**Exceptions: `/health`, `/`, `/docs`, webhooks (use HMAC signature auth).**

### Monitoring & Observability
- `GET /api/monitoring/credits` - Track Apollo credit usage and savings
- `GET /api/monitoring/rate-limits` - API health and backoff status
- `GET /api/monitoring/batches` - List active/completed batches
- `GET /api/monitoring/batches/{id}` - Detailed batch status

### Webhooks
- `POST /api/webhooks/apollo/phone-reveal` - Apollo async phone delivery
- `POST /api/webhooks/harvester/lead-push` - Real-time Harvester sync
- `POST /api/webhooks/clay/enrichment` - Clay fallback enrichment (75+ providers)
- `GET /api/webhooks/phones/pending` - Pending phone approvals
- `POST /api/webhooks/phones/approve` - Approve HubSpot sync

### LangGraph Agents
- `POST /api/agents/research` - Research a lead
- `POST /api/agents/scripts` - Get personalized script
- `POST /api/agents/competitors` - Get competitor intel
- `POST /api/agents/emails` - Generate email
- `POST /api/agents/emails/with-approval` - Generate email with human-in-the-loop approval
- `POST /api/agents/emails/approve/{thread_id}` - Approve/reject pending email
- `POST /api/agents/qualify` - Qualify lead against ICP criteria
- `POST /api/agents/qualify/stream` - Qualify with streaming progress (SSE)
- `POST /api/agents/emails/stream` - Token-level email streaming (SSE)
- `POST /api/agents/call-brief` - **One-page call prep brief** (research + qualify + script in parallel)

### Call Outcome Tracking
- `POST /api/call-outcomes` - Log a call outcome (auto-updates lead, schedules follow-up)
- `POST /api/call-outcomes/batch` - Batch log (end-of-day catch-up)
- `GET /api/call-outcomes/stats` - Daily performance dashboard (?date=YYYY-MM-DD)
- `GET /api/call-outcomes/stats/range` - Date range stats (?start=&end=)
- `GET /api/call-outcomes/follow-ups` - Pending follow-ups (?date=&include_overdue=true)
- `GET /api/call-outcomes/lead/{lead_id}` - Full call history for a lead
- `GET /api/call-outcomes/brief-effectiveness` - Brief quality → meeting conversion rates
- `POST /api/call-outcomes/{outcome_id}/hubspot-sync` - Manual HubSpot sync

### Voice AI Call Session
- `GET /ws/call-session?token=xxx` - **WebSocket for live call support** (bidirectional JSON)
- `POST /api/call-session/start` - REST: Start session + get call brief
- `POST /api/call-session/{id}/competitor` - REST: Competitor query during call
- `POST /api/call-session/{id}/objection` - REST: Objection response
- `POST /api/call-session/{id}/end` - REST: End call + log outcome
- `GET /api/call-session/{id}` - REST: Get session state

### Lead Management
- `POST /api/batch/process` - Process multiple leads
- `POST /api/batch/process/stream/tokens` - Single lead with token streaming (SSE)
- `POST /api/leads/ingest` - Ingest leads from Lead Harvester (with phone enrichment)
- `POST /api/leads/sync` - HubSpot sync
- `GET /api/leads/prioritized` - Get leads by tier/persona
- `GET /api/leads/ready-to-dial` - **Ready-to-dial list** (leads ranked by score with phones)

## Known Issues
- ~~mypy errors~~ **RESOLVED** (2026-01-31): All 174 errors fixed, strict mode compliant
- supabase module not installed for integration tests (skipped with SUPABASE_URL check)

## Code Style (Ruff Compliance)
- **E402**: Logger must be defined AFTER all imports
- **ARG001/ARG002**: Prefix unused params with underscore (`_method`, `_data`)
- **SIM102**: Combine nested if statements (`if a: if b:` → `if a and b:`)

## Apollo Phone Enrichment (CRITICAL)

> ⚠️ **Full documentation**: See `docs/reference/APOLLO_ENRICHMENT.md`

### Critical Discovery (2025-01-29)

**Apollo phone enrichment is ASYNCHRONOUS and requires a webhook.**

Per official Apollo documentation:
- `reveal_phone_number=true` **REQUIRES** a `webhook_url` parameter
- Without webhook: API returns error *"Please add a valid 'webhook_url' parameter"*
- The **immediate response only includes employer/HQ phone**
- **Mobile and direct phones are delivered via webhook 2-10 minutes later**

### Correct Usage
```python
# ✅ CORRECT - Full phone enrichment
payload = {
    "email": "john@company.com",
    "reveal_phone_number": True,
    "webhook_url": "https://api.yourdomain.com/api/webhooks/apollo/phone-reveal"
}
```

### Credit Costs
| Operation | Credits | Notes |
|-----------|---------|-------|
| Basic enrichment | 1 | Employer phone only |
| Phone enrichment | 8 per phone | Mobile, direct, work |
| Company phone (`work_hq`) | FREE | Included in basic |

### Phone Delivery Flow
```
API Request → Immediate: employer phone only
           → Webhook (2-10 min): mobile + direct phones
```

### Implementation Status
- ✅ `apollo.py` has `reveal_phone_number=true` by default
- ✅ `webhook_url` parameter supported
- ✅ Webhook endpoint: `POST /api/webhooks/apollo/phone-reveal`
- ✅ Config: `APOLLO_WEBHOOK_URL`, `APOLLO_WEBHOOK_SECRET`
- ✅ Local storage: `apollo_phone_webhooks` table (synced_to_hubspot=FALSE)
- ✅ Approval workflow: `GET /phones/pending`, `POST /phones/approve`

### Deployment Checklist
- [ ] Run migration: `psql -f migrations/003_add_webhook_phone_data.sql`
- [ ] Set `APOLLO_WEBHOOK_URL` to public endpoint (e.g., `https://api.yourdomain.com/api/webhooks/apollo/phone-reveal`)
- [ ] Set `APOLLO_WEBHOOK_SECRET` for signature verification
- [ ] Configure Supabase credentials (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`)

---

## Tiered Apollo Enrichment (Credit Optimization)

**Strategy**: Save ~67% credits by only revealing phones for ATL decision-makers.

| Phase | Cost | Action |
|-------|------|--------|
| Phase 1 | 1 credit | Basic enrichment - verify company, get title |
| Phase 2 | 8 credits | Phone reveal - ONLY if ATL decision-maker |

**ATL Detection** (`services/scoring/atl_detector.py`):
- Matches 40 title variations across 8 personas
- Fuzzy matching with 60% threshold (SequenceMatcher)
- Seniority-based detection (VP, Director, C-level)
- Negative signals: Student, Intern, Analyst, Coordinator

**Key Function**: `is_atl_decision_maker(title, seniority) -> ATLMatch`

**Rate Limiting**: Exponential backoff (1s → 32s max, 3 retries)

---

## Recent Work (2026-02-07) - Tech Debt Sprint: Wire Memory Modules
**Branch**: `main`

Wired 3 orphaned memory modules (UserMemoryStore 414 LOC, ConversationSummarizer 374 LOC, MessageTrimmer ~270 LOC) into production consumers. Previously only SemanticMemory was wired.

### Wired Modules
- **UserMemoryStore → CallSessionManager**: Prior interaction context in start_session(), interaction + objection recording in end_session()
- **UserMemoryStore → CallBriefAssembler**: 4th parallel call for user context, enriches brief with prior interaction data
- **MessageTrimmer + ConversationSummarizer → MasterOrchestrator**: Instantiated and wired as utilities, ready for message history activation

### New Test Files
- `tests/unit/test_user_memory_store.py` — UserMemoryStore unit tests
- `tests/unit/test_conversation_summarizer.py` — ConversationSummarizer unit tests
- `tests/unit/test_call_session_memory.py` — CallSession memory integration tests

**Code Quality**: 1309 tests passed, 5 skipped, 0 mypy errors, 0 ruff errors (51 new tests)

---

## Recent Work (2026-02-06) - Voice AI Call Session Integration
**Branch**: `main`

WebSocket + REST endpoints for live call support during Voice AI desktop app sessions. Manages session lifecycle: call brief generation, competitor battlecards, objection handling, and call outcome logging — all via a single connection.

### New Files
- `app/data/call_session_schemas.py` — Pydantic models for WS/REST message types (ClientMessage, ServerMessage, session state)
- `app/services/call_session/__init__.py` — Package init
- `app/services/call_session/manager.py` — CallSessionManager: in-memory session state, agent orchestration, fuzzy objection matching
- `app/api/routes/call_session.py` — WebSocket endpoint (`/ws/call-session`) + REST fallback (`/api/call-session/*`)
- `tests/unit/test_call_session_manager.py` (24 tests) — Session lifecycle, competitor/objection responses, outcome logging, fuzzy matching
- `tests/unit/test_call_session_websocket.py` (12 tests) — WS connect/auth, message routing, error handling
- `tests/unit/test_call_session_rest.py` (11 tests) — REST endpoint CRUD, session not found

### Modified Files
- `app/main.py` — Mounted `call_session_router` (REST) and `call_session_ws_router` (WebSocket)
- `.gitignore` — Added `*.dmg`, `*.exe`, `*.msi` patterns
- `PLANNING.md` — Added Voice AI endpoints, Clay webhook, architecture diagram updates
- `CLAUDE.md` — Added call session endpoints and project structure entries

### Key Features
- **Dual interface**: WebSocket (real-time bidirectional) + REST (fallback) — same `CallSessionManager`, zero logic duplication
- **JWT on WebSocket**: Token as query parameter (`?token=xxx`), validated on connect
- **In-memory sessions**: Ephemeral during call; briefs + outcomes persisted to Supabase via existing code
- **Agent reuse**: CallBriefAssembler, CompetitorIntelAgent, CallOutcomeService — no new AI logic
- **Fuzzy objection matching**: `SequenceMatcher` with 0.4 threshold against persona profiles
- **Graceful degradation**: All agent calls wrapped in try/except, returns partial data on failure

### WebSocket Protocol
```
Client → Server: {"type": "start_call|competitor_query|objection|end_call", "data": {...}}
Server → Client: {"type": "call_brief|competitor_response|objection_response|call_logged|error", "data": {...}}
```

**Code Quality**: 1253 tests passed, 5 skipped, 0 mypy errors, 0 ruff errors (47 new tests)

---

## Recent Work (2026-02-07) - Security Fix + Bug Fix
**Branch**: `main`

Two fixes from previous session handoff notes.

### Modified Files
- `app/api/routes/webhooks.py` — Added `Depends(require_auth)` to `/phones/pending` and `/phones/approve` endpoints
- `app/services/call_outcomes/service.py` — Fixed tier score aggregation: scores now counted per-brief, not per-outcome
- `tests/unit/test_brief_effectiveness_scoring.py` — Added regression test for tier score bug
- `tests/unit/test_phone_endpoint_auth.py` (NEW, 4 tests) — Auth enforcement tests for phone endpoints

### Key Fixes
- **Security: Phone endpoint auth** — `/phones/pending` and `/phones/approve` were BDR-facing data endpoints on the webhook router (which intentionally has NO router-level auth because webhooks use HMAC). Added per-endpoint `dependencies=[Depends(require_auth)]`.
- **Bug: Tier score duplication** — `tier_scores` was appended inside `for outcome in outcomes` loop. A brief with 3 outcomes contributed the same score 3x, inflating `avg_score`. Moved extraction before the outcome loop.

**Code Quality**: 1258 tests passed, 5 skipped, 0 mypy errors, 0 ruff errors (5 new tests)

---

## Deployment Checklists (Pending)

### Clay Enrichment
- [ ] Run migration: `psql -f migrations/006_add_clay_enrichment.sql`
- [ ] Set `CLAY_TABLE_WEBHOOK_URL` (from Clay UI)
- [ ] Set `CLAY_WEBHOOK_SECRET` for signature verification
- [ ] Set `CLAY_ENABLED=true` to activate

### Apollo Phone Webhooks
- [ ] Run migration: `psql -f migrations/003_add_webhook_phone_data.sql`
- [ ] Set `APOLLO_WEBHOOK_URL` to public endpoint
- [ ] Set `APOLLO_WEBHOOK_SECRET` for signature verification

### Call Briefs + Outcomes
- [ ] Run migration: `psql -f migrations/004_add_call_outcomes.sql`
- [ ] Run migration: `psql -f migrations/005_add_call_briefs.sql`

---

## Build History (condensed)
- **1309 tests**, 0 mypy errors, 0 ruff errors as of 2026-02-07
- All work on `main` branch. Key milestones:
  - Jan 27-28: Core agents (research, scripts, competitors, email, qualification)
  - Jan 29: Apollo tiered enrichment, Harvester sync, observability
  - Jan 31: mypy strict mode compliance (174 errors → 0)
  - Feb 5: LangGraph polish (middleware, streaming, memory, tracing), call briefs, outcomes
  - Feb 6: Brief analytics, Clay integration, JWT auth, Docker, Voice AI call sessions
  - Feb 7: Security fix (phone endpoint auth), tier score aggregation bug fix, tech debt sprint (wire memory modules)
