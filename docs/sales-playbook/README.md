# Sales Playbook

> AI-powered tools for Epiphan BDRs

---

## What This System Does For You

The Epiphan Sales Agent is your AI assistant that helps you:

1. **Know your leads** - Instantly see if a lead is Tier 1 (hot) or Tier 3 (nurture)
2. **Personalize your calls** - Get scripts tailored to WHO they are and WHAT they did
3. **Handle competitors** - Real-time battlecard responses for objection handling
4. **Write better emails** - AI-generated personalized outreach

---

## Quick Reference

| I want to... | Go to... |
|--------------|----------|
| Understand the 8 buyer personas | [Personas Overview](personas-overview.md) |
| Get call script help | [Scripts Guide](scripts-guide.md) |
| Understand lead scoring | [ICP Qualification](icp-qualification.md) |
| Handle competitor objections | [Competitive Intel](../reference/competitive-intel.md) |

---

## The 8 Personas (Quick Look)

| Persona | Primary Pain | Hot Button |
|---------|--------------|------------|
| **AV Director** | Too many rooms, too few people | "NC State: 300+ rooms with team of 3" |
| **L&D Director** | Can't scale content without cost | "218% higher revenue per employee" |
| **Technical Director** | Can't fail on Sunday | "5-minute volunteer training" |
| **Simulation Director** | HIPAA compliance anxiety | "PHI never leaves your network" |
| **Court Administrator** | Court reporter shortage | "33 states permit e-recording" |
| **Corp Comms Director** | Zero tolerance for CEO failures | "Broadcast quality, no production team" |
| **EHS Manager** | OSHA compliance gaps | "One violation = $100K-$500K" |
| **Law Firm IT** | Discovery risk from cloud | "No cloud = no discovery risk" |

See [Personas Overview](personas-overview.md) for full details.

---

## ACQP Framework (30-Second Calls)

Every warm call follows ACQP:

| Phase | Time | What You Say |
|-------|------|--------------|
| **A**cknowledge | 5s | Thank them, reference their action |
| **C**onnect | 10s | Relate to their situation |
| **Q**ualify | 10s | Ask about their context |
| **P**ropose | 5s | Offer specific value |

See [Scripts Guide](scripts-guide.md) for persona-specific scripts.

---

## Lead Scoring Tiers

| Tier | Score | What It Means | Your Action |
|------|-------|---------------|-------------|
| **Tier 1** | 70+ | Hot lead, strong ICP fit | Call immediately, involve AE |
| **Tier 2** | 50-69 | Good lead, standard fit | Standard outreach sequence |
| **Tier 3** | 30-49 | Low priority | Add to marketing nurture |
| **Not ICP** | <30 | Poor fit | Disqualify |

See [ICP Qualification](icp-qualification.md) for what the scores mean.

---

## Speed-to-Lead Matters

**Key stat:** Responding within 5 minutes = **9x higher conversion rate**

The AI helps you respond faster with:
- Pre-qualified leads (you know tier immediately)
- Ready scripts (don't waste time thinking)
- Context from research (know who you're calling)

---

## Using the API

### Check Lead Score

```bash
curl -X POST http://localhost:8001/api/agents/qualify \
  -H "Content-Type: application/json" \
  -d '{"lead": {"company": "Stanford University", "title": "AV Director", "employees": 15000}}'
```

### Get Call Script

```bash
curl -X POST http://localhost:8001/api/agents/scripts \
  -H "Content-Type: application/json" \
  -d '{"persona": "av_director", "trigger": "demo_request", "company": "Stanford", "name": "Jane"}'
```

### Get Competitor Response

```bash
curl -X POST http://localhost:8001/api/agents/competitors \
  -H "Content-Type: application/json" \
  -d '{"competitor": "blackmagic_atem", "context": "Customer says ATEM is cheaper"}'
```

---

## Questions?

Talk to your manager or check the [full documentation](../README.md).
