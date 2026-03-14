# Backlog

**Updated:** 2026-03-14

## Prioritized Items

| # | Item | Severity | Impact | Effort | Source |
|---|------|----------|--------|--------|--------|
| 1 | Redis session store for WebSocket sessions (remove 1-worker constraint) | RISK | HIGH | MEDIUM | Observer ARCH S2 |
| 2 | Redis-backed rate limiting (limits reset on deploy) | SMELL | MEDIUM | LOW | Observer ARCH S1 |
| 3 | RLS policies + anon_key for read operations | RISK | MEDIUM | MEDIUM | Observer ARCH R3 |
| 4 | Dockerfile HEALTHCHECK use $API_PORT not hardcoded 8001 | SMELL | LOW | LOW | Observer ARCH S3 |
| 5 | Scrub .env.example of real-looking keys | SMELL | LOW | LOW | Observer ARCH S4 |

## Completed

| Item | Completed | Session |
|------|-----------|---------|
| JWT secret separated from API key | 2026-02-22 | prod-deploy |
| Startup validation added | 2026-02-22 | prod-deploy |
| Observer path mismatch fixed | 2026-03-14 | session-3 |
