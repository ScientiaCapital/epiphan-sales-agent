# Observer: Architecture Report

**Date:** 2026-03-22
**Project:** epiphan-sales-agent
**Session:** session-4

---

## Blockers (stop work immediately)

None.

---

## Risks (address this sprint)

1. **[R3] Supabase service_key for all ops** — Unchanged from session 3.
2. **[R4] APScheduler in single-worker process** — Cron scheduler runs inside the uvicorn worker. Fine for UVICORN_WORKERS=1 but will double-fire if workers increase. Redis-backed scheduler needed before scaling. **Impact: LOW, Effort: MEDIUM**

---

## Smells (log to backlog)

1. **[S1] In-memory rate limiting** — Unchanged.
2. **[S2] In-memory WebSocket sessions** — Unchanged.
3. **[S3] Healthcheck hardcoded port** — Unchanged.
4. **[S4] `.env.example` has real-looking keys** — Unchanged.
5. **[S5] Background task via asyncio.ensure_future** — `trigger_run()` route uses fire-and-forget pattern. Fine for MVP, consider task queue for production reliability.

---

## Session 4 Architecture Notes

- **Autonomous pipeline is a composition layer, NOT a LangGraph agent** — Same pattern as CallBriefAssembler. Uses `asyncio.gather()` with `_safe_*()` wrappers. Intentional: LangGraph checkpointing overhead unnecessary for batch processing.
- **Self-learning via approval_patterns table** — Aggregated approval/rejection stats by industry, title, persona. Activates after 50+ decisions.
- **Challenger Sale + NSTTD prompt** — Email drafting uses specialized system prompt encoding sales methodology. Structured JSON output.
- **13 new API endpoints** under `/api/autonomous/` — run, queue CRUD, approve/reject, bulk actions, patterns, stats.
- **Supabase migration 003** — 3 tables (autonomous_runs, outreach_queue, approval_patterns) with indexes and dedup constraint.

---

## Resolved (from previous sessions)

| Finding | Resolved | Commit |
|---------|----------|--------|
| [R1] JWT secret = API key | 2026-02-22 | `49b5f95` |
| [R2] No startup validation | 2026-02-22 | `49b5f95` |
| Observer path mismatch | 2026-03-14 | `5912669` |
