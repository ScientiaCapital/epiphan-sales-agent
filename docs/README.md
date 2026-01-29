# Epiphan Sales Agent Documentation

> AI-powered sales assistant for Epiphan Video BDRs

---

## Quick Navigation

### For Developers

| Document | Description |
|----------|-------------|
| [Quickstart](getting-started/quickstart.md) | Get running in 5 minutes |
| [System Overview](architecture/system-overview.md) | Architecture diagram and components |
| [Agent Architecture](architecture/agent-architecture.md) | LangGraph patterns and state management |
| [Agents Overview](agents/overview.md) | All 5 agents explained |
| [Qualification Agent](agents/qualification-agent.md) | ICP scoring deep-dive |

### For BDRs (Sales Team)

| Document | Description |
|----------|-------------|
| [Playbook Index](sales-playbook/README.md) | BDR-friendly entry point |
| [Personas Overview](sales-playbook/personas-overview.md) | 8 buyer personas with pain points |
| [Scripts Guide](sales-playbook/scripts-guide.md) | ACQP framework and warm call scripts |
| [ICP Qualification](sales-playbook/icp-qualification.md) | What scoring means for prioritization |

### Integration & Reference

| Document | Description |
|----------|-------------|
| [Project Ecosystem](integration/project-ecosystem.md) | How 3 Epiphan projects connect |
| [Lead Harvester Sync](integration/lead-harvester-sync.md) | Data flow from harvester |
| [LangGraph Patterns](reference/langgraph-patterns.md) | Best practices from LangChain docs |
| [Competitive Intel](reference/competitive-intel.md) | Battlecard usage guide |

---

## Project Overview

The Epiphan Sales Agent is an AI-powered assistant that helps BDRs:

1. **Qualify leads** using 5-dimension ICP scoring
2. **Personalize scripts** based on persona and trigger type
3. **Generate emails** with context from research
4. **Access battlecards** for competitor conversations

### Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.10+, FastAPI |
| AI Agents | LangGraph, Claude, Cerebras |
| Database | Supabase (PostgreSQL) |
| Package Manager | uv |
| Testing | pytest |
| Linting | ruff, mypy |

### 5 AI Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| Lead Research | Claude | Enriches leads via Apollo, Clearbit, web scraping |
| Script Selection | Claude | Selects and personalizes ACQP call scripts |
| Competitor Intel | Cerebras | Provides battlecard responses in real-time |
| Email Personalization | Claude | Generates personalized outreach emails |
| Qualification | Claude | Scores leads against 5-dimension ICP criteria |

---

## Related Projects

This project is part of the Epiphan sales ecosystem:

| Project | Purpose | Location |
|---------|---------|----------|
| **epiphan-sales-agent** | AI agents for BDR assistance | This repo |
| **epiphan-bdr-playbook** | Sales intelligence source | `../epiphan-bdr-playbook` |
| **epiphan-lead-harvester** | Lead generation (30K+ leads/run) | `../epiphan-lead-harvester` |

See [Project Ecosystem](integration/project-ecosystem.md) for data flow details.

---

## Quick Commands

```bash
# Run tests
cd backend && uv run pytest tests/ -v

# Start server
cd backend && uv run uvicorn app.main:app --reload --port 8001

# Lint check
cd backend && uv run ruff check .

# Type check
cd backend && uv run mypy app/
```

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for code style, PR process, and test requirements.
