# Changelog

Completed work archived from Backlog.md. Most recent first.

---

## Security Hardening (2026-02-07)
- [x] Phone endpoint auth fix (`/phones/pending`, `/phones/approve`)
- [x] Tier score aggregation bug fix
- [x] Context cleanup audit (MCP, skills, CLAUDE.md)
- [x] Full security sweep: 0 secrets, 0 CVEs
- [x] 5 new tests

## Voice AI Call Session (2026-02-06)
- [x] WebSocket (`/ws/call-session`) + REST fallback endpoints
- [x] Real-time competitor battlecards + objection handling during calls
- [x] Session lifecycle: brief → call support → outcome logging
- [x] 47 new tests

## Clay.com Enrichment Integration (2026-02-06)
- [x] ClayClient with webhook-based enrichment (75+ provider waterfall)
- [x] Feature-flagged (`CLAY_ENABLED=false`), HMAC verification
- [x] Phone priority: Apollo > Harvester > Clay
- [x] Migration `006_add_clay_enrichment.sql`
- [x] 49 new tests

## Brief Effectiveness Deep Analytics (2026-02-06)
- [x] 10 new Pydantic models (ConversionFunnel, PhoneTypeImpact, TierAnalytics, etc.)
- [x] Enhanced `GET /brief-effectiveness` — persona summaries, tier analytics, phone impact, overall funnel
- [x] `GET /brief-effectiveness/persona/{persona_id}` — per-trigger deep dive
- [x] `GET /brief-effectiveness/scripts` — persona x trigger matrix ranked by meeting rate
- [x] 6 private service helpers for reusable analytics computation
- [x] 55 new tests (11 test classes)

## Call Brief / Outcome Linkage (2026-02-06)
- [x] Migration `005_add_call_briefs.sql` — call_briefs table + call_brief_id FK
- [x] Brief persistence + outcome linkage
- [x] Basic effectiveness analytics endpoint
- [x] 19 new tests

## JWT API Authentication + Docker (2026-02-06)
- [x] JWT middleware (15-min tokens, constant-time key comparison)
- [x] `POST /api/auth/token` endpoint
- [x] Bearer token required on all non-public endpoints
- [x] Multi-stage Docker build (python:3.12-slim, non-root, healthcheck)
- [x] 19 new tests

## Call Outcome Tracking (2026-02-05)
- [x] Migration `004_add_call_outcomes.sql` — new table with 5 indexes
- [x] 7 API endpoints: log, batch, stats, range, follow-ups, history, HubSpot sync
- [x] CallOutcomeService with auto follow-up rules + lead status updates
- [x] 8 new Supabase CRUD methods
- [x] 47 new tests (30 API + 17 service)

## Call Prep Brief + Ready-to-Dial (2026-02-05)
- [x] CallBriefAssembler composition layer (asyncio.gather, 3 agents in parallel)
- [x] 15 Pydantic response models (PhoneInfo, ContactInfo, CompanySnapshot, etc.)
- [x] `POST /api/agents/call-brief` endpoint with @trace_agent
- [x] `GET /api/leads/ready-to-dial` endpoint with tier/phone filtering
- [x] Playbook enrichment (objections, discovery, competitors, reference stories)
- [x] Brief quality scoring + intelligence gap detection
- [x] 48 new tests (30 assembler + 11 API + 8 ready-to-dial)

## Integration Testing Sprint (2026-02-05)
- [x] AES encryption roundtrip tests (20 tests)
- [x] Extended thinking edge case tests (21 tests)
- [x] Middleware pipeline integration tests (24 tests)

## LangGraph v1.0 Best Practices (2026-02-05)
- [x] Anthropic prompt caching header (~10x speedup)
- [x] InMemoryCache for Apollo enrichment
- [x] RetryPolicy with exponential backoff
- [x] Command pattern for routing
- [x] Input/Output schemas for cleaner API
- [x] Extended thinking client
- [x] Time-travel debug endpoint

## LangGraph Agent Polish Sprint (2026-02-05)
- [x] Master Orchestrator with parallel execution
- [x] Review gates for quality control
- [x] MessageTrimmer for memory management
- [x] SemanticMemory for pattern learning
- [x] Middleware layer (PII, rate limit, model selection)
- [x] LangSmith observability/tracing
- [x] Token-level streaming endpoints

## Code Quality
- [x] Run `ruff check . --fix` - 0 lint errors
- [x] Remove unused imports
- [x] Standardize import style

## API Implementation
- [x] All agent endpoints (research, scripts, competitors, emails, qualify)
- [x] Lead management endpoints (ingest, sync, score, prioritized)
- [x] Monitoring endpoints (credits, rate-limits, batches)
- [x] Webhook endpoints (Apollo phone, Harvester push)

## CRM Integration
- [x] HubSpot sync service
- [x] Phone approval workflow
- [x] Audit logging with HubSpot property mapping

## Features
- [x] Tiered Apollo enrichment (67% credit savings)
- [x] ATL decision-maker detection (8 personas, 40 titles)
- [x] Real-time Harvester sync
- [x] Background processing pipeline

## Testing
- [x] 1258 tests (1258 passed, 5 skipped)
- [x] Comprehensive test coverage for all features

## Tech Debt Resolution
- [x] Fix mypy type stub issues (fastapi, hubspot) - strict mode compliant
