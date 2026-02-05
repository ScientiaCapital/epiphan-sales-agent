# Production Deployment Checklist

**Version**: 0.1.0 | **Last Updated**: 2026-02-05

This checklist covers deploying the Epiphan Sales Agent to production. Follow steps in order.

---

## Pre-Flight Checks

### 1. Code Quality
- [ ] All tests pass: `cd backend && uv run pytest tests/ -v`
- [ ] No type errors: `cd backend && uv run mypy app/`
- [ ] No lint errors: `cd backend && uv run ruff check .`
- [ ] No secrets in code: `git secrets --scan` (if installed)

### 2. Environment Variables
Copy `backend/.env.example` to production secrets manager and fill in values.

**Required for core functionality:**
| Variable | Description | How to Generate |
|----------|-------------|-----------------|
| `SUPABASE_URL` | Supabase project URL | Supabase Dashboard → Settings → API |
| `SUPABASE_SERVICE_KEY` | Service role key (server-side only) | Supabase Dashboard → Settings → API |
| `ANTHROPIC_API_KEY` | Claude API key | console.anthropic.com |
| `JWT_SECRET_KEY` | JWT signing key | `openssl rand -hex 64` |

**Required for phone enrichment (PHONES ARE GOLD!):**
| Variable | Description | How to Generate |
|----------|-------------|-----------------|
| `APOLLO_API_KEY` | Apollo.io API key | Apollo Dashboard → Settings → Integrations |
| `APOLLO_WEBHOOK_URL` | Public URL for phone callbacks | Your API domain + `/api/webhooks/apollo/phone-reveal` |
| `APOLLO_WEBHOOK_SECRET` | HMAC signature secret | `openssl rand -hex 32` |

**Required for Lead Harvester sync:**
| Variable | Description | How to Generate |
|----------|-------------|-----------------|
| `HARVESTER_WEBHOOK_SECRET` | HMAC signature secret | `openssl rand -hex 32` |

**Optional but recommended:**
| Variable | Description |
|----------|-------------|
| `LANGCHAIN_TRACING_V2=true` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | LangSmith API key |
| `HUBSPOT_ACCESS_TOKEN` | HubSpot CRM sync |

---

## Database Migrations

Run migrations **in order** (they have dependencies):

### Migration 1: LangGraph Checkpoints
```bash
# Creates: checkpoints, checkpoint_blobs, checkpoint_writes tables
# Purpose: Agent state persistence, human-in-the-loop, time-travel debugging
psql $DATABASE_URL -f backend/migrations/001_add_checkpoints.sql
```

### Migration 2: Semantic Memory Store
```bash
# Creates: semantic_store table
# REQUIRES: pgvector extension (run `CREATE EXTENSION IF NOT EXISTS vector;` first)
# Purpose: Pattern learning, similar lead retrieval
psql $DATABASE_URL -f backend/migrations/002_add_semantic_store.sql
```

### Migration 3: Apollo Phone Webhooks
```bash
# Creates: apollo_phone_webhooks table
# Purpose: Store async phone data from Apollo callbacks
psql $DATABASE_URL -f backend/migrations/003_add_webhook_phone_data.sql
```

**For Supabase:** Run each SQL file in the SQL Editor (Dashboard → SQL Editor → New Query)

---

## Deployment Steps

### 1. Deploy Application
```bash
# Example for Docker/Railway/Fly.io
docker build -t epiphan-sales-agent ./backend
docker push your-registry/epiphan-sales-agent:latest

# Or for uvicorn direct:
cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 2. Configure Webhook Endpoints
Register these URLs with external services:

**Apollo (for phone enrichment):**
- URL: `https://your-api-domain.com/api/webhooks/apollo/phone-reveal`
- Method: POST
- Secret: Use value from `APOLLO_WEBHOOK_SECRET`

**Lead Harvester (for real-time sync):**
- URL: `https://your-api-domain.com/api/webhooks/harvester/lead-push`
- Method: POST
- Secret: Use value from `HARVESTER_WEBHOOK_SECRET`

---

## Post-Deployment Verification

### 1. Health Check
```bash
# Should return 200 OK with version info
curl https://your-api-domain.com/health
```

### 2. OpenAPI Documentation
```bash
# Should load Swagger UI
curl https://your-api-domain.com/docs
```

### 3. Monitoring Endpoints
```bash
# Credit usage tracking
curl https://your-api-domain.com/api/monitoring/credits

# Rate limit status
curl https://your-api-domain.com/api/monitoring/rate-limits
```

### 4. LangSmith Verification
If tracing is enabled:
1. Go to https://smith.langchain.com
2. Select project `epiphan-sales-agent`
3. Verify traces appear with prompt caching metadata

### 5. Webhook Test
Send a test payload to the Harvester webhook:
```bash
curl -X POST https://your-api-domain.com/api/webhooks/harvester/lead-push \
  -H "Content-Type: application/json" \
  -H "X-Harvester-Signature: $(echo -n '{"test": true}' | openssl dgst -sha256 -hmac $HARVESTER_WEBHOOK_SECRET | cut -d' ' -f2)" \
  -d '{"test": true}'
```

---

## Rollback Procedure

### If deployment fails:

1. **Revert to previous image/commit:**
   ```bash
   git checkout <previous-commit>
   # Redeploy
   ```

2. **Database rollback (if needed):**
   - Checkpoints: `DROP TABLE IF EXISTS checkpoints, checkpoint_blobs, checkpoint_writes CASCADE;`
   - Semantic store: `DROP TABLE IF EXISTS semantic_store CASCADE;`
   - Phone webhooks: `DROP TABLE IF EXISTS apollo_phone_webhooks CASCADE;`

3. **Verify rollback:**
   ```bash
   curl https://your-api-domain.com/health
   ```

### If webhooks stop working:

1. Check signature secret matches between sender and receiver
2. Verify endpoint is publicly accessible (not behind auth)
3. Check logs for signature validation errors

---

## Monitoring & Alerts

### Key Metrics to Monitor
| Metric | Warning Threshold | Critical Threshold |
|--------|-------------------|-------------------|
| Apollo credits/day | 80% of daily limit | 95% of daily limit |
| API response time | > 2s (p95) | > 5s (p95) |
| Error rate | > 1% | > 5% |
| LLM token usage | 80% of budget | 95% of budget |

### Recommended Alerts
- Apollo credit usage approaching limit
- Webhook delivery failures (3+ consecutive)
- Agent execution errors (any)
- Database connection pool exhaustion

---

## Contacts

| Role | Contact |
|------|---------|
| On-call | TBD |
| Apollo support | support@apollo.io |
| Supabase support | support.supabase.com |
| Anthropic support | support@anthropic.com |
