# epiphan-sales-agent

**Branch**: main | **Updated**: 2026-02-06

## Status
Production-ready AI sales assistant with 5 LangGraph agents, Call Brief Assembler with persistence, Call Outcome Tracking with brief linkage, Master Orchestrator with parallel execution and review gates, tiered Apollo enrichment, observability endpoints, LangSmith tracing, and real-time Harvester sync. JWT API authentication and Docker deployment added. 1102 tests (1097 passed, 5 skipped), 0 mypy errors, 0 ruff lint errors.

## Today's Focus
Production hardening + closed-loop feedback: JWT auth, Docker, call brief ↔ outcome linkage.

## Done (This Session)
- JWT API authentication (19 new tests)
- Docker deployment (Dockerfile, docker-compose, .dockerignore)
- Doc hygiene (PLANNING.md numbering, PRODUCTION_CHECKLIST.md migration 004)
- **Call brief ↔ outcome linkage (19 new tests)**:
  - `migrations/005_add_call_briefs.sql` — call_briefs table + call_brief_id FK on call_outcomes
  - `CallBriefResponse.brief_id` — briefs now have a persistent UUID
  - `POST /api/agents/call-brief` — auto-saves brief to DB, returns brief_id
  - `CallOutcomeCreate/Response.call_brief_id` — link outcomes to their prep brief
  - `GET /api/call-outcomes/brief-effectiveness` — conversion rates by brief quality, objection prediction accuracy
  - SupabaseClient: save_call_brief, get_call_brief, get_briefs_with_outcomes

## Recent Commits
- `c12cf9a` feat: JWT auth + Docker deployment (19 tests)
- `c905964` docs: Update project docs for call outcome tracking sprint
- `72362e8` feat: Implement Call Outcome Tracking (47 tests)
- `148cc4b` feat: Implement Call Prep Brief + Ready-to-Dial endpoints (48 tests)
- `ec58678` test: Add integration tests for gap analysis features (65 tests)

## Key Features Implemented
- **JWT API Authentication**: Bearer token auth on all endpoints, token issuance via API key exchange
- **5 LangGraph Agents**: Lead Research, Script Selection, Competitor Intel, Email Personalization, Qualification
- **Call Brief Assembler**: Composition layer — runs 3 agents in parallel, enriches with playbook data, **now persisted to DB**
- **Call Outcome Tracking**: Log call outcomes, auto follow-ups, lead status updates, daily stats, HubSpot sync, **linked to call briefs**
- **Brief Effectiveness Analytics**: Conversion rates by brief quality, objection prediction accuracy
- **Master Orchestrator**: Parallel agent execution with review gates using Command pattern
- **Tiered Apollo Enrichment**: Phase 1 (1 credit) + Phase 2 (8 credits for ATL only) = ~67% savings
- **Observability**: Credits, rate-limits, batch monitoring, LangSmith tracing
- **Streaming**: Token-level SSE streaming for emails and qualification
- **Harvester Sync**: Real-time webhook with auto-qualification
- **Docker Deployment**: Multi-stage Dockerfile with uv, docker-compose with full stack

## Next Sprint Candidates
- Call brief effectiveness scoring (deeper analytics — which scripts lead to meetings)
- Frontend UI (monitoring dashboard, call brief viewer, phone approval)
- Refresh token rotation
- Rate limiting per user

## Blockers
- None

## Tech Stack
Python 3.10+ | FastAPI | Pydantic | Supabase | LangGraph | Apollo | uv | pytest | ruff | mypy (strict) | Docker | PyJWT
