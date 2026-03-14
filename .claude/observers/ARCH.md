# Observer: Architecture Report

**Date:** 2026-03-14
**Project:** epiphan-sales-agent
**Session:** session-3

---

## Blockers (stop work immediately)

None.

---

## Risks (address this sprint)

1. **[R3] Supabase service_key for all ops** — All DB operations use service_key (bypasses RLS). Should use anon_key for reads when RLS policies are added. **Impact: MEDIUM, Effort: MEDIUM**

---

## Smells (log to backlog)

1. **[S1] In-memory rate limiting** — slowapi doesn't use Redis. Limits reset on deploy.
2. **[S2] In-memory WebSocket sessions** — 1-worker constraint. Needs Redis session store.
3. **[S3] Healthcheck hardcoded port** — Dockerfile HEALTHCHECK uses 8001, not `$API_PORT`.
4. **[S4] `.env.example` has real-looking keys** — Pre-existing, should scrub.

---

## Session 3 Architecture Notes

- **Coaching agent follows established agent pattern** — 4-node StateGraph, same structure as competitor_intel.py. Module-level singleton. No new architectural patterns introduced.
- **Call brief 5th parallel call** — `_safe_coaching_context()` uses Supabase client directly (lazy import). Follows `_safe_*()` pattern. Graceful degradation to None.
- **LLM routing change** — Cerebras removed, OpenRouter fast tier added. No architectural impact — same `ChatOpenAI` adapter, same `get_model()` interface.

---

## Resolved (from previous sessions)

| Finding | Resolved | Commit |
|---------|----------|--------|
| [R1] JWT secret = API key | 2026-02-22 | `49b5f95` |
| [R2] No startup validation | 2026-02-22 | `49b5f95` |
| Observer path mismatch | 2026-03-14 | (this session) |
