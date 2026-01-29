# Qualification Agent

Deep-dive into the 5-dimension ICP scoring system.

---

## Overview

The Qualification Agent scores leads against Epiphan's Ideal Customer Profile (ICP) using 5 weighted dimensions. This provides consistent, data-driven lead prioritization.

---

## 5-Dimension Scoring Model

### Dimension Weights

| Dimension | Weight | Why This Weight |
|-----------|--------|-----------------|
| Company Size | 25% | Larger orgs have more rooms, bigger deals |
| Industry Vertical | 20% | Some verticals convert better |
| Use Case Fit | 25% | Direct product-need alignment |
| Tech Stack Signals | 15% | Replacement opportunities score higher |
| Buying Authority | 15% | Budget holders close faster |

### Total: 100% (0-100 score scale)

---

## Dimension 1: Company Size (25%)

**Why it matters:** Larger organizations have more rooms/spaces to equip, leading to larger deals.

| Category | Employee Count | Raw Score | Weighted Score |
|----------|----------------|-----------|----------------|
| Enterprise | 1,000+ | 10 | 25.0 |
| Mid-market | 100-999 | 8 | 20.0 |
| SMB | 10-99 | 4 | 10.0 |
| Too small | <10 | 0 | 0.0 |
| Unknown | None | 0 | 0.0 |

### Code Reference

```python
# backend/app/services/langgraph/tools/qualification_tools.py:64
def classify_company_size(employees: int | None) -> tuple[str, int, str]:
    if employees is None:
        return ("Unknown", 0, "Employee count missing or unknown")
    if employees >= 1000:
        return ("Enterprise", 10, f"Large organization with {employees:,} employees")
    elif employees >= 100:
        return ("Mid-market", 8, f"Mid-size organization with {employees:,} employees")
    elif employees >= 10:
        return ("SMB", 4, f"Small business with {employees:,} employees")
    else:
        return ("Too small", 0, f"Very small organization ({employees} employees)")
```

---

## Dimension 2: Industry Vertical (20%)

**Why it matters:** Higher Ed and Healthcare have proven high conversion rates for Epiphan products.

| Category | Raw Score | Weighted Score | Detection Keywords |
|----------|-----------|----------------|-------------------|
| Higher Ed | 10 | 20.0 | education, university, college, academic |
| Healthcare | 9 | 18.0 | healthcare, medical, hospital, clinical |
| Corporate | 8 | 16.0 | corporate, enterprise, business services |
| Broadcast/Media | 7 | 14.0 | broadcast, media, entertainment, television |
| Legal/Government | 6 | 12.0 | legal, law, government, public sector |
| Other | 3 | 6.0 | Everything else |

### Code Reference

```python
# backend/app/services/langgraph/tools/qualification_tools.py:95
def classify_vertical(industry: str | None, company: str | None, inferred: str | None = None):
    # Higher Ed detection
    if any(kw in source_str_lower for kw in ["education", "higher ed", "university", "college"]):
        return ("Higher Ed", 10, f"Higher education vertical detected")
    # Healthcare detection
    if any(kw in source_str_lower for kw in ["healthcare", "medical", "hospital", "clinical"]):
        return ("Healthcare", 9, f"Healthcare vertical detected")
    # ... etc.
```

---

## Dimension 3: Use Case Fit (25%)

**Why it matters:** Direct alignment between what Epiphan does (video capture/streaming) and what the lead needs.

| Category | Raw Score | Weighted Score | Detection Logic |
|----------|-----------|----------------|-----------------|
| Live streaming | 10 | 25.0 | AV Director, Technical Director, video-related titles |
| Lecture capture | 9 | 22.5 | L&D Director, Simulation Director, training roles |
| Recording only | 6 | 15.0 | Court Administrator, EHS Manager, compliance roles |
| Consumer | 0 | 0.0 | Student, Intern, amateur, hobbyist |

### Persona-to-Use Case Mapping

