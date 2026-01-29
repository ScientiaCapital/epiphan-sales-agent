# Agents Overview

The Epiphan Sales Agent uses 5 specialized AI agents, each handling a specific aspect of the BDR workflow.

---

## Agent Summary

| Agent | Model | Purpose | Input | Output |
|-------|-------|---------|-------|--------|
| Lead Research | Claude | Enriches leads from multiple sources | Lead (email, company, domain) | ResearchBrief |
| Script Selection | Claude | Selects and personalizes ACQP scripts | Lead + Persona + Trigger | PersonalizedScript |
| Competitor Intel | Cerebras | Real-time battlecard responses | Context + Competitor | CompetitorResponse |
| Email Personalization | Claude | Generates outreach emails | Lead + Research + Context | PersonalizedEmail |
| Qualification | Claude | Scores leads against ICP criteria | Lead data | Score + Tier + Action |

---

## Lead Research Agent

**Purpose:** Enrich leads with data from Apollo, Clearbit, and web scraping.

**Model:** Claude (complex multi-source synthesis)

### Input
```python
{
    "email": "john.doe@umich.edu",
    "company": "University of Michigan",
    "domain": "umich.edu"
}
```

### Output
```python
{
    "apollo_data": {
        "title": "AV Director",
        "seniority": "director",
        "employees": 48000
    },
    "clearbit_data": {
        "industry": "Higher Education",
        "tech_stack": ["Panopto", "Canvas", "Zoom"]
    },
    "scraped_data": {
        "recent_news": "...",
        "job_postings": "..."
    },
    "synthesis": "University of Michigan is a large R1 research university..."
}
```

### API Endpoint
```bash
POST /api/agents/research
```

---

## Script Selection Agent

**Purpose:** Select the right ACQP warm call script based on persona and trigger type.

**Model:** Claude (nuanced personalization)

### ACQP Framework

| Phase | Duration | Purpose |
|-------|----------|---------|
| **A**cknowledge | 5s | Thank them, reference their action |
| **C**onnect | 10s | Relate to their situation |
| **Q**ualify | 10s | Ask about their context |
| **P**ropose | 5s | Offer specific value |

### Input
```python
{
    "persona": "av_director",
    "trigger": "demo_request",
    "company": "Stanford University",
    "name": "Jane Smith",
    "context": {
        "content_downloaded": "Fleet Management Case Study"
    }
}
```

### Output
```python
{
    "script": {
        "acknowledge": "Hi Jane, this is Tim from Epiphan Video. Got your demo request...",
        "connect": "Before we book time, what's driving the interest?...",
        "qualify": "Is this for a specific project with a timeline?...",
        "propose": "Perfect - let me get you on the calendar..."
    },
    "discovery_questions": [
        "What's the scope - how many rooms?",
        "When do you need this deployed by?",
        "Who else needs to be involved?"
    ],
    "objection_responses": [
        {
            "objection": "We're standardized on Crestron",
            "response": "Pearl integrates natively with Crestron control systems..."
        }
    ]
}
```

### API Endpoint
```bash
POST /api/agents/scripts
```

---

## Competitor Intelligence Agent

**Purpose:** Provide real-time battlecard responses for competitor conversations.

**Model:** Cerebras (fast response for real-time use)

### Why Cerebras?
- Sub-second response times for live call support
- Cost-effective for high-volume battlecard lookups
- Sufficient reasoning for structured responses

### Input
```python
{
    "competitor": "blackmagic_atem",
    "context": "Customer says ATEM is cheaper",
    "vertical": "house_of_worship"
}
```

### Output
```python
{
    "competitor": "Blackmagic ATEM",
    "response": "Calculate TCO: ATEM + PC + software + IT time = $3,000-5,000. Pearl Nano at $1,999 is all-in-one.",
    "key_differentiators": [
        {
            "feature": "Recording Architecture",
            "pearl": "All-in-one hardware recording",
            "competitor": "Requires external PC for recording",
            "why_it_matters": "PC can crash, Pearl hardware is purpose-built"
        }
    ],
    "proof_points": [
        "ATEM audio drift after 60 minutes makes long sessions 'worthless'",
        "ATEM software freezes requiring hard reboot documented"
    ],
    "talk_track": "ATEM is a great switcher - probably the best value for live switching. But it's not a recorder..."
}
```

