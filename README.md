# Epiphan Sales Agent

AI-powered sales intelligence platform for Epiphan's BDR team. Analyzes 100,000+ leads to identify patterns, prioritize outreach, and learn from AE conversations.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    EPIPHAN SALES AGENT                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   HubSpot    │    │    Clari     │    │   Enrichment │      │
│  │  100k+ Leads │    │   Copilot    │    │    APIs      │      │
│  │              │    │ AE Insights  │    │Apollo/Hunter │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │               │
│         └───────────────────┼───────────────────┘               │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    AGENT ORCHESTRATION                    │  │
│  │                      (LangGraph)                          │  │
│  │                                                           │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │  │
│  │  │Qualification│ │ Enrichment │ │ Prediction │            │  │
│  │  │   Agent    │ │   Agent    │ │   Agent    │            │  │
│  │  └────────────┘ └────────────┘ └────────────┘            │  │
│  │                                                           │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │  │
│  │  │Conversation│ │   BDR      │ │  Pattern   │            │  │
│  │  │  Analyst   │ │  Coach     │ │  Detector  │            │  │
│  │  └────────────┘ └────────────┘ └────────────┘            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     OUTPUTS                               │  │
│  │  • Prioritized Lead Queue       • Win/Loss Analysis      │  │
│  │  • Best Lead Patterns           • Buying Signal Detection│  │
│  │  • Outreach Recommendations     • AE Playbook Insights   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Lead Intelligence (HubSpot Integration)
- Sync and analyze 100,000+ BDR leads
- Identify patterns in successful conversions
- Detect leads with no prior outreach (untouched opportunities)
- Email domain analysis for lead quality scoring

### 2. Conversation Intelligence (Clari Copilot)
- Pull call recordings and transcripts from Lex, Phil, and other AEs
- Extract buying signals and objection patterns
- Understand why deals are won or lost
- Build playbooks from successful conversations

### 3. Pattern Detection
- ML-powered analysis of lead characteristics
- Identify common traits of best-converting leads
- Surface hidden opportunities in existing database
- Predict conversion likelihood

### 4. BDR Coaching
- Real-time suggestions based on AE patterns
- Personalized outreach recommendations
- Objection handling guidance from won deals

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI + Python 3.11 |
| **Agents** | LangGraph + Claude/Cerebras/DeepSeek |
| **Database** | PostgreSQL + Supabase |
| **Cache** | Redis |
| **Frontend** | React 19 + TypeScript + Vite |
| **CRM** | HubSpot API |
| **Conv. Intel** | Clari Copilot API |

## Quick Start

```bash
# 1. Clone and setup
cd epiphan-sales-agent
cp .env.example .env
# Fill in your API keys

# 2. Start infrastructure
docker-compose up -d

# 3. Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8001

# 4. Frontend
cd frontend
npm install
npm run dev
```

## Project Structure

```
epiphan-sales-agent/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # REST API endpoints
│   │   ├── models/              # SQLAlchemy models
│   │   ├── services/
│   │   │   ├── langgraph/       # AI agents
│   │   │   │   └── agents/      # Specialized agents
│   │   │   └── integrations/    # External APIs
│   │   │       ├── hubspot/     # HubSpot CRM
│   │   │       └── clari/       # Clari Copilot
│   │   ├── core/                # Config, logging
│   │   └── tasks/               # Celery async tasks
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/          # React components
│       ├── pages/               # Route pages
│       └── hooks/               # React Query hooks
├── docker-compose.yml
└── requirements.txt
```

## API Keys Required

| Service | Purpose | How to Get |
|---------|---------|------------|
| **HubSpot** | Lead data sync | Create private app in HubSpot |
| **Clari Copilot** | Conversation data | Request read-only API from admin |
| **Anthropic** | Claude AI (quality) | https://console.anthropic.com |
| **Cerebras** | Fast inference | https://cloud.cerebras.ai |
| **Apollo** | Contact enrichment | https://apollo.io/api |

## Development

```bash
# Run tests
pytest backend/tests/

# Run with coverage
pytest --cov=app backend/tests/

# Lint
ruff check backend/

# Format
ruff format backend/
```

## License

Private - Epiphan Video Internal Use Only
