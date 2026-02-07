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

## Recent Work (2026-02-06) - Clay.com Enrichment Integration
**Branch**: `main`

Clay as fallback enrichment source (75+ provider waterfall). Webhook-based: POST lead → Clay enriches → Clay POSTs back. Feature-flagged (`CLAY_ENABLED=false`). Phone priority: Apollo > Harvester > Clay.

### New Files
- `app/services/enrichment/clay.py` — ClayClient, ClayEnrichmentData, phone type mapping, singleton
- `migrations/006_add_clay_enrichment.sql` — clay_enrichment_results table + indexes
- `tests/unit/test_clay_client.py` (18 tests) — Client, parsing, feature flag, singleton
- `tests/unit/test_clay_webhook.py` (10 tests) — Endpoint, HMAC, payload handling
- `tests/unit/test_clay_supabase.py` (6 tests) — CRUD methods
- `tests/unit/test_clay_phone_merging.py` (6 tests) — Priority, dedup, backward compat
- `tests/unit/test_clay_pipeline.py` (4 tests) — Fallback trigger, feature flag, graceful degradation
- `tests/unit/test_clay_audit.py` (5 tests) — Audit entries, summary

### Modified Files
- `app/core/config.py` — 3 new settings: `clay_table_webhook_url`, `clay_webhook_secret`, `clay_enabled`
- `app/api/routes/webhooks.py` — `POST /api/webhooks/clay/enrichment` + HMAC verification
- `app/services/database/supabase_client.py` — 4 Clay CRUD methods (store, get, get_unsynced, mark_synced)
- `app/services/langgraph/tools/harvester_mapper.py` — `clay_phones` param in `enrich_phone_numbers()`
- `app/services/enrichment/pipeline.py` — Clay fallback trigger when Apollo finds no phone
- `app/services/enrichment/audit.py` — `EnrichmentType.CLAY` + `log_clay_enrichment()`
- `backend/.env.example` — Clay env vars section

### Key Features
- **Webhook-based**: No REST API — mirrors proven Apollo webhook pattern
- **Feature-flagged**: `CLAY_ENABLED=false` by default, zero risk to existing flow
- **Phone priority**: Apollo (primary) > Harvester (secondary) > Clay (tertiary fallback)
- **Graceful degradation**: Clay failures never block enrichment pipeline
- **HMAC verification**: Same `hmac.compare_digest()` pattern as Apollo/Harvester
- **Supabase upsert**: `on_conflict="lead_id"` for idempotent webhook handling

### Deployment Checklist
- [ ] Run migration: `psql -f migrations/006_add_clay_enrichment.sql`
- [ ] Set `CLAY_TABLE_WEBHOOK_URL` (from Clay UI)
- [ ] Set `CLAY_WEBHOOK_SECRET` for signature verification
- [ ] Set `CLAY_ENABLED=true` to activate

**Code Quality**: 1206 tests passed, 5 skipped, 0 mypy errors, 0 ruff errors (49 new tests)

---

## Recent Work (2026-02-06) - Production Hardening
**Branch**: `main`

JWT API authentication, Docker deployment, doc hygiene.

### New Files
- `app/middleware/__init__.py` — Middleware package
- `app/middleware/auth.py` — JWT middleware: create_access_token, get_current_user, require_auth
- `app/api/routes/auth.py` — Token endpoint: POST /api/auth/token
- `backend/Dockerfile` — Multi-stage production build with uv
- `backend/.dockerignore` — Docker build exclusions
- `tests/unit/test_auth_middleware.py` (19 tests) — Token creation, validation, expiry, integration

### Modified Files
- `app/main.py` — Registered auth_router
- `app/api/routes/{agents,batch,call_brief,call_outcomes,competitors,leads,monitoring,personas,scripts}.py` — Added `dependencies=[Depends(require_auth)]`
- `tests/conftest.py` — Added `_bypass_jwt_auth` fixture (dependency_overrides)
- `docker-compose.yml` — Added api service
- `backend/pyproject.toml` — Added fastapi, uvicorn, pydantic-settings deps
- `PLANNING.md` — Fixed section numbering
- `docs/deployment/PRODUCTION_CHECKLIST.md` — Added migration 004, Docker deploy instructions

