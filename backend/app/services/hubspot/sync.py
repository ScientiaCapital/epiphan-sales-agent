"""HubSpot Sync Service for syncing contacts to local Supabase.

Provides full and incremental sync capabilities for the 12,000+ contact database.
"""

from datetime import datetime, timezone
from typing import Any

from app.data.lead_schemas import LeadCreate, SyncResult
from app.services.database.supabase_client import supabase_client
from app.services.integrations.hubspot.client import hubspot_client


class HubSpotSyncService:
    """
    Service for syncing HubSpot contacts to local Supabase.

    Handles:
    - Full sync: Pull all contacts with pagination
    - Incremental sync: Pull only recently modified contacts
    - Data transformation: HubSpot format → Lead model
    """

    def __init__(self):
        """Initialize sync service."""
        self.batch_size = 100  # HubSpot API limit
        self.db_batch_size = 100  # Supabase upsert batch size

    async def full_sync(self) -> SyncResult:
        """
        Perform a full sync of all HubSpot contacts.

        Paginates through all contacts and upserts to Supabase.

        Returns:
            SyncResult with sync statistics
        """
        started_at = datetime.now(timezone.utc)
        contacts_fetched = 0
        contacts_synced = 0
        contacts_skipped = 0
        errors: list[str] = []
        leads_to_sync: list[dict[str, Any]] = []

        try:
            after_cursor: str | None = None

            while True:
                # Fetch page of contacts from HubSpot
                response = await hubspot_client.get_all_contacts(
                    limit=self.batch_size,
                    after=after_cursor,
                )

                contacts = response.get("results", [])
                contacts_fetched += len(contacts)

                # Transform contacts to leads
                for contact in contacts:
                    lead = self._transform_contact_to_lead(contact)
                    if lead:
                        leads_to_sync.append(lead.model_dump(exclude_none=True))
                    else:
                        contacts_skipped += 1

                # Batch upsert when we have enough leads
                if len(leads_to_sync) >= self.db_batch_size:
                    synced = supabase_client.upsert_leads_batch(leads_to_sync)
                    contacts_synced += synced
                    leads_to_sync = []

                # Check for more pages
                paging = response.get("paging")
                if paging and paging.get("next", {}).get("after"):
                    after_cursor = paging["next"]["after"]
                else:
                    break

            # Upsert remaining leads
            if leads_to_sync:
                synced = supabase_client.upsert_leads_batch(leads_to_sync)
                contacts_synced += synced

            success = True

        except Exception as e:
            errors.append(str(e))
            success = False

        completed_at = datetime.now(timezone.utc)
        duration = (completed_at - started_at).total_seconds()

        return SyncResult(
            success=success,
            contacts_fetched=contacts_fetched,
            contacts_synced=contacts_synced,
            contacts_skipped=contacts_skipped,
            errors=errors,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
        )

    async def incremental_sync(self, since: datetime) -> SyncResult:
        """
        Sync only contacts modified since a given datetime.

        Args:
            since: Only sync contacts modified after this time

        Returns:
            SyncResult with sync statistics
        """
        started_at = datetime.now(timezone.utc)
        contacts_fetched = 0
        contacts_synced = 0
        contacts_skipped = 0
        errors: list[str] = []
        leads_to_sync: list[dict[str, Any]] = []

        try:
            after_cursor: str | None = None

            while True:
                # Fetch modified contacts from HubSpot
                response = await hubspot_client.get_contacts_modified_since(
                    since=since,
                    limit=self.batch_size,
                    after=after_cursor,
                )

                contacts = response.get("results", [])
                contacts_fetched += len(contacts)

                # Transform contacts to leads
                for contact in contacts:
                    lead = self._transform_contact_to_lead(contact)
                    if lead:
                        leads_to_sync.append(lead.model_dump(exclude_none=True))
                    else:
                        contacts_skipped += 1

                # Batch upsert
                if len(leads_to_sync) >= self.db_batch_size:
                    synced = supabase_client.upsert_leads_batch(leads_to_sync)
                    contacts_synced += synced
                    leads_to_sync = []

                # Check for more pages
                paging = response.get("paging")
                if paging and paging.get("next", {}).get("after"):
                    after_cursor = paging["next"]["after"]
                else:
                    break

            # Upsert remaining leads
            if leads_to_sync:
                synced = supabase_client.upsert_leads_batch(leads_to_sync)
                contacts_synced += synced

            success = True

        except Exception as e:
            errors.append(str(e))
            success = False

        completed_at = datetime.now(timezone.utc)
        duration = (completed_at - started_at).total_seconds()

        return SyncResult(
            success=success,
            contacts_fetched=contacts_fetched,
            contacts_synced=contacts_synced,
            contacts_skipped=contacts_skipped,
            errors=errors,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
        )

    def _transform_contact_to_lead(
        self, contact: dict[str, Any]
    ) -> LeadCreate | None:
        """
        Transform a HubSpot contact to LeadCreate model.

        Args:
            contact: HubSpot contact dict from API

        Returns:
            LeadCreate if valid, None if missing required fields
        """
        # Skip contacts without email
        email = contact.get("email")
        if not email:
            return None

        hubspot_id = contact.get("id")
        if not hubspot_id:
            return None

        return LeadCreate(
            hubspot_id=str(hubspot_id),
            email=email,
            first_name=contact.get("first_name"),
            last_name=contact.get("last_name"),
            company=contact.get("company"),
            title=contact.get("title"),
            phone=contact.get("phone"),
            linkedin_url=self._normalize_linkedin_url(contact.get("linkedin")),
            city=contact.get("city"),
            state=contact.get("state"),
            country=contact.get("country"),
            hubspot_owner_id=contact.get("owner_id"),
            lifecycle_stage=contact.get("lifecycle_stage"),
            lead_status=contact.get("lead_status"),
            last_activity_date=self._parse_datetime(contact.get("last_activity_date")),
            contact_count=contact.get("contact_count", 0) or 0,
            last_contacted=self._parse_datetime(contact.get("last_contacted")),
            hubspot_created_at=self._parse_datetime(contact.get("created_at")),
            hubspot_updated_at=self._parse_datetime(contact.get("updated_at")),
        )

    def _normalize_linkedin_url(self, url: str | None) -> str | None:
        """
        Normalize LinkedIn URL to include https:// prefix.

        Args:
            url: Raw LinkedIn URL from HubSpot

        Returns:
            Normalized URL or None
        """
        if not url:
            return None

        url = url.strip()
        if not url:
            return None

        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        return url

    def _parse_datetime(self, dt_str: str | None) -> datetime | None:
        """
        Parse datetime string from HubSpot format.

        HubSpot uses ISO 8601 format: 2024-01-15T10:00:00Z

        Args:
            dt_str: DateTime string from HubSpot

        Returns:
            Parsed datetime or None
        """
        if not dt_str:
            return None

        dt_str = dt_str.strip()
        if not dt_str:
            return None

        try:
            # Handle both with and without milliseconds
            if "." in dt_str:
                # 2024-01-15T10:00:00.000Z
                dt_str = dt_str.replace("Z", "+00:00")
                return datetime.fromisoformat(dt_str)
            else:
                # 2024-01-15T10:00:00Z
                dt_str = dt_str.replace("Z", "+00:00")
                return datetime.fromisoformat(dt_str)
        except (ValueError, AttributeError):
            return None


# Singleton instance
hubspot_sync_service = HubSpotSyncService()
