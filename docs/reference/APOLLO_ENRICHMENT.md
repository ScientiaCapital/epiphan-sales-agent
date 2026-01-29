# Apollo.io Phone & Email Enrichment Reference

> **⚠️ CRITICAL: PHONES ARE GOLD!**
>
> This document contains critical information about Apollo phone enrichment.
> Phone numbers are essential for BDR outreach. Without proper configuration,
> Apollo either rejects requests or returns only employer/HQ phones.

**Last Updated:** 2025-01-29 (Deep research with official Apollo documentation)

**Official Documentation Sources:**
- [People Enrichment API](https://docs.apollo.io/reference/people-enrichment)
- [Retrieve Mobile Phone Numbers](https://docs.apollo.io/docs/retrieve-mobile-phone-numbers-for-contacts)
- [API Pricing](https://docs.apollo.io/docs/api-pricing)
- [Phone Numbers in Apollo](https://support.apollo.io/hc/en-us/articles/360020355912-Phone-numbers-in-Apollo)

---

## ⚠️ CRITICAL: Webhook is MANDATORY for Phone Enrichment

> **VERIFIED FINDING (2025-01-29 from official Apollo docs):**
>
> When using `reveal_phone_number=true`, the `webhook_url` parameter is **MANDATORY**.
>
> *"If you set the `reveal_phone_number` parameter to `true`, this parameter becomes mandatory."*
> — [Apollo API Documentation](https://docs.apollo.io/reference/people-enrichment)
>
> **Without webhook_url:** API returns error: *"Please add a valid 'webhook_url' parameter when using 'reveal_phone_number'"*

### Phone Delivery is ASYNCHRONOUS

```
┌─────────────────┐                    ┌──────────────────┐
│  Your App       │                    │  Apollo API      │
│                 │                    │                  │
│  POST /people/  │ ──────────────────▶│  /people/match   │
│  match with:    │                    │                  │
│  - email        │                    │  Returns 200 OK  │
│  - reveal_phone │◀──────────────────│  immediately     │
│    =true        │                    │  with ONLY:      │
│  - webhook_url  │                    │  - Basic info    │
│                 │                    │  - Employer phone│
└─────────────────┘                    └──────────────────┘
                                                │
                                                │ Apollo verifies
                                                │ phone numbers
                                                │ (2-10 minutes)
                                                │
                                                ▼
┌─────────────────┐                    ┌──────────────────┐
│  Your Webhook   │◀───────────────────│  Apollo POST     │
│  Endpoint       │                    │  with ALL phones:│
│                 │                    │  - mobile        │
│  Updates lead   │                    │  - work_direct   │
│  record with    │                    │  - work          │
│  phone data     │                    │  - home          │
└─────────────────┘                    └──────────────────┘
```

---

## API Parameters Reference

### `/people/match` Endpoint

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `email` | string | Yes* | - | Contact email address |
| `api_key` | string | Yes | - | Your Apollo API key |
| `reveal_phone_number` | boolean | No | `false` | Enable phone enrichment (8 credits) |
| `webhook_url` | string | **MANDATORY if reveal_phone=true** | - | URL for async phone delivery |
| `reveal_personal_emails` | boolean | No | `false` | Enable personal email (1 credit) |

*At least one identifier required (email, name, linkedin_url, etc.)

### Correct API Request

```python
# ✅ CORRECT - Full phone enrichment with webhook
payload = {
    "email": "john.smith@company.com",
    "api_key": "your_api_key",
    "reveal_phone_number": True,
    "webhook_url": "https://api.yourdomain.com/webhooks/apollo/phone-reveal"
}

response = requests.post(
    "https://api.apollo.io/v1/people/match",
    json=payload
)
```

### Incorrect Requests

```python
# ❌ WRONG - No reveal_phone_number = empty phone array
payload = {
    "email": "john@company.com",
    "api_key": "your_api_key"
}
# Result: phone_numbers: []

# ❌ WRONG - reveal_phone but no webhook = API ERROR
payload = {
    "email": "john@company.com",
    "api_key": "your_api_key",
    "reveal_phone_number": True
    # Missing webhook_url!
}
# Result: Error "Please add a valid 'webhook_url' parameter when using 'reveal_phone_number'"
```

---

## Credit Costs (Verified)

| Operation | Credits | Notes |
|-----------|---------|-------|
| Basic enrichment (no phones) | 1 | Name, title, company, employer phone only |
| Phone enrichment (per personal number) | 8 | Mobile, work_direct, work, home, corporate |
| Company/HQ phone (`work_hq`) | FREE | Included in basic enrichment |
| Full enrichment (basic + 1 phone) | 9 | 1 + 8 credits |
| Combined (email + phones) | 10+ | Depends on numbers found |

**Cost Consideration:**
- At ~$0.20/credit, phone enrichment costs ~$1.60 per lead
- But one converted call pays for thousands of enrichments
- **PHONES ARE GOLD** - always enrich for qualified leads

---

## Phone Types from Apollo

| Type | Property | Priority | Cost | Description |
|------|----------|----------|------|-------------|
| `work_direct` | Direct dial | **#1 BEST** | 8 credits | Reaches decision-maker directly |
| `mobile` | Personal cell | **#2 Good** | 8 credits | High answer rate |
| `work` | Office line | **#3 OK** | 8 credits | May need assistant |
| `work_hq` | Switchboard | **#4 Fallback** | FREE | Requires asking for person |
| `home` | Home phone | **#5 Last** | 8 credits | Personal/home number |
| `corporate` | Corporate | **#3 OK** | 8 credits | General corporate line |

---

## Response Formats

### Immediate Response (200 OK)

Only includes employer/HQ phone:

```json
{
  "person": {
    "first_name": "John",
    "last_name": "Smith",
    "title": "AV Director",
    "email": "john.smith@university.edu",
    "linkedin_url": "https://linkedin.com/in/johnsmith",
    "seniority": "director",
    "departments": ["Information Technology"],
    "organization": {
      "name": "State University",
      "phone": "+14155550000",
      "industry": "Higher Education"
    },
    "phone_numbers": [
      {
        "raw_number": "+1 (415) 555-0000",
        "sanitized_number": "+14155550000",
        "type": "work_hq"
      }
    ]
  }
}
```

### Webhook Payload (2-10 minutes later)

Includes ALL verified phone numbers:

```json
{
  "person": {
    "id": "abc123",
    "email": "john.smith@university.edu",
    "first_name": "John",
    "last_name": "Smith",
    "phone_numbers": [
      {
        "id": "phone_1",
        "raw_number": "+1 (415) 555-1234",
        "sanitized_number": "+14155551234",
        "type": "work_direct",
        "confidence": "high",
        "status": "valid_number",
        "dnc_status": "not_on_dnc",
        "position": 0
      },
      {
        "id": "phone_2",
        "raw_number": "+1 (415) 555-9999",
        "sanitized_number": "+14155559999",
        "type": "mobile",
        "confidence": "high",
        "status": "valid_number",
        "position": 1
      },
      {
        "id": "phone_3",
        "raw_number": "+1 (415) 555-0000",
        "sanitized_number": "+14155550000",
        "type": "work_hq",
        "confidence": "high",
        "status": "valid_number",
        "position": 2
      }
    ],
    "organization_id": "org456"
  }
}
```

### Phone Object Fields

| Field | Description | Use |
|-------|-------------|-----|
| `raw_number` | Formatted with hyphens/spaces | Display to user |
| `sanitized_number` | Digits only, E.164 format | **Use for dialing** |
| `type` | Phone type classification | Priority sorting |
| `confidence` | high, medium, low | Filter quality |
| `status` | valid_number, invalid, etc. | Verify before dial |
| `dnc_status` | not_on_dnc, on_dnc | Compliance check |
| `position` | Array index | Priority order |

---

## FastAPI Webhook Implementation

### 1. Create Webhook Router

File: `backend/app/api/routes/webhooks.py`

```python
"""Webhook endpoints for external service callbacks.

PHONES ARE GOLD! The Apollo webhook receives phone data asynchronously.
This is the ONLY way to get mobile/direct phone numbers from Apollo.
"""

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models for Apollo Webhook
# =============================================================================

class ApolloPhoneData(BaseModel):
    """Phone number data from Apollo webhook."""
    id: str | None = None
    raw_number: str | None = None
    sanitized_number: str | None = None
    type: str | None = None  # work_direct, mobile, work, work_hq
    position: int | None = None
    status: str | None = None  # valid_number, invalid
    dnc_status: str | None = None  # not_on_dnc, on_dnc
    confidence: str | None = None  # high, medium, low


class ApolloWebhookPayload(BaseModel):
    """Apollo webhook payload for phone enrichment."""
    person: dict[str, Any] | None = None


# =============================================================================
# Signature Verification
# =============================================================================

def verify_apollo_signature(body: bytes, signature: str | None) -> bool:
    """
    Verify Apollo webhook signature for security.

    Apollo signs webhooks with HMAC-SHA256. In production,
    always verify to prevent spoofed requests.
    """
    if not signature:
        logger.warning("Apollo webhook received without signature")
        return settings.environment == "development"

    if not settings.apollo_webhook_secret:
        logger.warning("Apollo webhook secret not configured")
        return settings.environment == "development"

    expected = hmac.new(
        settings.apollo_webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, f"sha256={expected}")


# =============================================================================
# Webhook Endpoint
# =============================================================================

@router.post("/apollo/phone-reveal")
async def apollo_phone_webhook(request: Request) -> dict[str, Any]:
    """
    Receive phone number data from Apollo asynchronously.

    PHONES ARE GOLD! This webhook is the ONLY way to get mobile/direct
    phones from Apollo. Without this, we only get employer/HQ phones.

    Flow:
    1. Our app calls Apollo /people/match with reveal_phone_number=true
    2. Apollo returns 200 with basic info + employer phone immediately
    3. Apollo verifies mobile/direct phones (takes 2-10 minutes)
    4. Apollo POSTs to THIS webhook with full phone data
    5. We update the lead record with verified phone numbers

    Security: Validate webhook signature in production!
    """
    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("x-apollo-signature")

    # Verify signature (critical for production!)
    if not verify_apollo_signature(body, signature):
        logger.error("Invalid Apollo webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        import json
        data = json.loads(body)
        person = data.get("person", {})
    except Exception as e:
        logger.error(f"Failed to parse Apollo webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Extract phone data - PHONES ARE GOLD!
    phone_numbers = person.get("phone_numbers", [])
    email = person.get("email")
    person_id = person.get("id")

    if not phone_numbers:
        logger.info(f"Apollo webhook for {email}: no phone numbers delivered")
        return {"status": "received", "phones_found": 0}

    # Extract best phones by type (priority: direct > mobile > work)
    direct_phone = None
    mobile_phone = None
    work_phone = None
    company_phone = None

    for phone in phone_numbers:
        ptype = (phone.get("type") or "").lower()
        number = phone.get("sanitized_number") or phone.get("raw_number")
        confidence = phone.get("confidence", "").lower()
        status = phone.get("status", "").lower()

        # Skip invalid numbers
        if status == "invalid" or confidence == "low":
            continue

        if "direct" in ptype and not direct_phone:
            direct_phone = number
        elif ptype == "mobile" and not mobile_phone:
            mobile_phone = number
        elif "work" in ptype and "direct" not in ptype and "hq" not in ptype and not work_phone:
            work_phone = number
        elif "hq" in ptype and not company_phone:
            company_phone = number

    # Determine best phone for BDR (PHONES ARE GOLD!)
    best_phone = direct_phone or mobile_phone or work_phone or company_phone

    # Log success
    logger.info(
        f"Apollo webhook for {email}: "
        f"direct={direct_phone}, mobile={mobile_phone}, "
        f"work={work_phone}, company={company_phone}, best={best_phone}"
    )

    # TODO: Update lead record in database with phone data
    # Example:
    # await supabase_client.update_lead_phones(
    #     email=email,
    #     direct_phone=direct_phone,
    #     mobile_phone=mobile_phone,
    #     work_phone=work_phone,
    #     company_phone=company_phone,
    #     phone_source="apollo_webhook",
    # )

    # TODO: Optionally sync to HubSpot
    # await hubspot_client.update_contact_phone(
    #     email=email,
    #     phone=direct_phone or mobile_phone or work_phone,
    #     mobilephone=mobile_phone,
    # )

    return {
        "status": "received",
        "email": email,
        "person_id": person_id,
        "phones_found": len(phone_numbers),
        "direct_phone": bool(direct_phone),
        "mobile_phone": bool(mobile_phone),
    }
```

### 2. Add Configuration

File: `backend/app/core/config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Apollo Webhooks (PHONES ARE GOLD!)
    apollo_webhook_secret: str = Field(
        default="",
        description="Secret for validating Apollo webhook signatures"
    )
    apollo_webhook_url: str = Field(
        default="",
        description="Public URL for Apollo callbacks: https://api.yourdomain.com/api/webhooks/apollo/phone-reveal"
    )
```

### 3. Register Router

File: `backend/app/main.py`

```python
from app.api.routes import webhooks

# Add webhook routes
app.include_router(webhooks.router, prefix="/api")
```

### 4. Update Apollo Client

File: `backend/app/services/enrichment/apollo.py`

```python
async def enrich_contact(
    self,
    email: str,
    reveal_phone: bool = True,
    webhook_url: str | None = None,
) -> dict[str, Any] | None:
    """
    Enrich a contact by email address.

    PHONES ARE GOLD! For full phone enrichment (mobile/direct), you MUST
    provide a webhook_url. Without it, Apollo rejects the request.

    The immediate response only includes employer/HQ phone.
    Mobile and direct phones are delivered asynchronously to your webhook
    2-10 minutes after the initial request.
    """
    # Use configured webhook URL if not provided
    if reveal_phone:
        webhook_url = webhook_url or settings.apollo_webhook_url
        if not webhook_url:
            raise ValueError(
                "webhook_url is REQUIRED for phone enrichment. "
                "Set APOLLO_WEBHOOK_URL in environment or pass explicitly."
            )

    payload: dict[str, Any] = {
        "email": email,
        "reveal_personal_emails": False,
        "reveal_phone_number": reveal_phone,
    }

    if webhook_url:
        payload["webhook_url"] = webhook_url

    response = await self._make_request("POST", "/people/match", payload)
    # ... rest of implementation
```

---

## HubSpot Phone Sync

### Phone Property Mapping

| Apollo Field | HubSpot Property | Notes |
|--------------|------------------|-------|
| `work_direct` phone | `phone` | Primary contact number |
| `mobile` phone | `mobilephone` | Secondary number |
| `work` phone | `phone` | Falls back to primary |
| `work_hq` phone | `phone` | Company switchboard |

### Batch Upsert Example

```python
from hubspot import HubSpot
from hubspot.crm.contacts import BatchInputSimplePublicObjectBatchInput

client = HubSpot(access_token=settings.hubspot_access_token)

# Sync Apollo phones to HubSpot
inputs = [
    {
        "id": "john@company.com",
        "idProperty": "email",
        "properties": {
            "phone": "+14155551234",       # work_direct from Apollo
            "mobilephone": "+14155559999"   # mobile from Apollo
        }
    }
]

batch_input = BatchInputSimplePublicObjectBatchInput(inputs=inputs)
response = client.crm.contacts.batch_api.upsert(
    batch_input_simple_public_object_batch_input=batch_input
)
```

### Rate Limits

- **Batch size:** 100 contacts max per request
- **Rate limit:** 110 requests per 10 seconds
- **Best practice:** Use batch upsert with 100ms delays between batches

---

## Verification Checklist

Use this checklist to verify phone enrichment is correctly configured:

### Apollo Configuration
- [ ] `reveal_phone_number=True` is set in `enrich_contact()`
- [ ] `webhook_url` is provided when `reveal_phone=True`
- [ ] `APOLLO_WEBHOOK_URL` environment variable is set
- [ ] `APOLLO_WEBHOOK_SECRET` is set for signature verification
- [ ] Webhook endpoint is publicly accessible (not localhost)

### Webhook Implementation
- [ ] `POST /api/webhooks/apollo/phone-reveal` endpoint exists
- [ ] Signature verification is implemented
- [ ] Phone extraction handles all types (direct, mobile, work, work_hq)
- [ ] Database update implemented for phone data
- [ ] Logging captures phone delivery success/failure

### Tests
- [ ] `pytest tests/unit/test_apollo_client.py -v -k phone` passes
- [ ] Webhook endpoint unit tests exist
- [ ] Integration test with real Apollo API (staging)

### Monitoring
- [ ] Track `apollo_phone_webhook_received` metric
- [ ] Track `leads_with_direct_phone` percentage
- [ ] Alert if phone enrichment rate drops below 40%

---

## Troubleshooting

### "Please add a valid 'webhook_url' parameter"

**Cause:** `reveal_phone_number=true` but no webhook URL
**Fix:** Add `APOLLO_WEBHOOK_URL` to environment and pass to enrichment

### Empty phone_numbers array

**Cause 1:** `reveal_phone_number` not set (defaults to false)
**Fix:** Ensure `reveal_phone_number: True` in payload

**Cause 2:** Contact has no phone data in Apollo
**Fix:** Use Harvester fallback phones, flag for manual research

### Webhook not receiving data

**Cause 1:** URL not publicly accessible (localhost)
**Fix:** Use ngrok for local dev, deploy to public server for prod

**Cause 2:** Firewall blocking Apollo IPs
**Fix:** Whitelist Apollo's IP ranges

**Cause 3:** SSL/TLS issues
**Fix:** Ensure valid HTTPS certificate

### Phones taking too long

**Expected:** 2-10 minutes for webhook delivery
**If longer:** Apollo may be rate-limited or verifying numbers

---

## Quick Reference

```python
# CORRECT: Full phone enrichment
from app.services.enrichment.apollo import apollo_client

result = await apollo_client.enrich_contact(
    email="john@company.com",
    reveal_phone=True,
    webhook_url="https://api.yourdomain.com/api/webhooks/apollo/phone-reveal"
)

# Immediate response: only employer phone
print(result["phone_numbers"])  # [{"type": "work_hq", ...}]

# Full phones arrive via webhook 2-10 minutes later
# Check your webhook endpoint logs for delivery

# Access extracted phones (from immediate response)
print(result["direct_phone"])   # Likely None (delivered via webhook)
print(result["mobile_phone"])   # Likely None (delivered via webhook)
print(result["work_phone"])     # Likely None (delivered via webhook)

# The webhook will have the full data:
# {
#   "direct_phone": "+14155551234",
#   "mobile_phone": "+14155559999",
#   "work_phone": "+14155550000"
# }
```

---

## History

| Date | Change | Notes |
|------|--------|-------|
| 2025-01-29 | Deep research verification | Confirmed webhook is MANDATORY |
| 2025-01-29 | Added FastAPI webhook impl | Complete implementation guide |
| 2025-01-29 | Added HubSpot sync guide | Property mapping and batch API |
| 2025-01-29 | Added troubleshooting | Common issues and fixes |

---

> **Remember: PHONES ARE GOLD!**
>
> Without proper webhook implementation, you're only getting employer phones.
> Implement the webhook to unlock mobile and direct dial numbers.
>
> More phones → More dials → More conversations → More deals → Food on the table.