### Key Features
- **JWT Auth**: Bearer token required on all non-public endpoints. 15-min token expiry (configurable). Constant-time API key comparison.
- **Public Routes**: /health, /, /docs, /api/auth/token, webhooks (HMAC auth)
- **Docker**: Multi-stage build (python:3.12-slim), non-root user, healthcheck, 4 uvicorn workers

**Code Quality**: 1083 tests passed, 5 skipped, 0 mypy errors, 0 ruff errors (19 new tests)

---

## Recent Work (2026-02-06) - Brief Effectiveness Deep Analytics
**Branch**: `main`

Deep analytics for call brief effectiveness: per-persona deep dives, script matrix, tier analytics, phone type impact. All data from existing `brief_json` JSONB + `call_outcomes` — no new migrations.

### New Files
- `tests/unit/test_brief_effectiveness_scoring.py` (55 tests) — 11 test classes: funnel builder, phone impact, top items, avg duration, persona extraction, tier extraction, enhanced effectiveness, persona deep dive, script matrix, API endpoints, edge cases

### Modified Files
- `app/data/call_outcome_schemas.py` — Added 10 Pydantic models: ConversionFunnel, QualityConversion, PhoneTypeImpact, TierAnalytics, PersonaSummary, ScriptTriggerPerformance, ScriptTemplateRow, BriefEffectivenessResponse, PersonaEffectivenessDetail, ScriptEffectivenessResponse
- `app/services/call_outcomes/service.py` — Refactored `get_brief_effectiveness()` to return typed `BriefEffectivenessResponse`. Added `get_persona_effectiveness()`, `get_script_effectiveness()`, and 6 private helpers
- `app/services/database/supabase_client.py` — Expanded `get_briefs_with_outcomes()` select fields + optional `persona_id` param with Python-side filtering
- `app/api/routes/call_outcomes.py` — Added `GET /brief-effectiveness/persona/{persona_id}` and `GET /brief-effectiveness/scripts` endpoints

### Key Features
- **ConversionFunnel**: Reusable building block model used across persona, tier, trigger, and overall contexts
- **Persona Deep Dive**: Per-trigger conversion funnels, top objections/signals with counts, phone type impact
- **Script Matrix**: Every persona x trigger combination ranked by meeting rate with sample size warnings (< 5)
- **Backward Compatible**: Enhanced response preserves all 5 original fields from basic brief-effectiveness

**Code Quality**: 1157 tests passed, 5 skipped, 0 mypy errors, 0 ruff errors (55 new tests)

---

## Recent Work (2026-02-06) - Call Brief ↔ Outcome Linkage
**Branch**: `main`

Closes the feedback loop: persisted call briefs linked to outcomes so agents can learn which scripts/briefs lead to meetings.

### New Files
- `migrations/005_add_call_briefs.sql` — call_briefs table + call_brief_id FK on call_outcomes
- `tests/unit/test_call_brief_linkage.py` (19 tests) — Schema, service, API, analytics tests

### Modified Files
- `app/services/langgraph/agents/call_brief.py` — Added `brief_id: str | None` to CallBriefResponse
- `app/api/routes/call_brief.py` — Added `save_call_brief()` persistence + brief_id assignment
- `app/data/call_outcome_schemas.py` — Added `call_brief_id: str | None` to CallOutcomeCreate + CallOutcomeResponse
- `app/services/call_outcomes/service.py` — Added `call_brief_id` to record insert + `get_brief_effectiveness()` analytics method
- `app/api/routes/call_outcomes.py` — Added `GET /api/call-outcomes/brief-effectiveness` endpoint
- `app/services/database/supabase_client.py` — Added save_call_brief, get_call_brief, get_briefs_with_outcomes methods

### Key Features
- **Brief Persistence**: `POST /api/agents/call-brief` now auto-saves to DB and returns `brief_id` (graceful degradation on failure)
- **Outcome Linkage**: `POST /api/call-outcomes` accepts optional `call_brief_id` to link outcome to its prep brief
- **Effectiveness Analytics**: `GET /api/call-outcomes/brief-effectiveness` — conversion rates by quality level, objection prediction accuracy