### API Endpoint
```bash
POST /api/agents/competitors
```

---

## Email Personalization Agent

**Purpose:** Generate personalized outreach emails using research and context.

**Model:** Claude (brand voice consistency)

### Input
```python
{
    "lead": {
        "name": "John Doe",
        "title": "AV Director",
        "company": "University of Michigan"
    },
    "research": {
        "industry": "Higher Education",
        "employees": 48000,
        "tech_stack": ["Panopto", "Canvas"]
    },
    "persona": "av_director",
    "trigger": "content_download",
    "context": {
        "content": "NC State Case Study"
    }
}
```

### Output
```python
{
    "subject": "Managing 300+ AV rooms with a small team",
    "body": "Hi John,\n\nThanks for downloading our NC State case study...",
    "cta": "Would a 15-minute look at the fleet management dashboard be useful?",
    "personalization_notes": [
        "Referenced NC State (similar profile)",
        "Highlighted Panopto integration (detected in tech stack)",
        "Emphasized fleet management (matches AV Director pain points)"
    ]
}
```

### API Endpoint
```bash
POST /api/agents/emails
```

---

## Qualification Agent

**Purpose:** Score leads against 5-dimension ICP criteria and determine next action.

**Model:** Claude (complex reasoning for nuanced scoring)

### 5-Dimension ICP Scoring

| Dimension | Weight | Scoring Criteria |
|-----------|--------|------------------|
| Company Size | 25% | Enterprise(10), Mid-market(8), SMB(4), Too small(0) |
| Industry Vertical | 20% | Higher Ed(10), Healthcare(9), Corporate(8), Broadcast(7), Legal(6), Other(3) |
| Use Case Fit | 25% | Live streaming(10), Lecture capture(9), Recording(6), Consumer(0) |
| Tech Stack Signals | 15% | Competitive solution(10), LMS need(8), No solution(5) |
| Buying Authority | 15% | Budget holder(10), Influencer(7), End user(4), Student(0) |

### Tier Thresholds

| Tier | Score Range | Action |
|------|-------------|--------|
| Tier 1 | 70+ | Priority sequence, AE involvement early |
| Tier 2 | 50-69 | Standard sequence |
| Tier 3 | 30-49 | Light touch, marketing nurture |
| Not ICP | <30 | Disqualify |

### Input
```python
{
    "lead": {
        "company": "University of Michigan",
        "title": "AV Director",
        "email": "john.doe@umich.edu",
        "employees": 48000,
        "industry": "Higher Education"
    }
}
```

### Output
```python
{
    "score": 82.5,
    "tier": "TIER_1",
    "breakdown": {
        "company_size": {"category": "Enterprise", "score": 10, "weighted": 25.0},
        "industry_vertical": {"category": "Higher Ed", "score": 10, "weighted": 20.0},
        "use_case_fit": {"category": "Live streaming", "score": 10, "weighted": 25.0},
        "tech_stack": {"category": "No solution", "score": 5, "weighted": 7.5},
        "buying_authority": {"category": "Budget holder", "score": 10, "weighted": 15.0}
    },
    "confidence": 0.85,
    "next_action": {
        "action_type": "priority_sequence",
        "description": "High-priority lead. Add to priority outreach sequence.",
        "priority": "high",
        "ae_involvement": true,
        "missing_info": []
    }
}
```

### API Endpoint
```bash
POST /api/agents/qualify
```

For detailed scoring logic, see [Qualification Agent Deep-Dive](qualification-agent.md).

---

## Agent Interaction Patterns

### Sequential Processing

```
Lead arrives → Research → Qualify → Select Script → Generate Email
```

### Parallel Processing

```
Lead arrives → ┬─ Apollo enrichment ──┐
               ├─ Clearbit enrichment ├─→ Qualify → Scripts
               └─ Web scraping ───────┘
```

### Batch Processing

```bash
POST /api/batch/process
{
    "leads": [lead1, lead2, lead3, ...],
    "operations": ["research", "qualify", "scripts"]
}
```

---

## See Also

- [Qualification Agent](qualification-agent.md) - Detailed ICP scoring
- [Agent Architecture](../architecture/agent-architecture.md) - LangGraph patterns
- [System Overview](../architecture/system-overview.md) - Full architecture
