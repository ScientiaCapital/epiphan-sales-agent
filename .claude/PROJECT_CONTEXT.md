# Project Context: epiphan-sales-agent

**Updated:** 2026-03-14 (Session 3)
**Branch:** main
**Tech Stack:** Python 3.12, FastAPI, LangGraph 1.1.2, Supabase, Railway

---

## Production Environment
- **API**: https://epiphan-api-production.up.railway.app
- **Supabase**: ulvjeeictfhfbzivexnf (us-east-1)
- **Railway project**: 8a6ddb6c-3f37-4db1-9c61-4585ad66210e

## Recent Commits

```
5912669 fix: observer path mismatch — agents now write to .claude/observers/ subdirectory
5d61cf6 feat: coaching LangGraph agent + OpenRouter fast tier + call brief coaching context
1dd03bf docs: update PROJECT_CONTEXT.md with session 2 work + tomorrow handoff
ef7fafe feat: structured output for competitor/script agents + coaching session state
```

## Working Tree Status

```
Clean (all committed and pushed)
```

## Done (2026-03-14)

### Session 1: Souffleur Intelligence Port
- Ported coaching intelligence layer from Rust: MEDDIC, DISC, Call Stage FSM, product catalog, context builder, state machine + 6 invariant rules
- Bumped LangChain ecosystem deps (langgraph 1.1.2, langsmith 0.7.17)
- 2x /simplify passes: 10 issues fixed
- Full codebase audit (8/10) + Souffleur architecture review

### Session 2: Structured Output + Coaching Wiring
- All 4 agents use `with_structured_output()` — zero manual LLM parsing
- Coaching fields wired into CallSessionState
- SessionStateResponse returns live coaching state
- DA agent review: 2 HIGH + 4 MEDIUM findings resolved
- 1465 tests, 0 mypy errors, 0 ruff errors

### Session 3: OpenRouter + Coaching Agent + Call Brief Integration
- **Cerebras → OpenRouter fast tier** (DeepSeek V3 via OpenRouter) — reliable structured output for fast tasks
- **Coaching LangGraph Agent (7th)** — 4-node graph: build_context → analyze_turn → generate_coaching → validate_state. Uses existing coaching intelligence layer with Claude structured output. 13 tests.
- **Call brief coaching context** — 5th parallel call via `_safe_coaching_context()`, fetches cross-call history from Supabase, enriches objection prep with unresolved prior objections
- **Observer infra fix** — path mismatch between agent definitions (root) and commands (subdirectory) meant reports were never visible. Unified to `.claude/observers/`
- 1478 tests, 0 mypy errors, 0 ruff errors

## 7 Agents Now Complete

1. Lead Research Agent — Apollo + web scraping enrichment
2. Script Selection Agent — persona-specific warm call scripts
3. Competitor Intelligence Agent — battlecard responses
4. Email Personalization Agent — personalized outreach
5. Qualification Agent — 5-dimension ICP scoring
6. Call Brief Assembler — parallel research + qualify + script + coaching
7. **Coaching Agent** — real-time MEDDIC/DISC coaching during calls

## Tomorrow

1. **Wire coaching agent into CallSessionManager** — connect coaching agent to WebSocket session for real-time coaching during live calls. On each `process_transcript` call, invoke coaching agent and push response over WebSocket.
2. **End-to-end coaching test** — integration test: WebSocket connect → send transcript → receive coaching response with MEDDIC/DISC updates
3. **Deploy to Railway** — new agent has no new deps, should be clean deploy. Verify OpenRouter env var is set.

Tomorrow: Wire coaching into WebSocket session via /build | sonnet | Est: medium | Observer notes: no blockers, backlog items S1-S4 are low priority

---

_Updated each session by END DAY workflow._