**Code Quality**: 1102 tests passed, 5 skipped, 0 mypy errors, 0 ruff errors (19 new tests)

---

## Previous Work (2026-02-05) - Call Outcome Tracking
**Branch**: `main`

Closes the feedback loop: log call outcomes, auto-update lead state, auto-schedule follow-ups, track daily stats.

### New Files
- `migrations/004_add_call_outcomes.sql` - New `call_outcomes` table (UUID PK, disposition, result, follow-up scheduling, HubSpot sync tracking)
- `app/data/call_outcome_schemas.py` - Pydantic models: CallDisposition, CallResult, FollowUpType enums + request/response models
- `app/services/call_outcomes/service.py` - CallOutcomeService: log_outcome (with default follow-up rules), get_daily_stats, get_lead_history, get_pending_follow_ups, sync_to_hubspot
- `app/api/routes/call_outcomes.py` - 7 endpoints under `/api/call-outcomes`
- `tests/unit/test_call_outcomes.py` (30 tests) - API endpoint tests
- `tests/unit/test_call_outcome_service.py` (17 tests) - Service/business logic tests

### Modified Files
- `app/services/database/supabase_client.py` - Added 8 CRUD methods for call outcomes
- `app/main.py` - Registered call_outcomes_router

### Key Features
- **Default Follow-Up Rules**: VM→callback 2 days, no_answer→1 day, gatekeeper→1 day, connected+FU→email 3 days. Tim can override.
- **Lead Status Auto-Update**: meeting_booked→meeting_scheduled, qualified_out→disqualified, dead→dead. Others unchanged.
- **Business Day Calc**: Follow-up dates skip weekends
- **Daily Stats**: connect_rate, meeting_rate (meetings/connections), avg_duration (connected only), phone_type breakdown
- **No AI/LLM**: Pure data tracking, no external API calls except optional HubSpot sync

**Code Quality**: 1064 tests passed, 5 skipped, 0 mypy errors, 0 ruff errors (47 new tests)

---

## Previous Work (2026-02-05) - Call Prep Brief + Ready-to-Dial
**Branch**: `main`

Implemented single-endpoint call preparation replacing 3 separate API calls + manual combination.

### New Files
- `app/services/langgraph/agents/call_brief.py` - CallBriefAssembler composition layer (runs research + qualify + script agents in parallel via asyncio.gather)
- `app/api/routes/call_brief.py` - `POST /api/agents/call-brief` endpoint
- `tests/unit/test_call_brief_assembler.py` (30 tests) - Assembler logic, phone extraction, graceful degradation
- `tests/unit/test_api_call_brief.py` (11 tests) - API endpoint behavior
- `tests/unit/test_ready_to_dial.py` (8 tests) - Ready-to-dial filtering

### Modified Files
- `app/api/routes/leads.py` - Added `GET /api/leads/ready-to-dial` endpoint
- `app/main.py` - Registered call_brief_router
- `app/services/langgraph/agents/__init__.py` - Export CallBriefAssembler

### Key Features
- **Call Brief**: Runs 3 agents in parallel (~3-5s), enriches with playbook data (persona objections, SPIN discovery questions, competitor battlecards, reference stories)
- **Ready-to-Dial**: Answers "who should I call next?" with leads ranked by score, filterable by tier and phone availability
- **Graceful Degradation**: Each agent failure returns partial brief from remaining data + static playbook
- **Quality Scoring**: Rates brief completeness as HIGH/MEDIUM/LOW (phone presence weighted highest at +3)
- **Intelligence Gaps**: Flags missing phone as CRITICAL

**Code Quality**: 1017 tests passed, 5 skipped, 0 mypy errors, 0 ruff errors (48 new tests)

---

## Previous Work (2026-02-05 Morning) - Integration Testing Sprint
**Branch**: `main`

Completed integration testing for the gap analysis features implemented in the previous session:

### New Test Files Created (65 tests)
- `tests/unit/test_checkpointing_encryption.py` (20 tests) - AES encryption roundtrip, key validation, cipher protocol compliance
- `tests/integration/test_qualification_edge_cases.py` (21 tests) - Extended thinking triggers on borderline scores (28-32, 48-52, 68-72) and low confidence (<0.6)
- `tests/integration/test_middleware_pipeline.py` (24 tests) - ModelCallLimitMiddleware, ModelFallbackMiddleware, full pipeline

