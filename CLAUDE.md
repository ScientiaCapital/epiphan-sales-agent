# Epiphan Sales Agent

AI-powered sales assistant for Epiphan Video BDR — warm call scripts, lead enrichment, ICP scoring, and CRM integration via LangGraph agents.

## Stack

- **Language**: Python 3.10+
- **Framework**: FastAPI
- **AI Agents**: LangGraph + langchain-anthropic (Claude)
- **Database**: Supabase (PostgreSQL)
- **Package manager**: uv
- **Testing**: pytest (1300+ tests)
- **Linting**: ruff + mypy (strict, 0 errors required)

## Directory Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── api/routes/          # agents, batch, call_outcomes, call_session, leads, webhooks, auth
│   ├── data/                # Pydantic schemas, scripts, competitor battlecards, persona scripts
│   └── services/
│       ├── enrichment/      # Apollo (primary), Clay (fallback), pipeline, scraper
│       ├── langgraph/       # Agents: research, scripts, competitors, email, qualify, call_brief
│       ├── scoring/         # ATL detector (8 personas, 40 title variations)
│       ├── call_outcomes/   # BDR call outcome tracking
│       ├── call_session/    # Voice AI session manager (WebSocket + REST)
│       └── integrations/hubspot/
├── tests/unit/              # 1300+ unit tests
└── pyproject.toml
```

## Key Commands

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8001   # Start server
uv run pytest tests/ -v                             # Run tests
uv run ruff check .                                 # Lint
uv run mypy app/                                    # Type check
```

## Environment Variables

```bash
ANTHROPIC_API_KEY=          # Claude (LangGraph agents)
SUPABASE_URL=               # Supabase project URL
SUPABASE_SERVICE_KEY=       # Supabase service role key
APOLLO_API_KEY=             # Apollo.io enrichment
APOLLO_WEBHOOK_URL=         # For async phone delivery
APOLLO_WEBHOOK_SECRET=      # Webhook signature verification
HUBSPOT_ACCESS_TOKEN=       # HubSpot private app token
LANGSMITH_API_KEY=          # LangSmith tracing (optional)
CLAY_TABLE_WEBHOOK_URL=     # Clay.com fallback enrichment
CLAY_WEBHOOK_SECRET=
```

## Apollo Phone Enrichment

- Phone enrichment is ALWAYS required in lead processing workflows
- Tiered: 1 credit (basic) → 8 credits (phone reveal, ATL decision-makers only)
- Phone reveal is async — mobile/direct phones delivered via webhook 2-10 min later
- Webhook: `POST /api/webhooks/apollo/phone-reveal`
- Full details: `docs/reference/APOLLO_ENRICHMENT.md`

## Code Style Rules

- **No OpenAI** — all LLM calls use `langchain-anthropic` (Claude) only
- 0 mypy errors and 0 ruff errors required before committing
- E402: Logger defined AFTER all imports
- ARG001/ARG002: Prefix unused params with `_`
- SIM102: Combine nested if statements

## LangGraph Agents (6)

1. Lead Research Agent — Apollo + web scraping enrichment
2. Script Selection Agent — persona-specific warm call scripts
3. Competitor Intelligence Agent — battlecard responses
4. Email Personalization Agent — personalized outreach
5. Qualification Agent — 5-dimension ICP scoring (Tier 1: 70+, Tier 2: 50-69)
6. Call Brief Assembler — parallel research + qualify + script in one brief
