# Epiphan Sales Agent - Claude Code Project Memory

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
│       │   ├── clearbit.py  # Clearbit API
│       │   └── scraper.py   # Web scraping
│       ├── langgraph/       # AI Agents
│       │   ├── agents/      # LangGraph agents
│       │   ├── tools/       # Agent tools
│       │   └── states.py    # State schemas
│       ├── llm/             # LLM clients
│       │   └── clients.py   # Multi-model router
│       └── integrations/
│           └── hubspot/     # HubSpot CRM client
├── tests/
│   ├── unit/                # Unit tests (416+)
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
- `POST /api/agents/qualify` - Qualify lead against ICP criteria
- `POST /api/batch/process` - Process multiple leads

## Known Issues
- mypy errors (missing type stubs for fastapi, hubspot)
- supabase module not installed for integration tests

## Recent Work (2025-01-28)
- Implemented Qualification Agent with 5-dimension ICP scoring
- Added qualification_tools.py with Tim's weighted scoring criteria
- New `/api/agents/qualify` endpoint for lead qualification
- 76 new tests for qualification (60 tools + 16 agent)
- 416 tests passing, 0 lint errors

## Previous Work (2025-01-27)
- Implemented 4 LangGraph agents (Lead Research, Script Selection, Competitor Intel, Email Personalization)
- Built enrichment clients (Apollo, Clearbit, Web Scraper)
- Added agent API endpoints and batch processing
