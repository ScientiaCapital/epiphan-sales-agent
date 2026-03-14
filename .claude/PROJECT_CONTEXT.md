# Project Context: epiphan-sales-agent

**Updated:** 2026-03-14
**Branch:** main
**Tech Stack:** Python 3.12, FastAPI, LangGraph 1.1.2, Supabase, Railway

---

## Production Environment
- **API**: https://epiphan-api-production.up.railway.app
- **Supabase**: ulvjeeictfhfbzivexnf (us-east-1)
- **Railway project**: 8a6ddb6c-3f37-4db1-9c61-4585ad66210e

## Recent Commits

```
ef7fafe feat: structured output for competitor/script agents + coaching session state
cb5fc64 refactor: replace manual LLM parsing with with_structured_output()
9985931 feat: port Souffleur coaching intelligence layer (core types)
```

## Working Tree Status

```
Clean (all committed and pushed)
```

## Done (This Session — 2026-03-14)

### Session 1: Souffleur Intelligence Port
- Ported coaching intelligence layer from Rust: MEDDIC, DISC, Call Stage FSM, product catalog, context builder, state machine + 6 invariant rules
- Bumped LangChain ecosystem deps (langgraph 1.1.2, langsmith 0.7.17)
- 2x /simplify passes: 10 issues fixed
- Full codebase audit (8/10) + Souffleur architecture review

### Session 2: Structured Output + Coaching Wiring
- **All 4 agents now use `with_structured_output()`** — zero manual LLM parsing remaining
  - Email agent: `EmailResponse` model
  - Qualification agent: `TierDecision` model
  - Competitor intel: `CompetitorResponseOutput` model (with fallback error handling)
  - Script selection: `ScriptResponseOutput` model
- **Coaching fields wired into CallSessionState**: call_stage, accumulated_state, audience, coaching_history (typed as CoachingResponse), topics_discussed, turn_count
- **SessionStateResponse** now returns live coaching state (call_stage, meddic_score, turn_count)
- DA agent review: 2 HIGH + 4 MEDIUM findings resolved
- 1465 tests, 0 mypy errors, 0 ruff errors

## Tomorrow

1. **Replace Cerebras with OpenRouter** — dynamic model routing via orchestrator for best tool use support per task (Tim's decision: no more Cerebras)
2. **Coaching LangGraph agent (7th agent)** — uses coaching schemas + state machine + context builder, Claude-powered
3. **Call brief coaching context** — wire coaching into call brief assembler as 5th parallel call

---

_Updated each session by END DAY workflow._
