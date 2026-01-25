# Architecture & Planning Notes

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (TBD)                        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Scripts   │  │   HubSpot   │  │    Clari    │     │
│  │    API      │  │   Client    │  │   Client    │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    Supabase                              │
│              (PostgreSQL + Auth)                         │
└─────────────────────────────────────────────────────────┘
```

## ACQP Framework (Warm Call Scripts)

Each persona script follows the ACQP structure:
- **Acknowledge**: Greeting + reference to their action
- **Connect**: Pain point that resonates with their role
- **Qualify**: Discovery question to gauge fit
- **Propose**: Value prop with reference customer

## Planned API Endpoints

### Implemented
- None yet exposed via API

### Planned
- `GET /api/scripts/warm` - Get warm call script by trigger/persona
- `GET /api/leads/{id}` - Get lead details from HubSpot
- `POST /api/calls/log` - Log call outcome

## Design Decisions

### 1. Script Lookup Strategy
- Persona + Trigger → Persona-specific script
- Trigger only → Generic trigger script
- Neither → Return None (404)

### 2. CRM Integration
- HubSpot as primary CRM
- Clari for call intelligence (optional)
- Async clients for non-blocking I/O

### 3. Data Storage
- Scripts stored as Python data structures (not DB)
- Lead/call data in Supabase
- Secrets in .env (not committed)