**Code Quality**: 969 tests passed, 5 skipped, 0 mypy errors, 0 ruff errors (65 new tests)

---

## Previous Work (2026-02-05 Late Evening) - LangChain/LangGraph Gap Analysis Polish
**Branch**: `main`

Completed comprehensive gap analysis (54 documentation URLs analyzed) and implemented priority improvements:

### Phase 1: Quick Wins
- **Extended Thinking Integration**: `_is_edge_case()` detects borderline scores (28-32, 48-52, 68-72) and low confidence (<0.6), triggers `claude_with_thinking` for nuanced tier decisions
- **List Reducers**: Added `Annotated[list, add]` to `OrchestratorState.errors` and `phase_results` - lists now append instead of overwrite
- **Encrypted Checkpointing**: `AESCipher` class implementing `CipherProtocol`, activated via `LANGGRAPH_AES_KEY` env var

### Phase 2: Middleware Enhancements
- **ModelCallLimitMiddleware**: Prevents runaway costs with per-thread (50) and per-run (20) limits
- **ModelFallbackMiddleware**: Records primary model errors, triggers fallback to OpenRouter on retry

### Phase 3: Memory Enhancements
- **UserMemoryStore** (`memory/user_store.py`): Cross-thread user preferences, interaction history, objections tracking
- **ConversationSummarizer** (`memory/summarizer.py`): Context overflow management with key decision extraction

**Code Quality**: 904 tests passed, 5 skipped, 0 mypy errors, 0 ruff errors (19 new middleware tests)

---

## Previous Work (2026-02-05 Evening) - LangGraph v1.0 Best Practices
**Branch**: `feature/agent-polish` → merged to `main`

Implemented recommendations from LangGraph documentation research (27 URLs analyzed):

### Phase 1: Quick Wins
- **Prompt Caching**: Added `anthropic-beta: prompt-caching-2024-07-31` header for ~10x speedup
- **Node Caching**: `InMemoryCache` for Apollo enrichment (avoids 8 credit duplicate calls)
- **RetryPolicy**: Native LangGraph retry with exponential backoff for API calls

### Phase 2: Architecture Improvements
- **Command Pattern**: Review gates now use `Command(update=..., goto=...)` for explicit routing
- **Input/Output Schemas**: `OrchestratorInput` and `OrchestratorOutput` TypedDicts for cleaner API

### Phase 3: Optional Enhancements
- **Extended Thinking**: `claude_with_thinking` property with 2000 token thinking budget
- **Time-Travel Debug**: `GET /api/agents/debug/{thread_id}/history` for checkpoint history

**Code Quality**: 890 tests passed, 5 skipped, 0 mypy errors, 0 ruff errors

---

## Previous Work (2026-02-05 Morning) - LangGraph Agent Polish Sprint
**Branch**: `feature/agent-polish` → `feature/agent-orchestration`

Completed 7-phase sprint implementing LangChain best practices:

### Phase 1-4: Error Handling, Middleware, Memory Trimming, Synthesis (Prior Session)
- ToolException pattern across all tools
- Middleware layer: `PIIDetectionMiddleware`, `DynamicModelMiddleware`, `RateLimitMiddleware`
- `MessageTrimmer` for short-term memory management
- Master Orchestrator with parallel execution and review gates

### Phase 5: Enhanced Token Streaming
- `astream_events(version="v2")` for granular token streaming
- New endpoints: `/api/agents/emails/stream`, `/api/batch/process/stream/tokens`
- SSE (Server-Sent Events) for real-time progress updates
- 12 new tests in `test_streaming.py`

### Phase 6: Semantic Memory Activation
- `SemanticMemory` class in `memory/semantic_store.py`
- Pattern learning for Tier 1/2 qualification successes
- Similar lead retrieval at research phase start
- 14 new tests in `test_semantic_memory.py`

### Phase 7: LangSmith Observability
- `@trace_agent` decorator for automatic LangSmith tracing
- `TracingMetrics` class for execution metrics
- `with_tracing_context()` async context manager
- 17 new tests in `test_tracing.py`

