# System Overview

Architecture diagram and component relationships for the Epiphan Sales Agent.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL SYSTEMS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Apollo   │  │ Clearbit │  │   Web    │  │  HubSpot │  │Lead Harvester│  │
│  │   API    │  │   API    │  │ Scraper  │  │   CRM    │  │   (30K+/run) │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │             │             │             │                │          │
└───────┼─────────────┼─────────────┼─────────────┼────────────────┼──────────┘
        │             │             │             │                │
        └─────────────┴─────────────┴─────────────┴────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI BACKEND                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         API ROUTES                                   │   │
│   │  /api/agents/qualify    /api/agents/scripts    /api/agents/research │   │
│   │  /api/agents/emails     /api/agents/competitors /api/batch/process  │   │
│   └───────────────────────────────────┬─────────────────────────────────┘   │
│                                       │                                      │
│                                       ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      LANGGRAPH AGENTS                                │   │
│   │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│   │  │   Lead      │ │   Script    │ │ Competitor  │ │   Email     │    │   │
│   │  │  Research   │ │  Selection  │ │   Intel     │ │Personalize  │    │   │
│   │  │   Agent     │ │   Agent     │ │   Agent     │ │   Agent     │    │   │
│   │  │  (Claude)   │ │  (Claude)   │ │ (Cerebras)  │ │  (Claude)   │    │   │
│   │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │   │
│   │                                                                      │   │
│   │  ┌─────────────────────────────────────────────────────────────┐    │   │
│   │  │              QUALIFICATION AGENT (Claude)                    │    │   │
│   │  │  5-Dimension ICP Scoring: Size | Vertical | Use Case |      │    │   │
│   │  │                          Tech Stack | Buying Authority       │    │   │
│   │  └─────────────────────────────────────────────────────────────┘    │   │
│   └───────────────────────────────────┬─────────────────────────────────┘   │
│                                       │                                      │
│                                       ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         DATA LAYER                                   │   │
│   │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────┐     │   │
│   │  │  8 Buyer  │  │   Warm    │  │Competitor │  │  ICP Scoring  │     │   │
│   │  │  Personas │  │  Scripts  │  │Battlecards│  │    Tools      │     │   │
│   │  └───────────┘  └───────────┘  └───────────┘  └───────────────┘     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SUPABASE (PostgreSQL)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│   leads │ contacts │ companies │ activities │ scores │ emails              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### API Layer

| Route | Handler | Purpose |
|-------|---------|---------|
| `/api/agents/qualify` | `agents.py` | Invokes Qualification Agent |
| `/api/agents/scripts` | `agents.py` | Invokes Script Selection Agent |
| `/api/agents/research` | `agents.py` | Invokes Lead Research Agent |
| `/api/agents/competitors` | `agents.py` | Invokes Competitor Intel Agent |
| `/api/agents/emails` | `agents.py` | Invokes Email Personalization Agent |
| `/api/batch/process` | `batch.py` | Parallel batch processing |

### LangGraph Agents

Each agent is a LangGraph graph with:
- **State schema** (TypedDict defining inputs/outputs)
- **Nodes** (Python functions performing work)
- **Edges** (Control flow between nodes)
- **Tools** (Functions the agent can call)

```
┌──────────────────────────────────────────────────────────┐
│                   AGENT GRAPH                             │
│                                                           │
│   START ──▶ classify_input ──▶ process ──▶ format ──▶ END │
│                  │                            │           │
│                  ▼                            ▼           │
│            [Conditional]              [Tool Execution]    │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### Data Layer

| Module | Contents |
|--------|----------|
| `personas.py` | 8 buyer personas with pain points, discovery questions, objections |
| `persona_warm_scripts.py` | ACQP scripts per persona per trigger type |
| `competitors.py` | 13 competitor battlecards with talk tracks |
| `qualification_tools.py` | 5-dimension ICP scoring functions |

### Enrichment Services

| Service | Source | Data Provided |
|---------|--------|---------------|
| `apollo.py` | Apollo.io API | Contact enrichment, company data |
| `clearbit.py` | Clearbit API | Company firmographics, tech stack |
| `scraper.py` | Web scraping | Website content, news |

---

## Data Flow

### Lead Qualification Flow

```
1. Lead data arrives (from API or batch)
           │
           ▼
2. Qualification Agent receives lead
           │
           ▼
3. classify_company_size() ─────────────────┐
4. classify_vertical() ──────────────────────┤
5. classify_use_case() ──────────────────────┼──▶ ICPScoreBreakdown
6. classify_tech_stack() ────────────────────┤
7. classify_buying_authority() ─────────────┘
           │
           ▼
8. calculate_weighted_score() → 0-100 score
           │
           ▼
9. assign_tier() → Tier 1 / Tier 2 / Tier 3 / Not ICP
           │
           ▼
10. determine_next_action() → Recommended action
```

### Script Selection Flow

```
1. Request with persona + trigger + context
           │
           ▼
2. Match persona (8 options)
           │
           ▼
3. Match trigger type (content_download, demo_request, etc.)
           │
           ▼
4. Get PersonaTriggerVariation
           │
           ▼
5. LLM personalizes ACQP script with context
           │
           ▼
6. Return personalized script + objection responses
```

---

## Technology Choices

### Why LangGraph?

| Requirement | LangGraph Solution |
|-------------|-------------------|
| Multi-step workflows | Graph-based execution |
| State management | TypedDict schemas with reducers |
| Conditional routing | Edge functions based on state |
| Tool execution | Native tool binding |
| Persistence | PostgresSaver checkpointing |
| Human-in-the-loop | Interrupt patterns |

### Why Multiple LLM Providers?

| Agent | Model | Reason |
|-------|-------|--------|
| Qualification | Claude | Complex reasoning, nuanced scoring |
| Research | Claude | Multi-source synthesis |
| Scripts | Claude | Nuanced personalization |
| Email | Claude | Brand voice consistency |
| Competitor | Cerebras | Fast response for real-time battlecards |

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    PRODUCTION                            │
│                                                          │
│   ┌──────────────┐     ┌──────────────┐                 │
│   │   uvicorn    │────▶│   FastAPI    │                 │
│   │   (ASGI)     │     │   Backend    │                 │
│   └──────────────┘     └──────┬───────┘                 │
│                               │                          │
│                               ▼                          │
│   ┌──────────────────────────────────────────────────┐  │
│   │              Supabase PostgreSQL                  │  │
│   │   (checkpoints, leads, scores, activities)        │  │
│   └──────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## See Also

- [Agent Architecture](agent-architecture.md) - LangGraph patterns in depth
- [Agents Overview](../agents/overview.md) - Each agent explained
- [Project Ecosystem](../integration/project-ecosystem.md) - How projects connect
