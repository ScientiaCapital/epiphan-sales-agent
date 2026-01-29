# Lead Harvester Sync

Data flow and integration details for the Lead Harvester.

---

## Lead Harvester Overview

The **epiphan-lead-harvester** is a sophisticated lead generation platform that:

- Scrapes 11 data sources across 5 verticals
- Generates 30,000+ qualified leads per run
- Applies vertical-specific ICP scoring
- Exports to CSV/JSON for downstream consumption

---

## Data Sources

### Active Scrapers (11 total)

| Scraper | Source | Method | Leads/Run |
|---------|--------|--------|-----------|
| IPEDS Higher Ed | College Scorecard API | REST | 6,400+ |
| CMS Hospitals | CMS Provider Data | REST | 6,000+ |
| Hartford Megachurch | Hartford Institute | Playwright | 1,800+ |
| Socrata Permits | 7 metro areas | REST | Variable |
| Arizona ROC | Salesforce portal | Playwright | 500+ |
| Texas TDLR | Socrata API | REST | 1,000+ |
| California CSLB | ASP.NET forms | HTTP | 2,000+ |
| Florida DBPR | State portal | Playwright | 500+ |
| Nevada SCB | State portal | Playwright | 200+ |
| LinkedIn Sales Nav | LinkedIn | Playwright | Variable |
| NA Integrators | Multi-state aggregator | Mixed | 5,000+ |

### Data by Vertical

| Vertical | Primary Sources | Lead Volume |
|----------|-----------------|-------------|
| Higher Education | IPEDS | 6,400+ |
| Healthcare | CMS Hospitals | 6,000+ |
| House of Worship | Hartford Megachurch | 1,800+ |
| Construction | Socrata Permits | 2,000+ |
| Low Voltage Integrators | 5 state contractor DBs | 5,000+ |

---

## ICP Scoring System

The Harvester uses a **vertical-specific** scoring system:

### Higher Education Scoring

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| Carnegie Classification | 30% | R1=30, R2=24, M1=18, etc. |
| Enrollment | 20% | 20K+=20, 10K+=16, etc. |
| Tech Infrastructure | 20% | Based on detected signals |
| Funding Level | 15% | High=15, Medium=10, Low=5 |
| Distance Learning | 15% | Yes=15, Partial=10, No=5 |

### Corporate Scoring

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| Employee Count | 25% | 10K+=25, 1K+=20, 100+=15 |
| Fortune Ranking | 20% | F500=20, F1000=15, etc. |
| Office Locations | 15% | 10+=15, 5+=10, etc. |
| Industry Fit | 18% | Based on NAICS codes |
| Hybrid Work | 12% | Based on signals |
| Multi-Location | 10% | Yes=10, No=0 |

### Tier Thresholds

| Tier | Score Range | Meaning |
|------|-------------|---------|
| A | 80-100 | Ideal customer |
| B | 60-79 | Good fit |
| C | 40-59 | Marginal fit |
| D | <40 | Poor fit |

---

## Export Formats

### CSV Export

```
output/
└── ipeds_higher_ed/
    └── 2025-01-29_leads.csv
```

**CSV Schema:**

| Column | Type | Description |
|--------|------|-------------|
| external_id | string | Unique source ID (e.g., IPEDS UNITID) |
| source | string | Data source name |
| company_name | string | Institution/company name |
| industry | string | Vertical category |
| employees | int | Employee count (if available) |
| city | string | City |
| state | string | State abbreviation |
| zip | string | ZIP code |
| website | string | Company website |
| icp_score | float | 0-100 score |
| icp_tier | string | A/B/C/D |
| scoring_reason | string | Explanation of score |
| raw_data | json | Full source data |
| scraped_at | datetime | Scrape timestamp |

### JSON Export

```json
{
  "leads": [
    {
      "external_id": "123456",
      "source": "ipeds_higher_ed",
      "company_name": "Stanford University",
      "industry": "Higher Education",
      "employees": 15000,
      "location": {
        "city": "Stanford",
        "state": "CA",
        "zip": "94305"
      },
      "website": "stanford.edu",
      "scoring": {
        "score": 92,
        "tier": "A",
        "breakdown": {
          "carnegie": 30,
          "enrollment": 20,
          "tech": 18,
          "funding": 12,
          "distance": 12
        }
      },
      "raw_data": { ... },
      "scraped_at": "2025-01-29T10:30:00Z"
    }
  ],
  "metadata": {
    "source": "ipeds_higher_ed",
    "total_leads": 6400,
    "tier_a": 1200,
    "tier_b": 2100,
    "tier_c": 2000,
    "tier_d": 1100,
    "generated_at": "2025-01-29T11:00:00Z"
  }
}
```

---

## Integration with Sales Agent

### Current: Manual Import

1. Run Harvester: `python backend/run_pipeline.py --states CA TX`
2. Locate exports in `output/` directory
3. Import into Sales Agent for testing/demo

### Future: API Ingestion

Proposed endpoint in Sales Agent:

