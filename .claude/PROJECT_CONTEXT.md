# epiphan-sales-agent

**Branch**: main | **Updated**: 2026-02-07

## Status
Production-ready AI sales assistant with 5 LangGraph agents, Call Brief Assembler with persistence, Call Outcome Tracking with brief linkage, Brief Effectiveness Deep Analytics, Clay.com fallback enrichment, Voice AI Call Session integration (WebSocket + REST), Master Orchestrator with parallel execution and review gates, tiered Apollo enrichment, observability endpoints, LangSmith tracing, and real-time Harvester sync. JWT API authentication and Docker deployment. 1258 tests (1258 passed, 5 skipped), 0 mypy errors, 0 ruff lint errors.

## Today's Focus
Security fixes + bug fixes from previous session handoff.

## Done (This Session)
- **Security fix: Phone endpoint authentication (5 new tests)**:
  - Added `Depends(require_auth)` to `/phones/pending` and `/phones/approve` — were accidentally unauthenticated on the HMAC-only webhook router
  - 4 auth tests: 401 without token, 200 with token, webhook still unauthenticated
- **Bug fix: Tier score aggregation**:
  - Moved tier score extraction outside `for outcome in outcomes` loop — was duplicating scores for briefs with multiple outcomes
  - 1 regression test: verifies avg_score = mean of per-brief scores, not inflated by outcome count
- End-of-day lockdown: security sweep (CLEAN), quality gate (PASS), docs updated

## Recent Commits
- `a4831f6` feat: Add Clay.com webhook-based enrichment (49 tests)
- `2b8a5d1` feat: Add brief effectiveness deep analytics (55 tests)
- `f52bd8f` feat: Link call briefs to outcomes for closed-loop feedback (19 tests)
- `c12cf9a` feat: Add JWT API authentication and Docker deployment (19 tests)
- `c905964` docs: Update project docs for call outcome tracking sprint

## Key Features Implemented
- **Voice AI Call Session**: WebSocket + REST endpoints for live call support — call briefs, competitor battlecards, objection handling, outcome logging
- **Clay.com Fallback Enrichment**: Webhook-based enrichment with 75+ provider waterfall, feature-flagged
- **Brief Effectiveness Deep Analytics**: Persona deep dives, script matrix, tier analytics
- **JWT API Authentication**: Bearer token auth on all endpoints, token issuance via API key exchange
- **5 LangGraph Agents**: Lead Research, Script Selection, Competitor Intel, Email Personalization, Qualification
- **Call Brief Assembler**: Composition layer — runs 3 agents in parallel, enriches with playbook data, persisted to DB
- **Call Outcome Tracking**: Log call outcomes, auto follow-ups, lead status updates, daily stats, HubSpot sync, linked to call briefs
- **Master Orchestrator**: Parallel agent execution with review gates using Command pattern
- **Tiered Apollo Enrichment**: Phase 1 (1 credit) + Phase 2 (8 credits for ATL only) = ~67% savings
- **Observability**: Credits, rate-limits, batch monitoring, LangSmith tracing
- **Streaming**: Token-level SSE streaming for emails and qualification
- **Harvester Sync**: Real-time webhook with auto-qualification
- **Docker Deployment**: Multi-stage Dockerfile with uv, docker-compose with full stack

## Next Sprint Candidates
- WebSocket session ownership hardening (user_id field for multi-user)
- Frontend UI (monitoring dashboard, call brief viewer, phone approval)
- Refresh token rotation
- Rate limiting per user

## Blockers
- None

## Tech Stack
Python 3.10+ | FastAPI | Pydantic | Supabase | LangGraph | Apollo | Clay | uv | pytest | ruff | mypy (strict) | Docker | PyJWT
