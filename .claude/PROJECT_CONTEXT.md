# Project Context: epiphan-sales-agent

**Updated:** 2026-03-22 (Session 4)
**Branch:** main
**Tech Stack:** Python 3.12, FastAPI, LangGraph 1.1.2, Supabase, Railway

---

## Production Environment
- **API**: https://epiphan-api-production.up.railway.app
- **Supabase**: ulvjeeictfhfbzivexnf (us-east-1)
- **Railway project**: 8a6ddb6c-3f37-4db1-9c61-4585ad66210e

## Done (2026-03-22)

### Session 4: Autonomous BDR Pipeline (Karpathy autoresearch-inspired)
- **Autonomous nightly pipeline** — Find prospects (Apollo + HubSpot) → Enrich → Score → Draft Challenger Sale emails → Queue for morning review
- **6 new service modules**: runner.py (orchestrator), sourcer.py (Apollo ICP search + HubSpot inbound), dedup.py (cross-source + history), drafter.py (Challenger Sale + NSTTD email generation), learner.py (approval pattern learning), schemas.py (15 Pydantic models)
- **13 API endpoints** under `/api/autonomous/` — trigger runs, review queue, approve/reject, bulk actions, view learned patterns, stats dashboard
- **3 Supabase tables** — autonomous_runs, outreach_queue, approval_patterns (migration applied to cloud)
- **APScheduler** — Cron at 2 AM ET daily, runs inside FastAPI process
- **Self-learning loop** — Records Tim's approval/rejection patterns by industry, title, persona. Activates scoring adjustments after 50+ decisions
- **2,393 lines of new code** (1,771 service + 536 tests + 86 migration)
- **1,466 tests, 0 mypy errors, 0 ruff errors**

### Previous Sessions (1-3)
- Session 1: Souffleur Intelligence Port (coaching layer)
- Session 2: Structured Output + Coaching Wiring
- Session 3: OpenRouter + Coaching Agent + Call Brief Integration

## 8 Agents / Systems Now Complete

1. Lead Research Agent — Apollo + web scraping enrichment
2. Script Selection Agent — persona-specific warm call scripts
3. Competitor Intelligence Agent — battlecard responses
4. Email Personalization Agent — personalized outreach
5. Qualification Agent — 5-dimension ICP scoring
6. Call Brief Assembler — parallel research + qualify + script + coaching
7. Coaching Agent — real-time MEDDIC/DISC coaching during calls
8. **Autonomous BDR Pipeline** — nightly prospect-to-outreach loop with human approval

## Tomorrow

1. **Update .env with production Supabase credentials** — local .env points to 127.0.0.1:54321. Need cloud service_key for local testing of autonomous pipeline.
2. **Deploy to Railway** — new module has 1 new dep (apscheduler). Verify env vars set. Test `POST /api/autonomous/run` on production.
3. **First live run** — Trigger with `{"prospect_limit": 5}` to validate end-to-end: Apollo search → enrichment → qualification → Challenger Sale email drafting → Supabase queue → morning review.
4. **Wire coaching into WebSocket** — Carried from session 3. Connect coaching agent to live call WebSocket.

Tomorrow: Deploy autonomous pipeline to Railway + first live run via /build | sonnet | Est: short | Observer notes: [R4] APScheduler fine for 1 worker, [W1] need cloud Supabase creds in local .env

---

_Updated each session by END DAY workflow._
