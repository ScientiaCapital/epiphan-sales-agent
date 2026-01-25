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
│   ├── data/
│   │   ├── schemas.py       # Pydantic models
│   │   ├── scripts.py       # Script lookup functions
│   │   └── persona_warm_scripts.py  # Persona-specific scripts
│   └── services/
│       └── integrations/
│           ├── hubspot/     # HubSpot CRM client
│           └── clari/       # Clari Copilot client
├── tests/
│   ├── unit/                # Unit tests
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

## Known Issues
- 250 ruff lint errors (mostly auto-fixable PEP 604/585 style)
- 47 mypy errors (missing type stubs for fastapi, hubspot)
- supabase module not installed for integration tests

## Recent Work
- Implemented persona-specific warm call scripts (ACQP framework)
- Added test coverage for all 8 personas
- 50 tests passing
