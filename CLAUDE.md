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
│   ├── api/routes/
│   │   ├── agents.py        # LangGraph agent endpoints
│   │   ├── batch.py         # Batch processing endpoint
│   │   ├── monitoring.py    # Observability (credits, rate-limits, batches)
│   │   ├── scripts.py       # Script endpoints
│   │   ├── leads.py         # Lead scoring endpoints
│   │   └── webhooks.py      # Apollo & Harvester webhooks
│   ├── data/
│   │   ├── schemas.py       # Pydantic models
│   │   ├── scripts.py       # Script lookup functions
│   │   ├── competitors.py   # Competitor battlecards
│   │   └── persona_warm_scripts.py  # Persona-specific scripts
│   └── services/
│       ├── enrichment/      # Data enrichment clients
│       │   ├── apollo.py    # Apollo.io API (primary enrichment)
│       │   ├── audit.py     # Enrichment audit logging & HubSpot mapping
│       │   ├── pipeline.py  # Background processing pipeline
│       │   └── scraper.py   # Web scraping
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
│   ├── unit/                # Unit tests (891+)
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
Five AI agents powered by LangGraph + Claude/Cerebras:

1. **Lead Research Agent** - Enriches leads via Apollo, web scraping
2. **Script Selection Agent** - Selects and personalizes call scripts
3. **Competitor Intelligence Agent** - Provides battlecard responses
4. **Email Personalization Agent** - Generates personalized outreach emails
5. **Qualification Agent** - Scores leads against 5-dimension weighted ICP criteria

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

### Monitoring & Observability
- `GET /api/monitoring/credits` - Track Apollo credit usage and savings
- `GET /api/monitoring/rate-limits` - API health and backoff status
- `GET /api/monitoring/batches` - List active/completed batches
- `GET /api/monitoring/batches/{id}` - Detailed batch status

### Webhooks
- `POST /api/webhooks/apollo/phone-reveal` - Apollo async phone delivery
- `POST /api/webhooks/harvester/lead-push` - Real-time Harvester sync
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

### Lead Management
- `POST /api/batch/process` - Process multiple leads
- `POST /api/batch/process/stream/tokens` - Single lead with token streaming (SSE)
- `POST /api/leads/ingest` - Ingest leads from Lead Harvester (with phone enrichment)
- `POST /api/leads/sync` - HubSpot sync
- `GET /api/leads/prioritized` - Get leads by tier/persona

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

## Recent Work (2026-02-05 Late Evening) - LangChain/LangGraph Gap Analysis Polish
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
