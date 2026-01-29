"""Sync Apollo phone data to HubSpot contacts.

PHONES ARE GOLD! This module ensures all enriched phone numbers reach HubSpot
for BDR calling. More phones = More dials = More conversations = More deals.

HubSpot phone properties:
- phone: Primary phone (we use best available: direct > mobile > work)
- mobilephone: Mobile number specifically
- apollo_direct_dial: Custom property for direct dial (create in HubSpot first)

Note: HubSpot SDK is synchronous, so we use asyncio.to_thread() to avoid blocking.
"""

import asyncio
import logging
from typing import Any

from app.core.config import settings
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput
from hubspot.crm.contacts.exceptions import ApiException

logger = logging.getLogger(__name__)


def _sync_hubspot_search(client: HubSpot, email: str) -> str | None:
    """Synchronous HubSpot search - called via asyncio.to_thread()."""
    search_response = client.crm.contacts.search_api.do_search(
        public_object_search_request={
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": email,
                        }
                    ]
                }
            ],
            "limit": 1,
        }
    )
    if search_response.results:
        return search_response.results[0].id
    return None


def _sync_hubspot_update(
    client: HubSpot, contact_id: str, properties: dict[str, Any]
) -> bool:
    """Synchronous HubSpot update - called via asyncio.to_thread()."""
    client.crm.contacts.basic_api.update(
        contact_id=contact_id,
        simple_public_object_input=SimplePublicObjectInput(properties=properties),
    )
    return True


async def sync_phones_to_hubspot(
    email: str,
    direct_phone: str | None = None,
    mobile_phone: str | None = None,
    work_phone: str | None = None,
) -> bool:
    """
    Sync phone numbers to HubSpot contact.

    PHONES ARE GOLD! This function updates HubSpot contacts with phone numbers
    from Apollo enrichment, prioritizing direct dials for BDR outreach.

    HubSpot properties updated:
    - phone: Primary phone (best available: direct > mobile > work)
    - mobilephone: Mobile number if available
    - apollo_direct_dial: Custom property for direct dial (must exist in HubSpot)

    Args:
        email: Contact email address to look up
        direct_phone: Direct dial phone number (best)
        mobile_phone: Mobile phone number (good)
        work_phone: Work phone number (fallback)

    Returns:
        True if sync succeeded, False otherwise
    """
    if not settings.hubspot_access_token:
        logger.warning("HubSpot access token not configured - skipping phone sync")
        return False

    # Check if we have any phones to sync
    if not any([direct_phone, mobile_phone, work_phone]):
        logger.debug(f"No phones to sync for {email}")
        return True

    client = HubSpot(access_token=settings.hubspot_access_token)

    # Find contact by email (use asyncio.to_thread to avoid blocking)
    try:
        contact_id = await asyncio.to_thread(_sync_hubspot_search, client, email)

        if not contact_id:
            logger.info(f"No HubSpot contact found for {email}")
            return False

    except ApiException as e:
        logger.error(f"HubSpot search failed for {email}: {e}")
        return False

    # Build update properties
    # PHONES ARE GOLD - prioritize direct dial for primary phone field
    best_phone = direct_phone or mobile_phone or work_phone

    properties: dict[str, Any] = {}

    if best_phone:
        properties["phone"] = best_phone

    if mobile_phone:
        properties["mobilephone"] = mobile_phone

    if direct_phone:
        # Custom property - must be created in HubSpot first
        # If property doesn't exist, HubSpot will return an error
        # but we log and continue
        properties["apollo_direct_dial"] = direct_phone

    if not properties:
        logger.debug(f"No phone properties to update for {email}")
        return True

    # Update contact (use asyncio.to_thread to avoid blocking)
    try:
        await asyncio.to_thread(_sync_hubspot_update, client, contact_id, properties)
        logger.info(
            f"PHONES ARE GOLD! Updated HubSpot contact {contact_id} ({email}) "
            f"with phones: {list(properties.keys())}"
        )
        return True

    except ApiException as e:
        # Check if it's a property not found error for apollo_direct_dial
        if "apollo_direct_dial" in str(e) and "property" in str(e).lower():
            logger.warning(
                "Custom property 'apollo_direct_dial' not found in HubSpot. "
                "Create it in HubSpot Settings > Properties > Contact Properties. "
                "Retrying without custom property..."
            )
            # Retry without the custom property
            properties.pop("apollo_direct_dial", None)
            if properties:
                try:
                    await asyncio.to_thread(
                        _sync_hubspot_update, client, contact_id, properties
                    )
                    logger.info(
                        f"Updated HubSpot contact {contact_id} ({email}) "
                        f"with standard phone properties"
                    )
                    return True
                except ApiException as retry_error:
                    logger.error(
                        f"HubSpot update failed on retry for {contact_id}: {retry_error}"
                    )
                    return False
        else:
            logger.error(f"HubSpot update failed for {contact_id}: {e}")
            return False

    return True


async def batch_sync_phones_to_hubspot(
    phone_records: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Batch sync multiple phone records to HubSpot.

    PHONES ARE GOLD! This function efficiently syncs multiple phone records
    in a single batch for webhook processing or batch enrichment.

    Args:
        phone_records: List of dicts with email, direct_phone, mobile_phone, work_phone

    Returns:
        Dict with success_count and failure_count
    """
    results = {"success_count": 0, "failure_count": 0}

    for record in phone_records:
        success = await sync_phones_to_hubspot(
            email=record.get("email", ""),
            direct_phone=record.get("direct_phone"),
            mobile_phone=record.get("mobile_phone"),
            work_phone=record.get("work_phone"),
        )

        if success:
            results["success_count"] += 1
        else:
            results["failure_count"] += 1

    logger.info(
        f"Batch phone sync complete: {results['success_count']} succeeded, "
        f"{results['failure_count']} failed"
    )

    return results
