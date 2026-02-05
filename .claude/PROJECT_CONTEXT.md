# epiphan-sales-agent

**Branch**: main | **Updated**: 2026-02-05

## Status
Production-ready AI sales assistant with 5 LangGraph agents, Master Orchestrator with parallel execution and review gates, tiered Apollo enrichment, observability endpoints, LangSmith tracing, and real-time Harvester sync. 895 tests (890 passed, 5 skipped), 0 mypy errors, 0 ruff lint errors.

## Done (This Session)
- Created `backend/.env.example` documenting all environment variables
- Created `docs/deployment/PRODUCTION_CHECKLIST.md` with full deployment guide
- Verified test suite (890 passed, 5 skipped)
- Verified server startup and endpoint accessibility

## Recent Commits
- `74007b8` docs: Update project documentation for LangGraph v1.0 implementation
- `d9d29f4` feat: Implement LangGraph v1.0 best practices from documentation research
- `ac94ea0` feat: Complete LangGraph Agent Polish sprint - all 7 phases
- `7c59014` feat: Add Master Orchestrator Agent with parallel execution and review gates
- `d7a548b` docs: Update project documentation to sync with codebase state

## Key Features Implemented
- **5 LangGraph Agents**: Lead Research, Script Selection, Competitor Intel, Email Personalization, Qualification
- **Master Orchestrator**: Parallel agent execution with review gates using Command pattern
- **LangGraph v1.0 Enhancements**:
  - Anthropic prompt caching (~10x speedup)
  - InMemoryCache for Apollo enrichment (saves 8 credits/duplicate)
  - RetryPolicy with exponential backoff
  - Extended thinking client for complex qualification
  - Time-travel debug endpoint
- **Tiered Apollo Enrichment**: Phase 1 (1 credit) + Phase 2 (8 credits for ATL only) = ~67% savings
- **Observability**: `/api/monitoring/credits`, `/api/monitoring/rate-limits`, `/api/monitoring/batches/{id}`
- **LangSmith Tracing**: `@trace_agent` decorator with execution metrics
- **Harvester Sync**: `POST /api/webhooks/harvester/lead-push` with auto-qualification
- **Phone Webhook**: Apollo async phone delivery with local storage + HubSpot approval workflow
- **Streaming**: Token-level SSE streaming for emails and qualification

## Blockers
- None

## Tech Stack
Python 3.10+ | FastAPI | Pydantic | Supabase | LangGraph | Apollo | uv | pytest | ruff | mypy (strict)
