# epiphan-sales-agent

**Branch**: main | **Updated**: 2026-02-05

## Status
Production-ready AI sales assistant with 5 LangGraph agents, Call Brief Assembler (composition layer), Master Orchestrator with parallel execution and review gates, tiered Apollo enrichment, observability endpoints, LangSmith tracing, and real-time Harvester sync. 1017 tests (1012 passed, 5 skipped), 0 mypy errors, 0 ruff lint errors.

## Done (This Session)
- Call Prep Brief + Ready-to-Dial sprint complete (48 new tests):
  - `CallBriefAssembler` composition layer using asyncio.gather (3 agents in parallel)
  - `POST /api/agents/call-brief` — one-page call prep brief with playbook enrichment
  - `GET /api/leads/ready-to-dial` — daily call list with tier/phone filtering
  - 15 Pydantic response models, brief quality scoring, intelligence gap detection
  - Graceful degradation: partial briefs when agents fail
- Integration Testing Sprint complete (65 new tests):
  - `test_checkpointing_encryption.py` (20 tests) - AES-256-GCM encryption verification
  - `test_qualification_edge_cases.py` (21 tests) - Extended thinking triggers on borderline scores
  - `test_middleware_pipeline.py` (24 tests) - ModelCallLimitMiddleware, ModelFallbackMiddleware

## Recent Commits
- `ec58678` test: Add integration tests for gap analysis features (65 tests)
- `77bb333` feat: Implement LangChain/LangGraph gap analysis improvements
- `74007b8` docs: Update project documentation for LangGraph v1.0 implementation
- `d9d29f4` feat: Implement LangGraph v1.0 best practices from documentation research
- `ac94ea0` feat: Complete LangGraph Agent Polish sprint - all 7 phases

## Key Features Implemented
- **5 LangGraph Agents**: Lead Research, Script Selection, Competitor Intel, Email Personalization, Qualification
- **Call Brief Assembler**: Composition layer (NOT a LangGraph agent) — runs 3 agents in parallel via asyncio.gather, enriches with playbook data (objections, discovery questions, competitors, reference stories), extracts phones from 3 sources
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

## Next Sprint: Call Outcome Tracking
- Design call outcome schema (connected, voicemail, no answer, callback, not interested)
- `POST /api/calls/outcome` endpoint
- Cadence management (auto-schedule follow-ups)

## Blockers
- None

## Tech Stack
Python 3.10+ | FastAPI | Pydantic | Supabase | LangGraph | Apollo | uv | pytest | ruff | mypy (strict)
