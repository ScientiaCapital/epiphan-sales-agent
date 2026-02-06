"""Harvester-to-Lead mapper for Lead Harvester integration.

Maps Lead Harvester export data to Sales Agent Lead models
and handles phone number extraction/prioritization.

IMPORTANT: Phone numbers are GOLD for BDR outreach.
This module prioritizes phone extraction to maximize dial opportunities.
More phones = More dials = More conversations = More deals = Food on the table.
"""

from typing import Any

from app.data.lead_schemas import Lead


def map_harvester_to_lead(
    external_id: str,
    source: str,
    company_name: str,
    contact_email: str | None = None,
    contact_name: str | None = None,
    contact_title: str | None = None,
    industry: str | None = None,
    employees: int | None = None,  # noqa: ARG001 - Reserved for future Lead model expansion
    city: str | None = None,
    state: str | None = None,
    website: str | None = None,  # noqa: ARG001 - Reserved for future Lead model expansion
    direct_phone: str | None = None,
    work_phone: str | None = None,
    mobile_phone: str | None = None,
    company_phone: str | None = None,
) -> Lead:
    """
    Convert Harvester export data to Sales Agent Lead model.

    Args:
        external_id: Unique source ID (IPEDS UNITID, permit #, etc.)
        source: Data source (ipeds_higher_ed, cms_hospitals, etc.)
        company_name: Organization name
        contact_email: Contact email address
        contact_name: Contact full name
        contact_title: Job title
        industry: Industry/vertical
        employees: Employee count
        city: City
        state: State
        website: Company website
        direct_phone: Direct dial phone (BEST for BDR)
        work_phone: Office phone
        mobile_phone: Cell phone
        company_phone: Main switchboard

    Returns:
        Lead model instance for qualification agent
    """
    # Parse first/last name from contact_name
    first_name = None
    last_name = None
    if contact_name:
        name_parts = contact_name.strip().split()
        if len(name_parts) >= 1:
            first_name = name_parts[0]
        if len(name_parts) >= 2:
            last_name = " ".join(name_parts[1:])

    # Use best available phone (PHONES ARE GOLD!)
    best_phone = direct_phone or mobile_phone or work_phone or company_phone

    # Generate hubspot_id from harvester data
    hubspot_id = f"harvester_{source}_{external_id}"

    # Generate placeholder email if none provided
    email = contact_email or f"{external_id}@placeholder.harvester.local"

    return Lead(
        hubspot_id=hubspot_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        company=company_name,
        title=contact_title,
        phone=best_phone,  # Store best phone in lead
        city=city,
        state=state,
        industry=industry,
    )


def map_harvester_tier_to_score(
    tier: str | None = None,
    score: float | None = None,
) -> int:
    """
    Convert Harvester A/B/C/D tier to numeric score.

    If a numeric score is provided, use it directly.
    Otherwise, map the letter tier to a representative score.

    Args:
        tier: Letter tier (A/B/C/D) from Harvester
        score: Numeric score (0-100) from Harvester

    Returns:
        Numeric score 0-100 for comparison
    """
    # If we have a numeric score, use it
    if score is not None:
        return int(min(max(score, 0), 100))

    # Map letter tiers to representative scores
    tier_map = {
        "A": 85,  # High-quality leads
        "B": 65,  # Good leads
        "C": 45,  # Marginal leads
        "D": 20,  # Poor fit leads
    }

    if tier:
        tier_upper = tier.upper().strip()
        return tier_map.get(tier_upper, 0)

    return 0


