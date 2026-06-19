# Project Context: epiphan-sales-agent

**Updated:** 2026-06-19 (Session 5)
**Branch:** main
**Tech Stack:** Python 3.12, FastAPI, LangGraph 1.1.2, Supabase, Railway

---

## Done (2026-06-19) — Session 5: Pivot to Nooks Autopilot (Claude+MCP skill)

**Major direction change.** Tim's autonomous BDR/SDR team now runs as a **scheduled Claude skill
on the MCP stack** (Epiphan AI + HubSpot + Nooks + Apollo/Clay), NOT this FastAPI backend. The
Session-4 backend pipeline is **superseded** for the live motion (its run_id/add_task bugs are
non-blocking — decide later whether to fix or retire).

- **Built `nooks-autopilot` skill** (`~/.claude/skills/nooks-autopilot/`): find → qualify → route →
  enroll into a **Nooks** sequence → monitor → hand off a warm/replied lead. Shadow-first.
  Per-rep agents (Tim/Edgar/Vasil/Nyasha), **one owner per lead** (`sdr_owner`), **one SDR per
  account** multi-thread guard, always-on **DA audit** (no live Lex/Phil deals, no 12-mo buyers).
- **Full shadow pass** on 50 candidates across 5 HubSpot `[AI]` lists — guards verified (double-dial,
  customers, AE-owned, gate-fix); published per-rep dial-list Artifact. Zero writes.
- **New private GitHub repo `ScientiaCapital/epiphan-sdr-skills`** (3 commits, 29 files): 13
  Tim-authored skills + 6 process playbooks + 2 conversion-intel docs. PII-scanned, gitleaks-clean.
- **Memory saved** (3 files): project_nooks_autopilot, reference_nooks_autopilot_ids, feedback_nooks_autopilot_guards.

Backend repo: **0 commits today** (work was skills + repo + memory).

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

## Tomorrow (nooks-autopilot → live)

Before flipping `SHADOW_MODE=false`, close 3 build-time items (all noted in the skill):
1. **Map non-standard HubSpot lifecycle-stage IDs** (e.g. `1028712882`, `970063423`) so the DA/in-deal guard is exact — don't enroll someone mid-deal.
2. **Division of labor vs the existing Epiphan AI prospecting agent** (it also sets `epiphan_ai_status`/enrolls via Apollo) — define hands-off so no lead is double-worked.
3. **Nyasha's Nooks mailbox** — get it connected so her auto-email touches fire (currently call/LinkedIn-only).
Then: live smoke test — enroll 1 test contact (verify Nooks `listSequenceStates` active + `[Epiphan AI] Enrolled`), reply from test inbox → monitor halts + `[Epiphan AI] Replied` + warm task.

Tomorrow: nooks-autopilot live-readiness (lifecycle-stage map + agent division-of-labor) | sonnet | Est: short | Note: backend pipeline superseded — decide fix-or-retire separately

---

_Updated each session by END DAY workflow._