```python
# POST /api/leads/ingest
{
    "source": "lead_harvester",
    "batch_id": "2025-01-29_ipeds",
    "leads": [
        {
            "external_id": "123456",
            "company": "Stanford University",
            "industry": "Higher Education",
            "employees": 15000,
            "harvester_score": 92,
            "harvester_tier": "A",
            "location": {"state": "CA", "city": "Stanford"},
            "metadata": {"carnegie": "R1", "enrollment": 17000}
        }
    ]
}
```

**Response:**
```json
{
    "processed": 100,
    "qualified": {
        "tier_1": 45,
        "tier_2": 30,
        "tier_3": 20,
        "not_icp": 5
    },
    "enrichment_needed": 12,
    "errors": []
}
```

---

## Score Translation

Harvester and Sales Agent use different scoring models. Here's how to translate:

### Harvester → Sales Agent

| Harvester Field | Sales Agent Dimension | Mapping |
|-----------------|----------------------|---------|
| employees | Company Size | Direct mapping |
| industry/vertical | Industry Vertical | Keyword mapping |
| carnegie_class | Use Case Fit | Higher Ed = Lecture capture |
| (inferred from vertical) | Use Case Fit | Based on vertical |
| (need enrichment) | Tech Stack | Requires Apollo/Clearbit |
| (need title) | Buying Authority | Requires contact enrichment |

### Recommended Workflow

1. **Ingest** Harvester leads (company-level)
2. **Enrich** with Apollo/Clearbit (contact-level)
3. **Re-score** with 5-dimension model
4. **Route** based on Sales Agent tier

---

## Enrichment Gap

The Harvester provides **company-level** data, but Sales Agent needs **contact-level** data:

| Data Type | Harvester | Sales Agent Needs |
|-----------|-----------|-------------------|
| Company name | Yes | Yes |
| Industry | Yes | Yes |
| Employees | Yes | Yes |
| Location | Yes | Yes |
| Contact name | Sometimes | Yes |
| Contact title | Rarely | Yes (for buying authority) |
| Contact email | Sometimes | Yes (for outreach) |
| Tech stack | No | Yes (for tech signals) |

### Enrichment Sources

The Sales Agent enriches Harvester leads via:

| Service | Data Provided |
|---------|---------------|
| Apollo.io | Contact name, title, email, seniority |
| Clearbit | Company firmographics, tech stack |
| Web Scraper | Recent news, job postings |

---

## Pipeline Example

### Full Flow: University Lead

**1. Harvester scrapes IPEDS:**
```json
{
    "unitid": "243744",
    "name": "Stanford University",
    "city": "Stanford",
    "state": "CA",
    "enrollment": 17680,
    "carnegie": 15,
    "harvester_score": 92,
    "harvester_tier": "A"
}
```

**2. Sales Agent ingests and enriches:**
```json
{
    "company": "Stanford University",
    "apollo_contacts": [
        {
            "name": "Jane Smith",
            "title": "AV Director",
            "email": "jsmith@stanford.edu",
            "seniority": "director"
        }
    ],
    "clearbit_data": {
        "tech_stack": ["Panopto", "Canvas", "Zoom"]
    }
}
```

**3. Sales Agent re-scores (5-dimension):**
```json
{
    "score": 100,
    "tier": "TIER_1",
    "breakdown": {
        "company_size": 25,
        "industry_vertical": 20,
        "use_case_fit": 25,
        "tech_stack": 15,
        "buying_authority": 15
    }
}
```

**4. Sales Agent generates script:**
```json
{
    "persona": "av_director",
    "script": {
        "acknowledge": "Hi Jane, this is Tim from Epiphan Video...",
        "connect": "...",
        "qualify": "...",
        "propose": "..."
    }
}
```

**5. Push to HubSpot:**
```json
{
    "contact": {
        "email": "jsmith@stanford.edu",
        "properties": {
            "lead_score": 100,
            "lead_tier": "Tier 1",
            "persona": "AV Director"
        }
    }
}
```

---

## Configuration

### Environment Variables (Sales Agent)

```bash
# Harvester export location (if local)
HARVESTER_OUTPUT_DIR=/path/to/lead-harvester/output

# Or Supabase shared database
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=xxx

# Enrichment services
APOLLO_API_KEY=xxx
CLEARBIT_API_KEY=xxx
```

### Running Harvester

```bash
cd epiphan-lead-harvester

# Run specific verticals
python backend/run_pipeline.py --states CA TX

# Run specific scraper
python -m scripts.scrapers.ipeds_harvester

# Skip scoring (faster, for testing)
python backend/run_pipeline.py --skip-scoring
```

---

## Monitoring

### Lead Quality Metrics

Track these to ensure Harvester→Agent quality:

| Metric | Target | Action if Below |
|--------|--------|-----------------|
| Tier 1 conversion rate | >20% | Adjust Harvester scoring |
| Enrichment success rate | >80% | Check Apollo/Clearbit limits |
| Email bounce rate | <5% | Improve email validation |
| Persona match rate | >90% | Refine vertical→persona mapping |

---

## See Also

- [Project Ecosystem](project-ecosystem.md) - High-level integration
- [System Overview](../architecture/system-overview.md) - Sales Agent architecture
- [Qualification Agent](../agents/qualification-agent.md) - Scoring details
