# epiphan-sales-agent

**Branch**: main | **Updated**: 2026-02-06

## Status
Production-ready AI sales assistant with 5 LangGraph agents, Call Brief Assembler, Call Outcome Tracking, Master Orchestrator with parallel execution and review gates, tiered Apollo enrichment, observability endpoints, LangSmith tracing, and real-time Harvester sync. JWT API authentication and Docker deployment added. 1088 tests (1083 passed, 5 skipped), 0 mypy errors, 0 ruff lint errors.

## Today's Focus
Production hardening: JWT API authentication, Dockerfile, doc hygiene.

## Done (This Session)
- JWT API authentication (19 new tests):
  - `app/middleware/auth.py` — JWT middleware: create_access_token, get_current_user, require_auth
  - `app/api/routes/auth.py` — Token endpoint: POST /api/auth/token (API key → JWT exchange)
  - 9 route files protected with `Depends(require_auth)` — agents, batch, call_brief, call_outcomes, competitors, leads, monitoring, personas, scripts
  - Public routes preserved: /health, /, /docs, /api/auth/token, webhooks (HMAC auth)
  - Test conftest updated with dependency_overrides for auth bypass
- Docker deployment:
  - `backend/Dockerfile` — Multi-stage build with uv, non-root user, healthcheck
  - `backend/.dockerignore` — Excludes tests, .venv, .env, docs
  - `docker-compose.yml` — Added api service with postgres/redis dependencies
  - `pyproject.toml` — Added missing core deps (fastapi, uvicorn, pydantic-settings)
- Doc hygiene:
  - PROJECT_CONTEXT.md — Cleared stale Done list, updated date
  - PLANNING.md — Fixed section numbering (§3 → §4 → §5)
  - PRODUCTION_CHECKLIST.md — Added Migration 4 (call_outcomes), Docker deploy instructions

## Recent Commits
- `c905964` docs: Update project docs for call outcome tracking sprint
- `72362e8` feat: Implement Call Outcome Tracking (47 tests) — log outcomes, auto follow-ups, daily stats
- `148cc4b` feat: Implement Call Prep Brief + Ready-to-Dial endpoints (48 tests)
- `ec58678` test: Add integration tests for gap analysis features (65 tests)
- `77bb333` feat: Implement LangChain/LangGraph gap analysis improvements

## Key Features Implemented
- **JWT API Authentication**: Bearer token auth on all endpoints, token issuance via API key exchange
- **5 LangGraph Agents**: Lead Research, Script Selection, Competitor Intel, Email Personalization, Qualification
- **Call Brief Assembler**: Composition layer — runs 3 agents in parallel, enriches with playbook data
- **Call Outcome Tracking**: Pure data layer — log call outcomes, auto follow-ups, lead status updates, daily stats dashboard, HubSpot sync
- **Master Orchestrator**: Parallel agent execution with review gates using Command pattern
- **Tiered Apollo Enrichment**: Phase 1 (1 credit) + Phase 2 (8 credits for ATL only) = ~67% savings
- **Observability**: Credits, rate-limits, batch monitoring, LangSmith tracing
- **Streaming**: Token-level SSE streaming for emails and qualification
- **Harvester Sync**: Real-time webhook with auto-qualification
- **Docker Deployment**: Multi-stage Dockerfile with uv, docker-compose with full stack

## Next Sprint Candidates
- Frontend UI (monitoring dashboard, call brief viewer, phone approval)
- Link call outcomes to call briefs for closed-loop feedback
- Call brief effectiveness scoring

## Blockers
- None

## Tech Stack
Python 3.10+ | FastAPI | Pydantic | Supabase | LangGraph | Apollo | uv | pytest | ruff | mypy (strict) | Docker | PyJWT
