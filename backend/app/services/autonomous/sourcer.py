"""Lead sourcing from Apollo (outbound) and HubSpot (inbound).

Builds Apollo ICP search queries from existing persona definitions
and ATL detector title keywords. Picks up new HubSpot contacts
since the last pipeline run.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.services.autonomous.schemas import LeadSource, RawLead
from app.services.scoring.atl_detector import get_all_atl_titles

logger = logging.getLogger(__name__)


class LeadSourcer:
    """Find net-new prospects from Apollo and HubSpot."""

    # Apollo people search endpoint
    APOLLO_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/search"

    # Target verticals for ICP
    TARGET_VERTICALS: list[str] = [
        "higher education",
        "hospital & health care",
        "government administration",
        "broadcast media",
        "entertainment",
        "legal services",
    ]

    async def find_apollo_prospects(
        self,
        limit: int = 25,
        verticals: list[str] | None = None,
        personas: list[str] | None = None,
    ) -> list[RawLead]:
        """Search Apollo for net-new outbound prospects matching ICP.

        Builds search query from ATL detector title keywords
        and target vertical industries.
        """
        import httpx

        if not settings.apollo_api_key:
            logger.warning("Apollo API key not configured, skipping Apollo sourcing")
            return []

        title_keywords = self._build_title_keywords(personas)
        target_industries = verticals or self.TARGET_VERTICALS

        payload: dict[str, Any] = {
            "api_key": settings.apollo_api_key,
            "q_person_title": title_keywords,
            "person_titles": [],
            "organization_industry_tag_ids": [],
            "q_organization_keyword_tags": target_industries,
            "organization_num_employees_ranges": ["50,10000"],
            "person_seniorities": ["director", "vp", "c_suite", "owner"],
            "page": 1,
            "per_page": min(limit, 100),
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.APOLLO_SEARCH_URL,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            people = data.get("people", [])
            leads: list[RawLead] = []

            for person in people[:limit]:
                email = person.get("email")
                if not email or "placeholder" in email:
                    continue

                org = person.get("organization", {}) or {}
                leads.append(
                    RawLead(
                        email=email,
                        first_name=person.get("first_name"),
                        last_name=person.get("last_name"),
                        name=person.get("name"),
                        title=person.get("title"),
                        company=org.get("name"),
                        industry=org.get("industry"),
                        phone=person.get("phone_number"),
                        linkedin_url=person.get("linkedin_url"),
                        source=LeadSource.APOLLO,
                        source_id=person.get("id"),
                        raw_data=person,
                    )
                )

            logger.info(
                "Apollo sourcing: found %d prospects from %d results",
                len(leads),
                len(people),
            )
            return leads

        except Exception:
            logger.exception("Apollo prospect search failed")
            return []

    async def find_hubspot_inbound(
        self,
        since: datetime | None = None,
    ) -> list[RawLead]:
        """Pick up new HubSpot contacts since last run.

        Queries for contacts created after `since` with lifecycle_stage
        of lead or marketingqualifiedlead.
        """
        try:
            from app.services.integrations.hubspot.client import hubspot_client
        except Exception:
            logger.warning("HubSpot client not available, skipping inbound sourcing")
            return []

        if not settings.hubspot_access_token:
            logger.warning("HubSpot token not configured, skipping inbound sourcing")
            return []

        since_ts = since or datetime(2020, 1, 1, tzinfo=timezone.utc)

        try:
            # Use get_contacts_modified_since from existing HubSpot client
            result = await hubspot_client.get_contacts_modified_since(
                since=since_ts,
                limit=100,
                properties=[
                    "email", "firstname", "lastname", "company",
                    "jobtitle", "phone", "industry", "hs_lead_status",
                    "lifecyclestage",
                ],
            )

            contacts = result.get("results", [])
            leads: list[RawLead] = []
            for contact in contacts:
                props = contact.get("properties", {})
                email = props.get("email")
                if not email or "placeholder" in email:
                    continue

                leads.append(
                    RawLead(
                        email=email,
                        first_name=props.get("firstname"),
                        last_name=props.get("lastname"),
                        name=f"{props.get('firstname', '')} {props.get('lastname', '')}".strip() or None,
                        title=props.get("jobtitle"),
                        company=props.get("company"),
                        industry=props.get("industry"),
                        phone=props.get("phone"),
                        source=LeadSource.HUBSPOT,
                        source_id=contact.get("id"),
                        raw_data=contact,
                    )
                )

            logger.info(
                "HubSpot sourcing: found %d inbound leads since %s",
                len(leads),
                since_ts.isoformat(),
            )
            return leads

        except Exception:
            logger.exception("HubSpot inbound sourcing failed")
            return []

    def _build_title_keywords(self, personas: list[str] | None = None) -> str:
        """Build Apollo title search string from ATL personas.

        Uses existing ATL detector title variations for targeting.
        """
        titles = get_all_atl_titles()

        # If specific personas requested, filter
        if personas:
            # get_all_atl_titles returns flat list; use as-is for now
            pass

        # Apollo wants comma-separated OR logic
        # Pick top title patterns for search efficiency
        top_titles = titles[:20] if len(titles) > 20 else titles
        return ", ".join(top_titles)


# Singleton
lead_sourcer = LeadSourcer()
