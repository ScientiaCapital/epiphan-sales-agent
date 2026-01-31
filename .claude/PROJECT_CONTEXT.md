# epiphan-sales-agent

**Branch**: main | **Updated**: 2026-01-31

## Status
Production-ready AI sales assistant with 5 LangGraph agents, tiered Apollo enrichment, observability endpoints, and real-time Harvester sync. 669 tests passing, 0 mypy errors, 0 ruff lint errors. Clean strict-mode type compliance.

## Done (This Session)
- Resolved all 174 mypy type errors for strict-mode compliance
- Added return type annotations to all `__init__` methods
- Added generic type parameters to SQLAlchemy Mapped[] columns
- Fixed pytest fixture naming for proper injection
- Added mypy overrides for external libraries (hubspot, langgraph, langchain)
- Pushed tech debt fix commit

## Recent Commits
- `44793c0` fix: Resolve all mypy type errors for clean strict-mode compliance
- `1ad4de2` docs: Update project docs after Clearbit removal
- `33d69a1` refactor: Remove Clearbit enrichment provider
- `ae6d025` feat: Add observability endpoints and real-time Harvester sync

## Key Features Implemented
- **5 LangGraph Agents**: Lead Research, Script Selection, Competitor Intel, Email Personalization, Qualification
- **Tiered Apollo Enrichment**: Phase 1 (1 credit) + Phase 2 (8 credits for ATL only) = ~67% savings
- **Observability**: `/api/monitoring/credits`, `/api/monitoring/rate-limits`, `/api/monitoring/batches/{id}`
- **Harvester Sync**: `POST /api/webhooks/harvester/lead-push` with auto-qualification
- **Phone Webhook**: Apollo async phone delivery with local storage + HubSpot approval workflow

## Blockers
- None

## Tech Stack
Python 3.10+ | FastAPI | Pydantic | Supabase | LangGraph | Apollo | uv | pytest | ruff | mypy (strict)
