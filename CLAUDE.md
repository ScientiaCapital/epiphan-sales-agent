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
│   │   ├── scripts.py       # Script endpoints
│   │   └── leads.py         # Lead scoring endpoints
│   ├── data/
│   │   ├── schemas.py       # Pydantic models
│   │   ├── scripts.py       # Script lookup functions
│   │   ├── competitors.py   # Competitor battlecards
│   │   └── persona_warm_scripts.py  # Persona-specific scripts
│   └── services/
│       ├── enrichment/      # Data enrichment clients
│       │   ├── apollo.py    # Apollo.io API
│       │   ├── audit.py     # Enrichment audit logging & HubSpot mapping
│       │   ├── clearbit.py  # Clearbit API
│       │   └── scraper.py   # Web scraping
│       ├── scoring/         # Lead scoring services
│       │   └── atl_detector.py  # ATL decision-maker detection (8 personas)
│       ├── langgraph/       # AI Agents
│       │   ├── agents/      # LangGraph agents
│       │   ├── tools/       # Agent tools
│       │   └── states.py    # State schemas
│       ├── llm/             # LLM clients
│       │   └── clients.py   # Multi-model router
│       └── integrations/
│           └── hubspot/     # HubSpot CRM client
├── tests/
│   ├── unit/                # Unit tests (623+)
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

1. **Lead Research Agent** - Enriches leads via Apollo, Clearbit, web scraping
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
- `POST /api/agents/research` - Research a lead
- `POST /api/agents/scripts` - Get personalized script
- `POST /api/agents/competitors` - Get competitor intel
- `POST /api/agents/emails` - Generate email
- `POST /api/agents/emails/with-approval` - Generate email with human-in-the-loop approval
- `POST /api/agents/emails/approve/{thread_id}` - Approve/reject pending email
- `POST /api/agents/qualify` - Qualify lead against ICP criteria
- `POST /api/agents/qualify/stream` - Qualify with streaming progress (SSE)
- `POST /api/batch/process` - Process multiple leads
- `POST /api/leads/ingest` - Ingest leads from Lead Harvester (with phone enrichment)

## Known Issues
- mypy errors (missing type stubs for fastapi, hubspot)
- supabase module not installed for integration tests

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
- ⚠️ **TODO**: Implement webhook endpoint (`/api/webhooks/apollo/phone-reveal`)
- ⚠️ **TODO**: Add `APOLLO_WEBHOOK_URL` to config
- ⚠️ **TODO**: Update lead records when webhook receives phones

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

## Recent Work (2025-01-29)
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
- 463 tests passing, 0 lint errors

## Previous Work (2025-01-28)
- Implemented Qualification Agent with 5-dimension ICP scoring
- Added qualification_tools.py with Tim's weighted scoring criteria
- New `/api/agents/qualify` endpoint for lead qualification
- 76 new tests for qualification (60 tools + 16 agent)
- 416 tests passing, 0 lint errors

## Earlier Work (2025-01-27)
- Implemented 4 LangGraph agents (Lead Research, Script Selection, Competitor Intel, Email Personalization)
- Built enrichment clients (Apollo, Clearbit, Web Scraper)
- Added agent API endpoints and batch processing