**Code Quality**: 891 tests (886 passed, 5 skipped), 0 mypy errors, 0 ruff errors

---

## Previous Work (2026-01-31) - Tech Debt Resolution
- **mypy Strict Mode Compliance** (COMMITTED: 44793c0)
  - Resolved all 174 mypy type errors
  - Added return type annotations to all `__init__` methods
  - Added generic type parameters to SQLAlchemy Mapped[] columns (ARRAY, JSONB)
  - Fixed `Sequence` vs `list` invariance issues in function signatures
  - Added `cast()` for Supabase/Clari query results returning `Any`
  - Fixed pytest fixture naming (removed underscore prefix for proper injection)
  - Added mypy overrides in `pyproject.toml` for external libraries:
    - `hubspot.*`, `langgraph.*`, `langchain_*` (ignore_missing_imports)
    - `app.services.llm.clients` (ignore_errors for LangChain type mismatches)
- **Code Quality**: 669 tests passing, 0 mypy errors, 0 ruff lint errors
- Removed Clearbit enrichment provider (consolidated to Apollo-only)

## Previous Work (2025-01-29) - Session 2
- **Observability Endpoints** (COMMITTED: ae6d025)
  - `GET /api/monitoring/credits` - Track Apollo credit usage and savings
  - `GET /api/monitoring/rate-limits` - API health and backoff status
  - `GET /api/monitoring/batches/{id}` - Batch status tracking
  - In-memory batch tracking with BatchAuditSummary integration
- **Real-time Harvester Sync** (COMMITTED: ae6d025)
  - `POST /api/webhooks/harvester/lead-push` - Webhook endpoint
  - Background processing pipeline (`pipeline.py`)
  - HMAC-SHA256 signature verification
  - Config: `HARVESTER_WEBHOOK_SECRET`
- 46 new tests (21 monitoring + 16 webhook + 9 pipeline)
- 676 tests passing, 0 lint errors

## Previous Work (2025-01-29) - Session 1
- **Tiered Apollo Enrichment** (COMMITTED: 03aef3f)
  - ATL decision-maker detector with 8 personas, 40 title variations
  - Two-phase enrichment: 1 credit basic, +8 only for ATL
  - Rate limit handling with exponential backoff
  - Audit logging with HubSpot property mapping
  - 130 new tests (110 ATL detector + 20 tiered enrichment)
  - Estimated 67% credit savings on typical batches
- **CRITICAL FIX: Apollo Phone Enrichment**
  - Fixed Apollo client to include `reveal_phone_number=true`
  - Without this, ALL phone enrichment was returning empty arrays!
  - Added `_extract_phone()` helper for phone type extraction
  - 7 new tests for phone extraction verification
- **Lead Harvester Integration**: New `/api/leads/ingest` endpoint for batch lead qualification
  - `HarvesterLeadInput` schema for ingesting harvester exports
  - Phone enrichment prioritized (PHONES ARE GOLD!)
  - `harvester_mapper.py` with mapping and phone extraction utilities
  - 41 new tests for ingest endpoint
- **LangGraph Enhancements**:
  - PostgresSaver checkpointing (`checkpointing.py`) for state persistence
  - Semantic memory store (`memory.py`) for pattern learning
  - Human-in-the-loop email approval workflow
  - Streaming progress via SSE (`/api/agents/qualify/stream`)
  - New endpoints: `/api/agents/emails/with-approval`, `/api/agents/emails/approve/{thread_id}`
- SQL migrations: `001_add_checkpoints.sql`, `002_add_semantic_store.sql`

## Previous Work (2025-01-28)
- Implemented Qualification Agent with 5-dimension ICP scoring
- Added qualification_tools.py with Tim's weighted scoring criteria
- New `/api/agents/qualify` endpoint for lead qualification
- 76 new tests for qualification (60 tools + 16 agent)

## Earlier Work (2025-01-27)
- Implemented 4 LangGraph agents (Lead Research, Script Selection, Competitor Intel, Email Personalization)
- Built enrichment clients (Apollo, Web Scraper)
- Added agent API endpoints and batch processing
