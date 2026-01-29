# Product Backlog

## Priority 1 - Production Deployment
- [ ] Set up production environment variables
- [ ] Run SQL migrations (001, 002, 003)
- [ ] Configure public webhook URLs
- [ ] Set up monitoring/alerting

## Priority 2 - Frontend
- [ ] Build monitoring dashboard UI
- [ ] Phone approval interface
- [ ] Batch status viewer

## Priority 3 - Enhanced Features
- [ ] Supabase persistence for batch tracking (currently in-memory)
- [ ] Historical credit usage charts
- [ ] Webhook retry logic for failures

## Tech Debt
- [ ] Fix mypy type stub issues (fastapi, hubspot)
- [ ] Fix integration test fixture (`_supabase_client`)

---

## Completed ✓

### Code Quality (DONE)
- [x] Run `ruff check . --fix` - 0 lint errors
- [x] Remove unused imports
- [x] Standardize import style

### API Implementation (DONE)
- [x] All agent endpoints (research, scripts, competitors, emails, qualify)
- [x] Lead management endpoints (ingest, sync, score, prioritized)
- [x] Monitoring endpoints (credits, rate-limits, batches)
- [x] Webhook endpoints (Apollo phone, Harvester push)

### CRM Integration (DONE)
- [x] HubSpot sync service
- [x] Phone approval workflow
- [x] Audit logging with HubSpot property mapping

### Features (DONE)
- [x] Tiered Apollo enrichment (67% credit savings)
- [x] ATL decision-maker detection (8 personas, 40 titles)
- [x] Real-time Harvester sync
- [x] Background processing pipeline

### Testing (DONE)
- [x] 676 unit tests passing
- [x] Comprehensive test coverage for all new features