| Persona | Typical Use Case | Score |
|---------|------------------|-------|
| AV Director | Live streaming | 10 |
| L&D Director | Lecture capture | 9 |
| Technical Director | Live streaming | 10 |
| Simulation Director | Lecture capture | 9 |
| Court Administrator | Recording only | 6 |
| Corp Comms Director | Lecture capture | 9 |
| EHS Manager | Recording only | 6 |
| Law Firm IT | Recording only | 6 |

### Code Reference

```python
# backend/app/services/langgraph/tools/qualification_tools.py:186
def classify_use_case(persona: str | None, vertical: str | None, title: str | None, tech_stack: list[str] | None = None):
    # Consumer detection (early exit)
    if any(kw in title_lower for kw in ["student", "intern", "amateur", "hobbyist"]):
        return ("Consumer", 0, "Consumer/non-business user detected")

    # AV Director / Technical Director - Live streaming fit
    if any(p in persona_lower for p in ["av director", "technical director", "av"]):
        return ("Live streaming", 10, f"Live production persona: {persona or title}")
    # ... etc.
```

---

## Dimension 4: Tech Stack Signals (15%)

**Why it matters:** Leads using competitor products are replacement opportunities; leads with LMS indicate content delivery needs.

| Category | Raw Score | Weighted Score | Detection |
|----------|-----------|----------------|-----------|
| Competitive solution | 10 | 15.0 | Vaddio, Crestron, Panopto, Kaltura, MediaSite, etc. |
| LMS/collaboration need | 8 | 12.0 | Canvas, Blackboard, Moodle, Teams, Zoom, etc. |
| No relevant solution | 5 | 7.5 | No detected tech |

### Competitor Tech Keywords

```python
COMPETITOR_TECH = {
    "vaddio", "crestron", "panopto", "kaltura", "mediasite", "yuja",
    "qumu", "brightcove", "vidyo", "polycom", "cisco webex", "lifesize",
}
```

### LMS/Collaboration Tech Keywords

```python
LMS_COLLABORATION_TECH = {
    "canvas", "blackboard", "moodle", "d2l", "brightspace", "schoology",
    "microsoft teams", "zoom", "webex", "google meet", "slack",
}
```

---

## Dimension 5: Buying Authority (15%)

**Why it matters:** Budget holders can make purchase decisions; influencers need to convince others.

| Category | Raw Score | Weighted Score | Detection Keywords |
|----------|-----------|----------------|-------------------|
| Budget holder | 10 | 15.0 | Director, VP, Chief, CTO, CIO, President, Dean |
| Influencer | 7 | 10.5 | Manager, Senior, Lead, Principal |
| End user | 4 | 6.0 | Analyst, Specialist, Coordinator, Engineer |
| Student/Intern | 0 | 0.0 | Student, Intern |

### Code Reference

```python
# backend/app/services/langgraph/tools/qualification_tools.py:339
def classify_buying_authority(title: str | None, seniority: str | None = None):
    budget_holder_keywords = [
        "director", "vp", "vice president", "chief", "cto", "cio", "coo", "ceo",
        "president", "head of", "dean", "administrator",
    ]

    if any(kw in title_lower for kw in budget_holder_keywords):
        return ("Budget holder", 10, f"Decision maker: {title}")
```

---

## Tier Assignment

### Thresholds

| Tier | Score Range | Meaning |
|------|-------------|---------|
| **Tier 1** | 70+ | Hot lead - prioritize |
| **Tier 2** | 50-69 | Good lead - standard follow-up |
| **Tier 3** | 30-49 | Low priority - marketing nurture |
| **Not ICP** | <30 | Disqualify |

### Next Actions by Tier

| Tier | Action Type | Description | AE Involvement |
|------|-------------|-------------|----------------|
| Tier 1 | priority_sequence | High-priority lead with immediate BDR follow-up | Yes |
| Tier 2 | standard_sequence | Good lead, standard outreach sequence | No |
| Tier 3 | nurture | Add to marketing nurture campaign | No |
| Not ICP | disqualify | Mark as disqualified | No |

---

## Scoring Examples

### Example 1: Tier 1 Lead

