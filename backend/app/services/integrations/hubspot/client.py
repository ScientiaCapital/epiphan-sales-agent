"""HubSpot CRM integration client."""

from datetime import datetime
from typing import Any

import httpx

from app.core.config import settings
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput


class HubSpotClient:
    """
    HubSpot CRM client for syncing leads and contacts.

    Handles:
    - Lead/contact sync (100k+ records)
    - Company data enrichment
    - Deal tracking
    - Activity logging
    """

    def __init__(self):
        self.client = HubSpot(access_token=settings.hubspot_access_token)
        self.portal_id = settings.hubspot_portal_id

    async def get_all_contacts(
        self,
        limit: int = 100,
        properties: list[str] | None = None,
        after: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch contacts with pagination support.

        For 100k+ leads, use pagination with after cursor.
        """
        default_properties = [
            "email",
            "firstname",
            "lastname",
            "company",
            "jobtitle",
            "phone",
            "linkedin",
            "city",
            "state",
            "country",
            "lifecyclestage",
            "hs_lead_status",
            "hubspot_owner_id",
            "createdate",
            "lastmodifieddate",
            "num_contacted_notes",
            "notes_last_contacted",
        ]

        props = properties or default_properties

        response = self.client.crm.contacts.basic_api.get_page(
            limit=limit,
            properties=props,
            after=after,
        )

        return {
            "results": [self._contact_to_dict(c) for c in response.results],
            "paging": response.paging.to_dict() if response.paging else None,
        }

    async def get_untouched_contacts(self, limit: int = 1000) -> list[dict[str, Any]]:
        """
        Find contacts with no outreach (prime BDR targets).

        Filters for:
        - No contacted notes
        - No last contacted date
        - Has email
        """
        # Use search API for filtering
        filter_groups = [
            {
                "filters": [
                    {
                        "propertyName": "num_contacted_notes",
                        "operator": "EQ",
                        "value": "0",
                    },
                    {
                        "propertyName": "email",
                        "operator": "HAS_PROPERTY",
                    },
                ]
            }
        ]

        response = self.client.crm.contacts.search_api.do_search(
            public_object_search_request={
                "filterGroups": filter_groups,
                "properties": [
                    "email",
                    "firstname",
                    "lastname",
                    "company",
                    "jobtitle",
                    "phone",
                ],
                "limit": limit,
            }
        )

        return [self._contact_to_dict(c) for c in response.results]

    async def get_contact_by_email(self, email: str) -> dict[str, Any] | None:
        """Fetch a single contact by email."""
        try:
            response = self.client.crm.contacts.basic_api.get_by_id(
                contact_id=email,
                id_property="email",
                properties=[
                    "email",
                    "firstname",
                    "lastname",
                    "company",
                    "jobtitle",
                ],
            )
            return self._contact_to_dict(response)
        except Exception:
            return None

    async def create_contact(self, contact_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new contact in HubSpot."""
        properties = {
            "email": contact_data.get("email"),
            "firstname": contact_data.get("first_name"),
            "lastname": contact_data.get("last_name"),
            "company": contact_data.get("company"),
            "jobtitle": contact_data.get("title"),
            "phone": contact_data.get("phone"),
        }

        # Remove None values
        properties = {k: v for k, v in properties.items() if v is not None}

        response = self.client.crm.contacts.basic_api.create(
            simple_public_object_input=SimplePublicObjectInput(properties=properties)
        )

        return self._contact_to_dict(response)

    async def update_contact(
        self, contact_id: str, properties: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing contact."""
        response = self.client.crm.contacts.basic_api.update(
            contact_id=contact_id,
            simple_public_object_input=SimplePublicObjectInput(properties=properties),
        )
        return self._contact_to_dict(response)

    async def get_companies(
        self, limit: int = 100, after: str | None = None
    ) -> dict[str, Any]:
        """Fetch companies with pagination."""
        response = self.client.crm.companies.basic_api.get_page(
            limit=limit,
            properties=[
                "name",
                "domain",
                "industry",
                "numberofemployees",
                "annualrevenue",
                "city",
                "state",
                "country",
            ],
            after=after,
        )

        return {
            "results": [self._company_to_dict(c) for c in response.results],
            "paging": response.paging.to_dict() if response.paging else None,
        }

    async def get_deals(
        self, limit: int = 100, after: str | None = None
    ) -> dict[str, Any]:
        """Fetch deals for win/loss analysis."""
        response = self.client.crm.deals.basic_api.get_page(
            limit=limit,
            properties=[
                "dealname",
                "dealstage",
                "amount",
                "closedate",
                "pipeline",
                "hubspot_owner_id",
                "hs_closed_won_reason",
                "hs_closed_lost_reason",
            ],
            after=after,
        )

        return {
            "results": [self._deal_to_dict(d) for d in response.results],
            "paging": response.paging.to_dict() if response.paging else None,
        }

    async def log_activity(
        self,
        contact_id: str,
        activity_type: str,
        body: str,
        timestamp: datetime | None = None,
    ) -> dict[str, Any]:
        """Log an engagement/activity on a contact."""
        engagement_data = {
            "engagement": {
                "type": activity_type.upper(),  # NOTE, EMAIL, CALL, MEETING
                "timestamp": int((timestamp or datetime.now()).timestamp() * 1000),
            },
            "associations": {"contactIds": [int(contact_id)]},
            "metadata": {"body": body},
        }

        # Use engagements API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.hubapi.com/engagements/v1/engagements",
                headers={"Authorization": f"Bearer {settings.hubspot_access_token}"},
                json=engagement_data,
            )
            return response.json()

    def _contact_to_dict(self, contact) -> dict[str, Any]:
        """Convert HubSpot contact object to dictionary."""
        props = contact.properties
        return {
            "id": contact.id,
            "email": props.get("email"),
            "first_name": props.get("firstname"),
            "last_name": props.get("lastname"),
            "company": props.get("company"),
            "title": props.get("jobtitle"),
            "phone": props.get("phone"),
            "linkedin": props.get("linkedin"),
            "city": props.get("city"),
            "state": props.get("state"),
            "country": props.get("country"),
            "lifecycle_stage": props.get("lifecyclestage"),
            "lead_status": props.get("hs_lead_status"),
            "owner_id": props.get("hubspot_owner_id"),
            "created_at": props.get("createdate"),
            "updated_at": props.get("lastmodifieddate"),
            "contact_count": int(props.get("num_contacted_notes") or 0),
            "last_contacted": props.get("notes_last_contacted"),
        }

    def _company_to_dict(self, company) -> dict[str, Any]:
        """Convert HubSpot company object to dictionary."""
        props = company.properties
        return {
            "id": company.id,
            "name": props.get("name"),
            "domain": props.get("domain"),
            "industry": props.get("industry"),
            "employee_count": props.get("numberofemployees"),
            "annual_revenue": props.get("annualrevenue"),
            "city": props.get("city"),
            "state": props.get("state"),
            "country": props.get("country"),
        }

    def _deal_to_dict(self, deal) -> dict[str, Any]:
        """Convert HubSpot deal object to dictionary."""
        props = deal.properties
        return {
            "id": deal.id,
            "name": props.get("dealname"),
            "stage": props.get("dealstage"),
            "amount": props.get("amount"),
            "close_date": props.get("closedate"),
            "pipeline": props.get("pipeline"),
            "owner_id": props.get("hubspot_owner_id"),
            "won_reason": props.get("hs_closed_won_reason"),
            "lost_reason": props.get("hs_closed_lost_reason"),
        }


# Singleton instance
hubspot_client = HubSpotClient()
