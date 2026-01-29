# Project Ecosystem

How the three Epiphan sales projects work together.

---

## The Three Projects

| Project | Purpose | Key Output |
|---------|---------|------------|
| **epiphan-lead-harvester** | Generate and score leads | 30K+ qualified leads per run |
| **epiphan-bdr-playbook** | Sales intelligence content | Personas, scripts, battlecards |
| **epiphan-sales-agent** | AI-powered BDR assistant | Personalized scripts, emails, scoring |

---

## Data Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LEAD HARVESTER                                       │
│                                                                              │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │
│   │   IPEDS    │  │    CMS     │  │  Socrata   │  │ State Contractors  │   │
│   │ Higher Ed  │  │ Hospitals  │  │  Permits   │  │ (AZ, TX, CA, FL)   │   │
│   │  6,400+    │  │  6,000+    │  │ 7 metros   │  │    2,000-5,000+    │   │
│   └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────────┬──────────┘   │
│         │               │               │                    │              │
│         └───────────────┴───────────────┴────────────────────┘              │
│                                    │                                         │
│                                    ▼                                         │
│                        ┌──────────────────────┐                             │
│                        │   ICP SCORING        │                             │
│                        │   (Vertical-based)   │                             │
│                        │   Tier A/B/C/D       │                             │
│                        └──────────┬───────────┘                             │
│                                   │                                          │
│                                   ▼                                          │
│                        ┌──────────────────────┐                             │
│                        │   CSV/JSON Export    │                             │
│                        │   output/ directory  │                             │
│                        └──────────┬───────────┘                             │
│                                   │                                          │
└───────────────────────────────────┼──────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SALES AGENT                                         │
│                                                                              │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │                      LEAD INGESTION                                 │    │
│   │   (Future: API endpoint to consume Harvester exports)               │    │
│   └────────────────────────────────────┬───────────────────────────────┘    │
│                                        │                                     │
│                                        ▼                                     │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│   │   Lead     │  │  Script    │  │ Competitor │  │   Email    │           │
│   │  Research  │  │ Selection  │  │   Intel    │  │   Agent    │           │
│   │   Agent    │  │   Agent    │  │   Agent    │  │            │           │
│   └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘           │
│         │               │               │               │                    │
│         └───────────────┴───────────────┴───────────────┘                    │
│                                    │                                         │
│                                    ▼                                         │
│                        ┌──────────────────────┐                             │
│                        │ QUALIFICATION AGENT  │                             │
│                        │ (5-dimension scoring)│                             │
│                        │ Tier 1/2/3/Not ICP   │                             │
│                        └──────────┬───────────┘                             │
│                                   │                                          │
└───────────────────────────────────┼──────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HUBSPOT CRM                                        │
│                                                                              │
│   Contacts │ Companies │ Deals │ Activities │ Sequences                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## BDR Playbook Integration

The **epiphan-bdr-playbook** is the source of truth for sales content. The Sales Agent consumes this content:

| Playbook Content | Sales Agent Location | Usage |
|------------------|---------------------|-------|
| 8 buyer personas | `app/data/personas.py` | Persona matching and context |
| ACQP warm scripts | `app/data/persona_warm_scripts.py` | Script Selection Agent |
| Competitor battlecards | `app/data/competitors.py` | Competitor Intel Agent |
| Vertical targeting | `app/data/schemas.py` | ICP scoring weights |
| Discovery questions | `app/data/personas.py` | Script personalization |

### Content Sync Process

When playbook content is updated:

1. Review changes in playbook repo
2. Update corresponding Python data files in Sales Agent
3. Run tests to ensure schema compatibility
4. Deploy updated Sales Agent

---

## Lead Harvester Integration

### Current State

The Lead Harvester outputs qualified leads to CSV/JSON files in its `output/` directory:

```
epiphan-lead-harvester/
└── output/
    ├── ipeds_higher_ed/
    │   └── 2025-01-29_leads.csv
    ├── cms_hospitals/
    │   └── 2025-01-29_leads.csv
    └── contractors/
        └── 2025-01-29_az_tx_ca.csv
```

### Planned Integration

Future enhancement: Direct API ingestion

```python
# Proposed endpoint
POST /api/leads/ingest
{
    "source": "lead_harvester",
    "leads": [
        {
            "external_id": "ipeds_123456",
            "company": "Stanford University",
            "industry": "Higher Education",
            "employees": 15000,
            "harvester_score": 85,  # Harvester's A/B/C/D score
            "harvester_tier": "A"
        }
    ]
}
```

### Score Alignment

**Issue:** Harvester uses A/B/C/D tiers, Sales Agent uses Tier 1/2/3.

| Harvester Tier | Score Range | Sales Agent Tier |
|----------------|-------------|------------------|
| A | 80-100 | Tier 1 (70+) |
| B | 60-79 | Tier 2 (50-69) |
| C | 40-59 | Tier 3 (30-49) |
| D | <40 | Not ICP (<30) |

**Recommendation:** Use Harvester score as input, but re-score with Sales Agent's 5-dimension model for final qualification.

---

## Data Models

### Lead Schema (Shared Concept)

Both projects work with lead data. Key fields:

| Field | Harvester | Sales Agent | Notes |
|-------|-----------|-------------|-------|
| external_id | Yes | No | Harvester's unique ID |
| company | Yes | Yes | Company name |
| industry | Yes | Yes | Industry vertical |
| employees | Yes | Yes | Employee count |
| title | Sometimes | Yes | Contact job title |
| email | Sometimes | Yes | Contact email |
| domain | Yes | Sometimes | Company domain |
| icp_score | Yes (A/B/C/D) | Yes (0-100) | Different scales |
| source | Yes | Yes (via import) | Data source |

### Persona Mapping

Harvester focuses on verticals; Sales Agent maps to personas:

| Harvester Vertical | Sales Agent Personas |
|-------------------|---------------------|
| Higher Education | AV Director, L&D Director |
| Healthcare | Simulation Director |
| Corporate | L&D Director, Corp Comms Director |
| Government/Legal | Court Administrator, Law Firm IT |
| Industrial | EHS Manager |
| House of Worship | Technical Director |

---

## Implementation Roadmap

### Phase 1: Manual Sync (Current)

- Harvester exports CSV/JSON
- Manual import into Sales Agent testing
- Separate scoring in each system

### Phase 2: API Ingestion

- Build `/api/leads/ingest` endpoint
- Accept Harvester export format
- Re-score with 5-dimension model

### Phase 3: Real-Time Sync

- Webhook from Harvester on new leads
- Automatic qualification and routing
- CRM update via HubSpot integration

### Phase 4: Unified Pipeline

- Single orchestration layer
- Harvester → Agent → CRM automated
- Shared Supabase for state

---

## Tech Stack Alignment

| Component | Lead Harvester | Sales Agent |
|-----------|---------------|-------------|
| Language | Python 3.10+ | Python 3.10+ |
| Package Manager | pip/requirements.txt | uv |
| Database | Supabase PostgreSQL | Supabase PostgreSQL |
| AI Scoring | Gemini | Claude/Cerebras |
| Framework | Scripts/CLI | FastAPI |

### Shared Infrastructure

- **Supabase:** Both can share the same Supabase project
- **Environment:** Same `.env` pattern for API keys
- **Testing:** Both use pytest

---

## See Also

- [Lead Harvester Sync](lead-harvester-sync.md) - Detailed data flow
- [System Overview](../architecture/system-overview.md) - Sales Agent architecture
- [Agents Overview](../agents/overview.md) - AI agents detail