def enrich_phone_numbers(
    apollo_data: dict[str, Any] | None,
    harvester_direct: str | None = None,
    harvester_mobile: str | None = None,
    harvester_work: str | None = None,
    harvester_company: str | None = None,
    clay_phones: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Extract and prioritize phone numbers from Apollo, Harvester, and Clay.

    PHONES ARE GOLD FOR BDR OUTREACH!
    Priority order: Apollo (primary) > Harvester (secondary) > Clay (tertiary)

    Phone type priority (best to worst):
    1. Direct dial - Best: reaches decision-maker directly
    2. Mobile - Good: personal, high answer rate
    3. Work line - OK: may go to voicemail/assistant
    4. Company switchboard - Fallback: requires asking for person

    Args:
        apollo_data: Enrichment data from Apollo.io
        harvester_direct: Direct phone from Harvester
        harvester_mobile: Mobile phone from Harvester
        harvester_work: Work phone from Harvester
        harvester_company: Company phone from Harvester
        clay_phones: Phone list from Clay [{number, type, provider}]

    Returns:
        Dict with phone numbers and source tracking:
        {
            "direct_phone": str | None,
            "mobile_phone": str | None,
            "work_phone": str | None,
            "company_phone": str | None,
            "best_phone": str | None,
            "phone_source": str | None,
        }
    """
    result: dict[str, Any] = {
        "direct_phone": None,
        "mobile_phone": None,
        "work_phone": None,
        "company_phone": None,
        "best_phone": None,
        "phone_source": None,
    }

    # Track where we got phones from
    sources_used: list[str] = []

    # Extract phones from Apollo data (PRIMARY SOURCE - most reliable)
    if apollo_data:
        phones = apollo_data.get("phone_numbers", [])

        for phone in phones:
            number = phone.get("sanitized_number") or phone.get("number")
            if not number:
                continue

            phone_type = (phone.get("type") or "").lower()

            # Map Apollo phone types to our categories
            if "direct" in phone_type and not result["direct_phone"]:
                result["direct_phone"] = number
                sources_used.append("apollo")
            elif phone_type == "mobile" and not result["mobile_phone"]:
                result["mobile_phone"] = number
                sources_used.append("apollo")
            elif "work" in phone_type and "hq" not in phone_type and not result["work_phone"]:
                result["work_phone"] = number
                sources_used.append("apollo")

        # Get company switchboard from organization data
        org_phone = apollo_data.get("organization", {}).get("phone")
        if org_phone and not result["company_phone"]:
            result["company_phone"] = org_phone
            sources_used.append("apollo")

    # Fill gaps with Harvester data (SECONDARY SOURCE)
    if harvester_direct and not result["direct_phone"]:
        result["direct_phone"] = harvester_direct
        sources_used.append("harvester")

    if harvester_mobile and not result["mobile_phone"]:
        result["mobile_phone"] = harvester_mobile
        sources_used.append("harvester")

    if harvester_work and not result["work_phone"]:
        result["work_phone"] = harvester_work
        sources_used.append("harvester")

    if harvester_company and not result["company_phone"]:
        result["company_phone"] = harvester_company
        sources_used.append("harvester")

    # Fill remaining gaps with Clay data (TERTIARY SOURCE — fallback)
    if clay_phones:
        for phone in clay_phones:
            number = phone.get("number", "").strip()
            if not number:
                continue
            phone_type = phone.get("type", "").lower()

            if phone_type == "work_direct" and not result["direct_phone"]:
                result["direct_phone"] = number
                sources_used.append("clay")
            elif phone_type == "mobile" and not result["mobile_phone"]:
                result["mobile_phone"] = number
                sources_used.append("clay")
            elif phone_type == "work" and not result["work_phone"]:
                result["work_phone"] = number
                sources_used.append("clay")
            elif phone_type == "work_hq" and not result["company_phone"]:
                result["company_phone"] = number
                sources_used.append("clay")

    # Determine best phone (PHONES ARE GOLD - priority matters!)
    result["best_phone"] = (
        result["direct_phone"]
        or result["mobile_phone"]
        or result["work_phone"]
        or result["company_phone"]
    )

    # Track source
    if sources_used:
        # Remove duplicates while preserving order
        unique_sources = list(dict.fromkeys(sources_used))
        result["phone_source"] = ",".join(unique_sources)

    return result


def get_best_phone(
    direct_phone: str | None = None,
    mobile_phone: str | None = None,
    work_phone: str | None = None,
    company_phone: str | None = None,
) -> str | None:
    """
    Return best available phone for BDR to call.

    PHONES ARE GOLD! Priority order:
    1. Direct dial - reaches decision-maker directly
    2. Mobile - personal, high answer rate
    3. Work line - may go to voicemail
    4. Company switchboard - requires asking for person

    Args:
        direct_phone: Direct dial number
        mobile_phone: Mobile number
        work_phone: Office line
        company_phone: Main switchboard

    Returns:
        Best available phone number or None
    """
    return direct_phone or mobile_phone or work_phone or company_phone
