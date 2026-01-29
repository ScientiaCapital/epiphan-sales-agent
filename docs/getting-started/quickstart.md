# Quickstart Guide

Get the Epiphan Sales Agent running in 5 minutes.

---

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- API keys for Claude (Anthropic) and optionally Cerebras

---

## 1. Clone and Install

```bash
# Clone the repository
git clone <repo-url> epiphan-sales-agent
cd epiphan-sales-agent

# Install dependencies with uv
cd backend
uv sync
```

---

## 2. Configure Environment

Create a `.env` file in the `backend/` directory:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...        # Claude API key

# Optional (for specific agents)
CEREBRAS_API_KEY=...                 # Cerebras for Competitor Intel agent
APOLLO_API_KEY=...                   # Apollo.io for lead enrichment
CLEARBIT_API_KEY=...                 # Clearbit for company data
SUPABASE_URL=...                     # Supabase database URL
SUPABASE_SERVICE_KEY=...             # Supabase service key
HUBSPOT_ACCESS_TOKEN=...             # HubSpot CRM integration
```

---

## 3. Run Tests

Verify everything is working:

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test modules
uv run pytest tests/unit/test_qualification_tools.py -v
uv run pytest tests/unit/test_personas.py -v
```

Expected: 416+ tests passing.

---

## 4. Start the Server

```bash
uv run uvicorn app.main:app --reload --port 8001
```

The API will be available at `http://localhost:8001`.

---

## 5. Make Your First API Call

### Qualify a Lead

```bash
curl -X POST http://localhost:8001/api/agents/qualify \
  -H "Content-Type: application/json" \
  -d '{
    "lead": {
      "company": "University of Michigan",
      "title": "AV Director",
      "email": "john.doe@umich.edu",
      "employees": 5000
    }
  }'
```

### Get a Personalized Script

```bash
curl -X POST http://localhost:8001/api/agents/scripts \
  -H "Content-Type: application/json" \
  -d '{
    "persona": "av_director",
    "trigger": "demo_request",
    "company": "Stanford University",
    "name": "Jane Smith"
  }'
```

### Research a Lead

```bash
curl -X POST http://localhost:8001/api/agents/research \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Harvard University",
    "domain": "harvard.edu",
    "email": "contact@harvard.edu"
  }'
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/agents/qualify` | POST | Score lead against ICP criteria |
| `/api/agents/scripts` | POST | Get personalized call script |
| `/api/agents/research` | POST | Enrich lead with external data |
| `/api/agents/competitors` | POST | Get competitor battlecard response |
| `/api/agents/emails` | POST | Generate personalized email |
| `/api/batch/process` | POST | Process multiple leads |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── api/routes/          # API endpoints
│   ├── data/                # Personas, scripts, battlecards
│   └── services/
│       ├── langgraph/       # AI agents
│       ├── enrichment/      # Apollo, Clearbit, web scraper
│       └── integrations/    # HubSpot CRM
└── tests/
    ├── unit/                # Unit tests
    └── integration/         # Integration tests
```

---

## Next Steps

1. Read [System Overview](../architecture/system-overview.md) to understand the architecture
2. Explore [Agents Overview](../agents/overview.md) to learn about each AI agent
3. Review [Personas Overview](../sales-playbook/personas-overview.md) for BDR context

---

## Troubleshooting

### Missing API Key Errors

Ensure your `.env` file has the required keys. The server will log which keys are missing.

### Test Failures

```bash
# Check for lint issues first
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check . --fix
```

### Port Already in Use

```bash
# Use a different port
uv run uvicorn app.main:app --reload --port 8002
```
