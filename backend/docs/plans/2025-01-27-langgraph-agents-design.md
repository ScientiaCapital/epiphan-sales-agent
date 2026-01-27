# LangGraph Sales Intelligence Agents - Design Document

**Date:** 2025-01-27
**Status:** Approved

## Overview

Four LangGraph agents to support BDR workflows:
1. **Script Selection Agent** - Personalize warm/cold call scripts
2. **Lead Research Agent** - Enrich leads with external data
3. **Email Personalization Agent** - Generate sequence emails
4. **Competitor Intelligence Agent** - Real-time battlecard responses

### Use Cases
- Pre-call preparation (research briefs, personalized scripts)
- Automated outreach generation (batch emails)
- Real-time call assistance (competitor responses)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LANGGRAPH ORCHESTRATOR                        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────┬───────────┴───────────┬───────────────┐
        ▼               ▼                       ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ ┌──────────────┐
│   SCRIPT     │ │    LEAD      │ │      EMAIL       │ │  COMPETITOR  │
│  SELECTION   │ │  RESEARCH    │ │ PERSONALIZATION  │ │ INTELLIGENCE │
│    AGENT     │ │    AGENT     │ │      AGENT       │ │    AGENT     │
├──────────────┤ ├──────────────┤ ├──────────────────┤ ├──────────────┤
│ Claude       │ │ Claude       │ │ Claude           │ │ Cerebras/    │
│ (quality)    │ │ (synthesis)  │ │ (personalization)│ │ DeepSeek     │
└──────────────┘ └──────────────┘ └──────────────────┘ └──────────────┘
```

---

## LLM Routing

| Agent | Model | Reason |
|-------|-------|--------|
| Script Selection | Claude Sonnet | Quality for BDR-facing output |
| Lead Research | Claude Sonnet | Complex multi-source synthesis |
| Email Personalization | Claude Sonnet | Tone critical for prospects |
| Competitor Intelligence | Cerebras/DeepSeek | Speed (<2s), simpler task |

**Fallback:** OpenRouter for all agents if primary fails.

---

## Agent State Definitions

### Script Selection Agent
```python
class ScriptSelectionState(TypedDict):
    lead: Lead
    persona_match: str | None
    trigger: str | None
    call_type: str                 # "warm" | "cold"
    base_script: dict | None
    lead_context: str | None
    personalized_script: str
    talking_points: list[str]
    objection_responses: list[dict]
```
**Flow:** `load_script → extract_context → personalize → format_output`

### Lead Research Agent
```python
class LeadResearchState(TypedDict):
    lead: Lead
    research_depth: str            # "quick" | "deep"
    apollo_data: dict | None
    clearbit_data: dict | None
    news_articles: list[dict]
    linkedin_context: str | None
    research_brief: ResearchBrief
    talking_points: list[str]
    risk_factors: list[str]
```
**Flow:** `enrich_apis (parallel) → scrape_web → synthesize → format_brief`

### Email Personalization Agent
```python
class EmailPersonalizationState(TypedDict):
    lead: Lead
    research_brief: ResearchBrief | None
    persona: PersonaProfile
    sequence_step: int             # 1-4
    email_type: str
    pain_points: list[str]
    personalization_hooks: list[str]
    subject_line: str
    email_body: str
    follow_up_note: str | None
```
**Flow:** `gather_context → select_template → personalize → generate_subject`

### Competitor Intelligence Agent
```python
class CompetitorIntelState(TypedDict):
    competitor_name: str
    context: str
    query_type: str                # "claim" | "objection" | "comparison"
    battlecard: CompetitorBattlecard | None
    relevant_differentiators: list[dict]
    response: str
    proof_points: list[str]
    follow_up_question: str | None
```
**Flow:** `lookup_battlecard → match_context → generate_response`

---

## Tools by Agent

| Agent | Tools |
|-------|-------|
| Script Selection | `get_warm_script`, `get_cold_script`, `get_persona_profile` |
| Lead Research | `apollo_enrich`, `clearbit_lookup`, `scrape_linkedin`, `fetch_news`, `scrape_website` |
| Email Personalization | `get_email_template`, `get_persona_pain_points`, `get_success_stories` |
| Competitor Intelligence | `get_battlecard`, `search_differentiators`, `get_claim_responses` |

---

## API Endpoints

### Script Selection
```
POST /api/agents/scripts/personalize
{
    "lead_id": "uuid",
    "call_type": "warm",
    "trigger": "demo_request"
}
→ { "personalized_script": "...", "talking_points": [...], "objection_responses": [...] }
```

### Lead Research
```
POST /api/agents/research/brief
{
    "lead_id": "uuid",
    "depth": "deep"
}
→ { "company_overview": "...", "talking_points": [...], "risk_factors": [...] }
```

### Email Personalization
```
POST /api/agents/email/generate
{
    "lead_id": "uuid",
    "sequence_step": 1,
    "email_type": "pattern_interrupt",
    "include_research": true
}
→ { "subject_line": "...", "email_body": "...", "bdr_notes": "..." }
```

### Batch Email Generation
```
POST /api/agents/email/batch
{ "lead_ids": [...], "sequence_step": 1, "email_type": "pattern_interrupt" }
→ { "task_id": "batch-uuid", "estimated_time_seconds": 120 }

GET /api/agents/email/batch/{task_id}
→ { "status": "completed", "results": [...] }
```

### Competitor Intelligence
```
POST /api/agents/competitor/respond
{
    "competitor": "blackmagic",
    "context": "They said ATEM is cheaper",
    "query_type": "claim"
}
→ { "response": "...", "proof_points": [...], "follow_up": "..." }
```

---

## File Structure

```
backend/app/
├── services/
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── clients.py              # LLMRouter
│   │   └── prompts.py              # Prompt templates
│   │
│   ├── langgraph/
│   │   ├── agents/
│   │   │   ├── script_selection.py
│   │   │   ├── lead_research.py
│   │   │   ├── email_personalization.py
│   │   │   └── competitor_intel.py
│   │   │
│   │   ├── tools/
│   │   │   ├── script_tools.py
│   │   │   ├── research_tools.py
│   │   │   ├── email_tools.py
│   │   │   └── competitor_tools.py
│   │   │
│   │   └── states.py
│   │
│   └── enrichment/
│       ├── apollo.py
│       ├── clearbit.py
│       └── scraper.py
│
├── api/routes/agents.py
│
└── tests/unit/
    ├── test_script_selection_agent.py
    ├── test_lead_research_agent.py
    ├── test_email_personalization_agent.py
    └── test_competitor_intel_agent.py
```

---

## Implementation Order

| Phase | Component | Tests |
|-------|-----------|-------|
| 1 | LLM clients + routing | 5 |
| 2 | Competitor Intel Agent | 10 |
| 3 | Script Selection Agent | 12 |
| 4 | Enrichment clients | 8 |
| 5 | Lead Research Agent | 15 |
| 6 | Email Personalization Agent | 12 |
| 7 | API endpoints + batch | 10 |

**Total: ~72 new tests**

---

## Data Sources for Research

**APIs (structured data):**
- Apollo.io - Contact + company enrichment
- Clearbit - Firmographics
- Hunter.io - Email verification

**Web scraping (context):**
- LinkedIn - Role, tenure, recent posts
- Company websites - About, news, leadership
- News APIs - Recent company mentions, funding
