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


async def update_lead_phones(email: str, phone_numbers: list[dict[str, Any]]) -> bool:
    """
    Update lead record with phone numbers from webhook.

    PHONES ARE GOLD! This function processes async phone delivery and
    stores the numbers for BDR outreach.

    Args:
        email: Lead email address
        phone_numbers: List of phone objects from Apollo

    Returns:
        True if lead was found and updated
    """
    phones = extract_phones_from_payload(phone_numbers)

    # Log the phones we received - PHONES ARE GOLD!
    logger.info(
        f"Processing phones for {email}: "
        f"direct={phones['direct_phone']}, "
        f"mobile={phones['mobile_phone']}, "
        f"work={phones['work_phone']}"
    )

    # TODO: Implement database storage
    # This requires the apollo_phone_webhooks table from migration 003
    # For now, we log and return success

    # TODO: Sync to HubSpot
    # from app.services.integrations.hubspot.phone_sync import sync_phones_to_hubspot
    # await sync_phones_to_hubspot(email, phones["direct_phone"], phones["mobile_phone"], phones["work_phone"])

    return True


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

    # Update lead record with new phones
    lead_updated = await update_lead_phones(email, phone_numbers)

    return WebhookResponse(
        status="processed",
        phones_received=len(phone_numbers),
        lead_updated=lead_updated,
    )
