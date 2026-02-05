# Product Backlog

## Priority 1 - Production Deployment
- [ ] Add API authentication (API key or JWT)
- [ ] Set up production environment variables
- [ ] Run SQL migrations (001, 002, 003, 004)
- [ ] Configure public webhook URLs
- [ ] Set up monitoring/alerting

## Priority 2 - Frontend
- [ ] Build monitoring dashboard UI
- [ ] Phone approval interface
- [ ] Call brief viewer / daily call list UI
- [ ] Batch status viewer

## Priority 3 - Enhanced Features
- [ ] Supabase persistence for batch tracking (currently in-memory)
- [ ] Historical credit usage charts
- [ ] Webhook retry logic for failures

## Tech Debt
- [ ] Fix integration test fixture (`_supabase_client`)
- [ ] Wire UserMemoryStore into orchestrator (currently orphaned, 414 LOC)
- [ ] Wire ConversationSummarizer for long sessions (currently orphaned, 374 LOC)

---

## Completed

### Call Outcome Tracking (DONE - 2026-02-05)
- [x] Migration `004_add_call_outcomes.sql` — new table with 5 indexes
- [x] 7 API endpoints: log, batch, stats, range, follow-ups, history, HubSpot sync
- [x] CallOutcomeService with auto follow-up rules + lead status updates
- [x] 8 new Supabase CRUD methods
- [x] 47 new tests (30 API + 17 service)

### Call Prep Brief + Ready-to-Dial (DONE - 2026-02-05)
- [x] CallBriefAssembler composition layer (asyncio.gather, 3 agents in parallel)
- [x] 15 Pydantic response models (PhoneInfo, ContactInfo, CompanySnapshot, etc.)
- [x] `POST /api/agents/call-brief` endpoint with @trace_agent
- [x] `GET /api/leads/ready-to-dial` endpoint with tier/phone filtering
- [x] Playbook enrichment (objections, discovery, competitors, reference stories)
- [x] Brief quality scoring + intelligence gap detection
- [x] 48 new tests (30 assembler + 11 API + 8 ready-to-dial)

### Integration Testing Sprint (DONE - 2026-02-05)
- [x] AES encryption roundtrip tests (20 tests)
- [x] Extended thinking edge case tests (21 tests)
- [x] Middleware pipeline integration tests (24 tests)

### LangGraph v1.0 Best Practices (DONE - 2026-02-05)
- [x] Anthropic prompt caching header (~10x speedup)
- [x] InMemoryCache for Apollo enrichment
- [x] RetryPolicy with exponential backoff
- [x] Command pattern for routing
- [x] Input/Output schemas for cleaner API
- [x] Extended thinking client
- [x] Time-travel debug endpoint

### LangGraph Agent Polish Sprint (DONE - 2026-02-05)
- [x] Master Orchestrator with parallel execution
- [x] Review gates for quality control
- [x] MessageTrimmer for memory management
- [x] SemanticMemory for pattern learning
- [x] Middleware layer (PII, rate limit, model selection)
- [x] LangSmith observability/tracing
- [x] Token-level streaming endpoints

### Code Quality (DONE)
- [x] Run `ruff check . --fix` - 0 lint errors
- [x] Remove unused imports
- [x] Standardize import style

### API Implementation (DONE)
- [x] All agent endpoints (research, scripts, competitors, emails, qualify)
- [x] Lead management endpoints (ingest, sync, score, prioritized)
- [x] Monitoring endpoints (credits, rate-limits, batches)
- [x] Webhook endpoints (Apollo phone, Harvester push)

### CRM Integration (DONE)
- [x] HubSpot sync service
- [x] Phone approval workflow
- [x] Audit logging with HubSpot property mapping

### Features (DONE)
- [x] Tiered Apollo enrichment (67% credit savings)
- [x] ATL decision-maker detection (8 personas, 40 titles)
- [x] Real-time Harvester sync
- [x] Background processing pipeline

### Testing (DONE)
- [x] 1069 tests (1064 passed, 5 skipped)
- [x] Comprehensive test coverage for all features

### Tech Debt Resolution (DONE)
- [x] Fix mypy type stub issues (fastapi, hubspot) - strict mode compliant

### Cleanup (DONE)
- [x] Removed Clearbit enrichment (consolidated to Apollo-only)
