# Coding Rules — epiphan-sales-agent

## Stack
- **Language**: Python 3.10+
- **Framework**: FastAPI
- **AI Agents**: LangGraph + langchain-anthropic
- **Database**: Supabase (PostgreSQL)
- **Package manager**: uv (not pip)
- **Validation**: Pydantic v2
- **Testing**: pytest (1300+ tests)
- **Linting**: ruff (strict), mypy (strict mode, 0 errors required)

## Key Patterns
- All source code under `backend/app/`
- Agents in `backend/app/services/langgraph/agents/`
- API routes in `backend/app/api/routes/`
- Pydantic schemas in `backend/app/data/schemas.py`
- Apollo enrichment is tiered: basic (1 credit) first, phone reveal (8 credits) only for ATL decision-makers
- Phone enrichment is async — requires webhook delivery (2-10 min delay for mobile/direct)
- Ruff compliance: logger defined AFTER imports (E402), unused params prefixed `_` (ARG001/ARG002)

## Rules
- **No OpenAI** — LLM calls use `langchain-anthropic` (Claude) only
- All secrets in `.env` — never hardcoded
- Maintain 0 mypy errors and 0 ruff errors before committing
- Phone enrichment must ALWAYS be included in lead processing workflows
- Run tests with `uv run pytest`, lint with `uv run ruff check .`

## Testing
- Run all tests: `cd backend && uv run pytest tests/ -v`
- Unit tests: `tests/unit/` — no external services needed
- Integration tests: `tests/integration/` — requires Supabase credentials
