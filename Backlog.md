# Product Backlog

## Priority 1 - Production Hardening (from observer/devil's advocate)
- [x] ~~**[R1] Separate API key from JWT secret**~~ — DONE 2026-02-22 (commit `49b5f95`)
- [x] ~~**[R2] Startup validation for critical secrets**~~ — DONE 2026-02-22 (commit `49b5f95`)
- [ ] **[R3] Call `setup_checkpoint_tables()` at startup** — LangGraph tables exist via migration but helper not invoked. Falls back to MemorySaver silently. Impact: MEDIUM, Effort: SMALL
- [x] ~~**[W1] Fix mypy errors**~~ — DONE 2026-02-22, all 55 errors resolved (commit `49b5f95`)
- [ ] **[W4] Scrub `.env.example` of real-looking keys** — `sb_secret_*`, `sb_publishable_*` from old commits. Consider `git filter-repo`. Impact: LOW, Effort: MEDIUM

## Priority 2 - Frontend
- [ ] Build monitoring dashboard UI
- [ ] Phone approval interface
- [ ] Call brief viewer / daily call list UI
- [ ] Brief effectiveness analytics dashboard
- [ ] Batch status viewer

## Priority 3 - Enhanced Features
- [ ] Supabase persistence for batch tracking (currently in-memory)
- [ ] Historical credit usage charts
- [ ] Webhook retry logic for failures
- [ ] Redis-backed WebSocket sessions (enables multi-worker scaling)
- [ ] Redis-backed rate limiting (slowapi, enables multi-worker)
- [ ] Supabase RLS with anon_key for read operations [R3 from observer]
- [ ] Railway restart policy (`restartPolicyType = "ON_FAILURE"`, maxRetries: 3)

## Tech Debt
- [ ] Fix integration test fixture (`_supabase_client`)
- [ ] Upgrade markdownify 0.13.1 → 0.14.1 (CVE-2025-46656, CVSS 3.1 LOW)
- [ ] Refresh token rotation (currently single 15-min JWT, no revocation)
- [ ] Dockerfile HEALTHCHECK should use `${API_PORT:-8001}` not hardcoded 8001
- [ ] `.env.production.example` pooler docs: session-mode (5432) for app, direct (5432) for DDL only

---

Completed items archived in [CHANGELOG.md](CHANGELOG.md).
