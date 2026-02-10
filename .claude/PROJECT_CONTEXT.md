# epiphan-sales-agent

**Branch**: main | **Updated**: 2026-02-09

## Status
Production-ready AI sales assistant with 5 LangGraph agents, Call Brief Assembler with persistence, Call Outcome Tracking with brief linkage, Brief Effectiveness Deep Analytics, Clay.com fallback enrichment, Voice AI Call Session integration (WebSocket + REST), Master Orchestrator with parallel execution and review gates, tiered Apollo enrichment, per-user rate limiting (slowapi), WebSocket session ownership, observability endpoints, LangSmith tracing, and real-time Harvester sync. JWT API authentication and Docker deployment. 1334 tests (1334 passed, 5 skipped), 0 mypy errors, 0 ruff lint errors.

## Today's Focus
Completed: WebSocket session ownership hardening, per-user rate limiting, devil's advocate agent, housekeeping.

## Done (This Session)
- WebSocket session ownership: IDOR prevention with `user_id` binding on sessions (13 tests)
- Per-user rate limiting: JWT-based slowapi key function, decorators on all LLM endpoints (12 tests)
- Devil's advocate agent: `.claude/agents/devils-advocate.md` (read-only reviewer)
- Housekeeping: Worktree cleanup, doc updates, cost tracking init, ruff per-file-ignores

## Recent Commits
- `243800c` fix: Harden WebSocket session ownership + add per-user rate limiting (25 tests)
- `3105e27` feat: Wire orphaned memory modules into production consumers (51 tests)
- `22bf5f5` chore: Trim project docs + fix ruff lint error
- `ffd68ff` fix: Secure phone endpoints + fix tier score aggregation bug (5 tests)
- `52820dc` feat: Add Voice AI call session integration — WebSocket + REST (47 tests)

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
- Frontend UI (monitoring dashboard, call brief viewer, phone approval)
- Refresh token rotation
- Integration test suite with real Supabase

## Blockers
- None

## Tech Stack
Python 3.10+ | FastAPI | Pydantic | Supabase | LangGraph | Apollo | Clay | uv | pytest | ruff | mypy (strict) | Docker | PyJWT
