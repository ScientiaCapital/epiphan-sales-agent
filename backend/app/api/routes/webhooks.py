"""Apollo webhook endpoint for async phone delivery.

PHONES ARE GOLD! Apollo delivers mobile/direct phones asynchronously.
This webhook receives them 2-10 minutes after the initial enrichment request.

More phones = More dials = More conversations = More deals = Food on the table for Tim.
"""

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class ApolloPhoneWebhookPayload(BaseModel):
    """Payload from Apollo phone reveal webhook.

    Apollo sends phone numbers asynchronously after initial enrichment.
    This may include mobile and direct dial phones not available in sync response.
    """

    person_id: str | None = None
    email: str | None = None
    phone_numbers: list[dict[str, Any]] = []
    # Apollo may include additional fields
    first_name: str | None = None
    last_name: str | None = None
    organization_name: str | None = None


class WebhookResponse(BaseModel):
    """Standard webhook response."""

    status: str
    phones_received: int = 0
    lead_updated: bool = False


def verify_apollo_signature(body: bytes, signature: str | None) -> bool:
    """
    Verify Apollo webhook signature using HMAC-SHA256.

    Apollo signs webhooks with your webhook secret.
    ALWAYS verify in production to prevent spoofed requests.

    Args:
        body: Raw request body bytes
        signature: Signature from x-apollo-signature header

    Returns:
        True if signature is valid, False otherwise
    """
    if not settings.apollo_webhook_secret:
        # No secret configured - allow in development, warn in production
        if settings.environment == "production":
            logger.warning("Apollo webhook secret not configured in production!")
            return False
        return True

    if not signature:
        return False

    expected = hmac.new(
        settings.apollo_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    # Handle both with and without prefix
    sig_to_check = signature
    if signature.startswith("sha256="):
        sig_to_check = signature[7:]

    return hmac.compare_digest(sig_to_check, expected)


def extract_phones_from_payload(
    phone_numbers: list[dict[str, Any]],
) -> dict[str, str | None]:
    """
    Extract typed phone numbers from Apollo phone array.

    PHONES ARE GOLD! Priority:
    1. Direct dial (work_direct) - Best: reaches decision-maker directly
    2. Mobile - Good: personal, high answer rate
    3. Work line (work) - OK: may go to voicemail/assistant

    Args:
        phone_numbers: List of phone objects from Apollo

    Returns:
        Dict with direct_phone, mobile_phone, work_phone
    """
    result: dict[str, str | None] = {
        "direct_phone": None,
        "mobile_phone": None,
        "work_phone": None,
    }

    for phone in phone_numbers:
        ptype = (phone.get("type") or "").lower()
        number = phone.get("sanitized_number") or phone.get("number")

        if not number:
            continue

        # Direct dial - THE GOLD
        if "direct" in ptype and not result["direct_phone"]:
            result["direct_phone"] = number
        # Mobile - also valuable
        elif ptype == "mobile" and not result["mobile_phone"]:
            result["mobile_phone"] = number
        # Work line (not direct, not HQ)
        elif (
            "work" in ptype
            and "direct" not in ptype
            and "hq" not in ptype
            and not result["work_phone"]
        ):
            result["work_phone"] = number

    return result


async def update_lead_phones(
    email: str,
    person_id: str | None,
    phone_numbers: list[dict[str, Any]],
) -> bool:
    """
    Store phone numbers from webhook LOCALLY (not to HubSpot yet).

    PHONES ARE GOLD! This stores phones in apollo_phone_webhooks table
    with synced_to_hubspot=FALSE. HubSpot sync requires explicit approval.

    Flow:
    1. Apollo webhook delivers phones
    2. Store locally (this function)
    3. Admin reviews pending phones
    4. Admin approves → sync to HubSpot

    Args:
        email: Lead email address
        person_id: Apollo person ID
        phone_numbers: List of phone objects from Apollo

    Returns:
        True if stored successfully
    """
    phones = extract_phones_from_payload(phone_numbers)

    # Log the phones we received - PHONES ARE GOLD!
    logger.info(
        f"Storing phones for {email}: "
        f"direct={phones['direct_phone']}, "
        f"mobile={phones['mobile_phone']}, "
        f"work={phones['work_phone']}"
    )

    # Store LOCALLY - NOT synced to HubSpot until approved
    try:
        from app.services.database.supabase_client import supabase_client

        supabase_client.store_apollo_phone_webhook(
            email=email,
            person_id=person_id,
            direct_phone=phones["direct_phone"],
            mobile_phone=phones["mobile_phone"],
            work_phone=phones["work_phone"],
            raw_phones=phone_numbers,
        )
        logger.info(f"Phones stored locally for {email} (pending HubSpot approval)")
        return True

    except ValueError as e:
        # Supabase not configured - log warning but don't fail webhook
        logger.warning(f"Supabase not configured, phones logged but not persisted: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to store phones for {email}: {e}")
        return False


@router.post("/apollo/phone-reveal", response_model=WebhookResponse)
async def apollo_phone_webhook(request: Request) -> WebhookResponse:
    """
    Receive async phone number delivery from Apollo.

    PHONES ARE GOLD! Apollo delivers mobile/direct phones asynchronously,
    typically 2-10 minutes after the initial enrichment request.

    This endpoint:
    1. Validates the webhook signature (HMAC-SHA256)
    2. Extracts phone numbers from payload
    3. Updates the lead record with new phones
    4. Optionally syncs to HubSpot

    Configure APOLLO_WEBHOOK_SECRET in .env for production security.

    Returns:
        WebhookResponse with status and phone count
    """
    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("x-apollo-signature")

    # Verify signature
    if not verify_apollo_signature(body, signature):
        logger.warning("Invalid Apollo webhook signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse payload
    try:
        payload = ApolloPhoneWebhookPayload(**(await request.json()))
    except Exception as e:
        logger.error(f"Failed to parse Apollo webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload format") from e

    # Extract phone data
    email = payload.email
    phone_numbers = payload.phone_numbers

    if not email:
        logger.warning("Apollo webhook missing email identifier")
        return WebhookResponse(status="ignored", phones_received=0)

    if not phone_numbers:
        logger.info(f"Apollo webhook for {email}: no phones delivered")
        return WebhookResponse(status="received", phones_received=0)

    # Log the gold we just received!
    phone_types = [p.get("type", "unknown") for p in phone_numbers]
    logger.info(
        f"PHONES ARE GOLD! Received {len(phone_numbers)} phones for {email}: {phone_types}"
    )

    # Store phones LOCALLY (not to HubSpot until approved)
    lead_updated = await update_lead_phones(email, payload.person_id, phone_numbers)

    return WebhookResponse(
        status="processed",
        phones_received=len(phone_numbers),
        lead_updated=lead_updated,
    )


# =============================================================================
# HubSpot Sync Approval Endpoints
# =============================================================================


class PendingPhoneRecord(BaseModel):
    """Phone record pending HubSpot sync approval."""

    id: int
    email: str
    person_id: str | None = None
    direct_phone: str | None = None
    mobile_phone: str | None = None
    work_phone: str | None = None
    received_at: str
    synced_to_hubspot: bool = False


class PendingPhonesResponse(BaseModel):
    """Response with pending phone records."""

    pending_count: int
    phones: list[PendingPhoneRecord]


class SyncApprovalRequest(BaseModel):
    """Request to approve HubSpot sync for specific phone records."""

    phone_ids: list[int]


class SyncResult(BaseModel):
    """Result of a single phone sync."""

    phone_id: int
    email: str
    success: bool
    error: str | None = None


class SyncApprovalResponse(BaseModel):
    """Response after approving HubSpot sync."""

    approved_count: int
    synced_count: int
    failed_count: int
    results: list[SyncResult]


@router.get("/phones/pending", response_model=PendingPhonesResponse)
async def get_pending_phones() -> PendingPhonesResponse:
    """
    Get phone records pending HubSpot sync approval.

    PHONES ARE GOLD! This shows phones received via Apollo webhook
    that have NOT been synced to HubSpot yet.

    Use POST /phones/approve to sync selected records to HubSpot.

    Returns:
        List of pending phone records with their details
    """
    try:
        from app.services.database.supabase_client import supabase_client

        pending = supabase_client.get_unsynced_phones(limit=100)

        phones = [
            PendingPhoneRecord(
                id=p["id"],
                email=p["email"],
                person_id=p.get("person_id"),
                direct_phone=p.get("direct_phone"),
                mobile_phone=p.get("mobile_phone"),
                work_phone=p.get("work_phone"),
                received_at=p.get("received_at", ""),
                synced_to_hubspot=p.get("synced_to_hubspot", False),
            )
            for p in pending
        ]

        return PendingPhonesResponse(
            pending_count=len(phones),
            phones=phones,
        )

    except ValueError as e:
        logger.warning(f"Supabase not configured: {e}")
        return PendingPhonesResponse(pending_count=0, phones=[])


@router.post("/phones/approve", response_model=SyncApprovalResponse)
async def approve_hubspot_sync(request: SyncApprovalRequest) -> SyncApprovalResponse:
    """
    Approve and sync selected phone records to HubSpot.

    PHONES ARE GOLD! This syncs locally-stored phones to HubSpot CRM.
    Only approved records are synced - this prevents accidental data push.

    Args:
        request: List of phone_ids to approve and sync

    Returns:
        Sync results for each record
    """
    from app.services.database.supabase_client import supabase_client
    from app.services.integrations.hubspot.phone_sync import sync_phones_to_hubspot

    results: list[SyncResult] = []
    synced_count = 0
    failed_count = 0

    for phone_id in request.phone_ids:
        try:
            # Get the phone record
            phone_records = supabase_client.client.table("apollo_phone_webhooks").select("*").eq("id", phone_id).execute()

            if not phone_records.data:
                results.append(SyncResult(
                    phone_id=phone_id,
                    email="unknown",
                    success=False,
                    error="Record not found",
                ))
                failed_count += 1
                continue

            record = phone_records.data[0]
            email = record["email"]

            # Skip if already synced
            if record.get("synced_to_hubspot"):
                results.append(SyncResult(
                    phone_id=phone_id,
                    email=email,
                    success=True,
                    error="Already synced",
                ))
                continue

            # Sync to HubSpot
            sync_success = await sync_phones_to_hubspot(
                email=email,
                direct_phone=record.get("direct_phone"),
                mobile_phone=record.get("mobile_phone"),
                work_phone=record.get("work_phone"),
            )

            if sync_success:
                # Mark as synced in local DB
                supabase_client.mark_phone_synced(phone_id)
                synced_count += 1
                results.append(SyncResult(
                    phone_id=phone_id,
                    email=email,
                    success=True,
                ))
                logger.info(f"Synced phones to HubSpot for {email}")
            else:
                failed_count += 1
                results.append(SyncResult(
                    phone_id=phone_id,
                    email=email,
                    success=False,
                    error="HubSpot sync failed",
                ))

        except Exception as e:
            failed_count += 1
            results.append(SyncResult(
                phone_id=phone_id,
                email="unknown",
                success=False,
                error=str(e),
            ))
            logger.error(f"Failed to sync phone {phone_id}: {e}")

    return SyncApprovalResponse(
        approved_count=len(request.phone_ids),
        synced_count=synced_count,
        failed_count=failed_count,
        results=results,
    )


# =============================================================================
# Lead Harvester Webhook - Real-time Sync
# =============================================================================


class HarvesterLeadPayload(BaseModel):
    """Single lead from Harvester webhook push."""

    external_id: str
    source: str = "harvester"
    company_name: str
    industry: str | None = None
    employees: int | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    website: str | None = None
    harvester_score: float | None = None
    harvester_tier: str | None = None
    contact_name: str | None = None
    contact_title: str | None = None
    contact_email: str | None = None
    direct_phone: str | None = None
    work_phone: str | None = None
    mobile_phone: str | None = None
    company_phone: str | None = None
    tech_stack: list[str] | None = None
    raw_data: dict[str, Any] | None = None


class HarvesterPushPayload(BaseModel):
    """Payload from Lead Harvester webhook push."""

    source: str = "harvester"
    timestamp: str | None = None
    leads: list[HarvesterLeadPayload]


class HarvesterPushResponse(BaseModel):
    """Response to Harvester webhook push."""

    status: str  # "accepted" | "rejected"
    leads_received: int
    batch_id: str  # For tracking via /api/monitoring/batches/{id}
    message: str


def verify_harvester_signature(body: bytes, signature: str | None) -> bool:
    """
    Verify Lead Harvester webhook signature using HMAC-SHA256.

    Follows same pattern as Apollo verification for consistency.

    Args:
        body: Raw request body bytes
        signature: Signature from x-harvester-signature header

    Returns:
        True if signature is valid, False otherwise
    """
    if not settings.harvester_webhook_secret:
        # No secret configured - allow in development, warn in production
        if settings.environment == "production":
            logger.warning("Harvester webhook secret not configured in production!")
            return False
        logger.debug("Harvester signature skipped (dev mode, no secret configured)")
        return True

    if not signature:
        logger.warning("Missing x-harvester-signature header")
        return False

    expected = hmac.new(
        settings.harvester_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    # Handle both with and without prefix
    sig_to_check = signature
    if signature.startswith("sha256="):
        sig_to_check = signature[7:]

    return hmac.compare_digest(sig_to_check, expected)


@router.post("/harvester/lead-push", response_model=HarvesterPushResponse)
async def harvester_lead_push(request: Request) -> HarvesterPushResponse:
    """
    Receive real-time lead push from Lead Harvester.

    This endpoint enables automatic lead flow from Harvester without manual CSV exports.
    Leads are validated, stored, and queued for background enrichment/qualification.

    Security:
    - HMAC-SHA256 signature validation (set HARVESTER_WEBHOOK_SECRET in production)
    - Signature check is enforced in production, permissive in development

    Processing:
    1. Validate webhook signature
    2. Parse and validate lead payload
    3. Store raw leads to Supabase (if configured)
    4. Queue background enrichment/qualification
    5. Return batch_id for tracking via /api/monitoring/batches/{id}

    Returns:
        HarvesterPushResponse with status and batch_id for tracking
    """
    from datetime import datetime, timezone

    from app.api.routes.monitoring import register_batch
    from app.services.enrichment.pipeline import queue_harvester_batch

    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("x-harvester-signature")

    # Verify signature
    if not verify_harvester_signature(body, signature):
        logger.warning("Invalid Harvester webhook signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse payload
    try:
        payload = HarvesterPushPayload(**(await request.json()))
    except Exception as e:
        logger.error(f"Failed to parse Harvester webhook payload: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid payload format: {e}") from e

    # Validate we have leads
    if not payload.leads:
        return HarvesterPushResponse(
            status="accepted",
            leads_received=0,
            batch_id="",
            message="No leads in payload",
        )

    # Generate batch ID
    timestamp = payload.timestamp or datetime.now(timezone.utc).isoformat()
    batch_id = f"harv_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{len(payload.leads)}"

    # Register batch for monitoring
    register_batch(batch_id, len(payload.leads))

    # Log the push
    logger.info(
        f"Harvester push received: {len(payload.leads)} leads, batch_id={batch_id}",
        extra={
            "batch_id": batch_id,
            "source": payload.source,
            "lead_count": len(payload.leads),
            "timestamp": timestamp,
        },
    )

    # Queue for background processing (non-blocking)
    try:
        await queue_harvester_batch(
            batch_id=batch_id,
            leads=[lead.model_dump() for lead in payload.leads],
        )
    except Exception as e:
        logger.error(f"Failed to queue Harvester batch: {e}")
        # Still return accepted - we can retry from stored data
        return HarvesterPushResponse(
            status="accepted",
            leads_received=len(payload.leads),
            batch_id=batch_id,
            message=f"Leads received but queue failed: {e}. Check batch status for retry.",
        )

    return HarvesterPushResponse(
        status="accepted",
        leads_received=len(payload.leads),
        batch_id=batch_id,
        message=f"Leads queued for processing. Track at /api/monitoring/batches/{batch_id}",
    )
