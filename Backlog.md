# Product Backlog

## Priority 1 - Code Quality
- [ ] Run `ruff check . --fix` to fix 228 auto-fixable issues
- [ ] Add type stubs for fastapi (`pip install types-fastapi`)
- [ ] Add type stubs for hubspot client
- [ ] Fix remaining mypy errors

## Priority 2 - API Implementation
- [ ] Create `/api/scripts/warm` endpoint
- [ ] Add request validation
- [ ] Add OpenAPI documentation
- [ ] Integration tests for API

## Priority 3 - CRM Integration
- [ ] HubSpot lead retrieval endpoint
- [ ] Call logging endpoint
- [ ] Activity sync with HubSpot

## Priority 4 - Features
- [ ] Cold call scripts (separate from warm)
- [ ] Objection handling responses
- [ ] Email templates per persona
- [ ] Meeting scheduler integration

## Priority 5 - Infrastructure
- [ ] Docker containerization
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Staging environment
- [ ] Production deployment

## Tech Debt
- [ ] Install supabase module for integration tests
- [ ] Standardize import style (PEP 604 `X | None`)
- [ ] Remove unused imports
- [ ] Add comprehensive error handling

---

## Completed
- [x] Persona-specific warm scripts (8 personas)
- [x] ACQP framework implementation
- [x] Unit test coverage (50 tests)
- [x] Schema definitions (Pydantic)
- [x] Script lookup helper functions
