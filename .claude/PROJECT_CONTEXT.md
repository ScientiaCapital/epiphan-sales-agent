# Project Context: epiphan-sales-agent

**Updated:** 2026-02-22
**Branch:** main
**Tech Stack:** Python 3.12, FastAPI, LangGraph, Supabase, Railway

---

## Production Environment
- **API**: https://epiphan-api-production.up.railway.app
- **Supabase**: ulvjeeictfhfbzivexnf (us-east-1)
- **Railway project**: 8a6ddb6c-3f37-4db1-9c61-4585ad66210e

## Recent Commits

```
49b5f95 fix(security): Separate API key from JWT secret + startup validation + mypy cleanup
0d98613 feat(infra): Deploy to Railway + Supabase production
aad9371 chore(infra): update gitignore and lock files
0fb77a1 chore(infra): add dual-team observer workflow infrastructure
9018314 chore: End-of-day doc sync — mark session complete, update backlog
```

## Working Tree Status

```
Clean (all committed and pushed)
```

## Done (This Session — 2026-02-22 Session 2)
- Separated EPIPHAN_API_KEY from JWT_SECRET_KEY (security fix R1)
- Added _validate_production_secrets() startup guard (security fix R2)
- Resolved all 55 mypy errors (cast() at Supabase boundary)
- Set EPIPHAN_API_KEY in Railway production
- 9 new tests (1343 total), 0 mypy, 0 ruff

## Tomorrow

Tomorrow: Build monitoring dashboard UI (frontend) via feature-build | STANDARD scope | Est: 4h, $5-8 | Observer notes: [R3] service_key for all ops, [S1-S2] in-memory limits/sessions need Redis for scale

---

_Updated each session by END DAY workflow._