**Input:**
- Company: Stanford University
- Title: AV Director
- Employees: 15,000
- Industry: Higher Education
- Tech Stack: ["Panopto", "Canvas"]

**Scoring:**

| Dimension | Category | Raw | Weighted |
|-----------|----------|-----|----------|
| Company Size | Enterprise | 10 | 25.0 |
| Industry Vertical | Higher Ed | 10 | 20.0 |
| Use Case Fit | Live streaming | 10 | 25.0 |
| Tech Stack | Competitive (Panopto) | 10 | 15.0 |
| Buying Authority | Budget holder | 10 | 15.0 |
| **Total** | | | **100.0** |

**Result:** Tier 1 (100.0) - Priority sequence, AE involvement

---

### Example 2: Tier 2 Lead

**Input:**
- Company: Regional Hospital
- Title: Training Manager
- Employees: 800
- Industry: Healthcare
- Tech Stack: ["Zoom", "Microsoft Teams"]

**Scoring:**

| Dimension | Category | Raw | Weighted |
|-----------|----------|-----|----------|
| Company Size | Mid-market | 8 | 20.0 |
| Industry Vertical | Healthcare | 9 | 18.0 |
| Use Case Fit | Lecture capture | 9 | 22.5 |
| Tech Stack | LMS need | 8 | 12.0 |
| Buying Authority | Influencer | 7 | 10.5 |
| **Total** | | | **83.0** |

**Result:** Tier 1 (83.0) - Priority sequence

---

### Example 3: Tier 3 Lead

**Input:**
- Company: Small Law Firm
- Title: IT Coordinator
- Employees: 25
- Industry: Legal
- Tech Stack: None detected

**Scoring:**

| Dimension | Category | Raw | Weighted |
|-----------|----------|-----|----------|
| Company Size | SMB | 4 | 10.0 |
| Industry Vertical | Legal | 6 | 12.0 |
| Use Case Fit | Recording only | 6 | 15.0 |
| Tech Stack | No solution | 5 | 7.5 |
| Buying Authority | End user | 4 | 6.0 |
| **Total** | | | **50.5** |

**Result:** Tier 2 (50.5) - Standard sequence

---

### Example 4: Not ICP

**Input:**
- Company: Unknown
- Title: Student Intern
- Employees: None
- Industry: None
- Tech Stack: None

**Scoring:**

| Dimension | Category | Raw | Weighted |
|-----------|----------|-----|----------|
| Company Size | Unknown | 0 | 0.0 |
| Industry Vertical | Other | 3 | 6.0 |
| Use Case Fit | Consumer | 0 | 0.0 |
| Tech Stack | No solution | 5 | 7.5 |
| Buying Authority | Student | 0 | 0.0 |
| **Total** | | | **13.5** |

**Result:** Not ICP (13.5) - Disqualify

---

## API Usage

### Endpoint

```bash
POST /api/agents/qualify
```

### Request

```json
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

### Response

```json
{
    "score": 82.5,
    "tier": "TIER_1",
    "breakdown": {
        "company_size": {
            "category": "Enterprise",
            "raw_score": 10,
            "weighted_score": 25.0,
            "reason": "Large organization with 48,000 employees"
        },
        "industry_vertical": {
            "category": "Higher Ed",
            "raw_score": 10,
            "weighted_score": 20.0,
            "reason": "Higher education vertical detected"
        },
        "use_case_fit": {
            "category": "Live streaming",
            "raw_score": 10,
            "weighted_score": 25.0,
            "reason": "Live production persona: AV Director"
        },
        "tech_stack": {
            "category": "No solution",
            "raw_score": 5,
            "weighted_score": 7.5,
            "reason": "No tech stack information available"
        },
        "buying_authority": {
            "category": "Budget holder",
            "raw_score": 10,
            "weighted_score": 15.0,
            "reason": "Decision maker: AV Director"
        }
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

---

## See Also

- [Agents Overview](overview.md) - All 5 agents
- [ICP Qualification (BDR Guide)](../sales-playbook/icp-qualification.md) - Plain English for BDRs
- [Agent Architecture](../architecture/agent-architecture.md) - LangGraph patterns
