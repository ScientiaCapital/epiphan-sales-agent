"""Supabase client for local lead storage and scoring."""

from functools import lru_cache
from typing import Any, cast

from postgrest.types import CountMethod

from app.core.config import settings
from supabase import Client, create_client


class SupabaseClient:
    """
    Supabase client wrapper for lead intelligence operations.

    Handles:
    - Lead storage and retrieval
    - Scoring data persistence
    - Outreach tracking
    """

    def __init__(self) -> None:
        """Initialize Supabase client with settings."""
        self._client: Client | None = None

    @property
    def client(self) -> Client:
        """Lazy-load Supabase client."""
        if self._client is None:
            if not settings.supabase_url or not settings.supabase_service_key:
                raise ValueError(
                    "Supabase credentials not configured. "
                    "Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
                )
            self._client = create_client(
                settings.supabase_url,
                settings.supabase_service_key,
            )
        return self._client

    # =========================================================================
    # Lead Operations
    # =========================================================================

    def upsert_lead(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        """
        Insert or update a lead by hubspot_id.

        Args:
            lead_data: Lead data with required hubspot_id

        Returns:
            Upserted lead record
        """
        result = (
            self.client.table("leads")
            .upsert(lead_data, on_conflict="hubspot_id")
            .execute()
        )
        return cast(dict[str, Any], result.data[0]) if result.data else {}

    def upsert_leads_batch(
        self, leads: list[dict[str, Any]], batch_size: int = 100
    ) -> int:
        """
        Batch upsert leads for efficient sync.

        Args:
            leads: List of lead data dicts
            batch_size: Number of records per batch

        Returns:
            Total number of upserted records
        """
        total_upserted = 0

        for i in range(0, len(leads), batch_size):
            batch = leads[i : i + batch_size]
            result = (
                self.client.table("leads")
                .upsert(batch, on_conflict="hubspot_id")
                .execute()
            )
            total_upserted += len(result.data) if result.data else 0

        return total_upserted

    def get_lead_by_id(self, lead_id: str) -> dict[str, Any] | None:
        """Get a lead by its UUID."""
        result = (
            self.client.table("leads")
            .select("*")
            .eq("id", lead_id)
            .single()
            .execute()
        )
        return cast(dict[str, Any] | None, result.data)

    def get_lead_by_hubspot_id(self, hubspot_id: str) -> dict[str, Any] | None:
        """Get a lead by HubSpot ID."""
        result = (
            self.client.table("leads")
            .select("*")
            .eq("hubspot_id", hubspot_id)
            .single()
            .execute()
        )
        return cast(dict[str, Any] | None, result.data)

    def get_unscored_leads(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Get leads that haven't been scored yet."""
        result = (
            self.client.table("leads")
            .select("*")
            .is_("scored_at", "null")
            .limit(limit)
            .execute()
        )
        return result.data or []

    def get_prioritized_leads(
        self,
        tier: str | None = None,
        persona: str | None = None,
        vertical: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Get leads prioritized by score with optional filters.

        Args:
            tier: Filter by tier (hot, warm, nurture, cold)
            persona: Filter by persona_match
            vertical: Filter by vertical
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of leads ordered by total_score descending
        """
        query = self.client.table("leads").select("*")

        if tier:
            query = query.eq("tier", tier)
        if persona:
            query = query.eq("persona_match", persona)
        if vertical:
            query = query.eq("vertical", vertical)

        result = (
            query.order("total_score", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data or []

    def update_lead_scores(
        self,
        lead_id: str,
        persona_match: str | None,
        persona_confidence: float,
        vertical: str | None,
        persona_score: int,
        vertical_score: int,
        company_score: int,
        engagement_score: int,
    ) -> dict[str, Any]:
        """
        Update scoring fields for a lead.

        Args:
            lead_id: Lead UUID
            persona_match: Matched persona type
            persona_confidence: Confidence score (0-1)
            vertical: Matched vertical
            persona_score: Score for persona fit (0-25)
            vertical_score: Score for vertical alignment (0-25)
            company_score: Score for company signals (0-25)
            engagement_score: Score for engagement data (0-25)

        Returns:
            Updated lead record
        """
        from datetime import datetime, timezone

        result = (
            self.client.table("leads")
            .update(
                {
                    "persona_match": persona_match,
                    "persona_confidence": persona_confidence,
                    "vertical": vertical,
                    "persona_score": persona_score,
                    "vertical_score": vertical_score,
                    "company_score": company_score,
                    "engagement_score": engagement_score,
                    "scored_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", lead_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def get_lead_count_by_tier(self) -> dict[str, int]:
        """Get count of leads in each tier."""
        tiers = ["hot", "warm", "nurture", "cold"]
        counts = {}

        for tier in tiers:
            result = (
                self.client.table("leads")
                .select("id", count=CountMethod.exact)
                .eq("tier", tier)
                .execute()
            )
            counts[tier] = result.count or 0

        return counts

    def get_total_lead_count(self) -> int:
        """Get total number of leads."""
        result = (
            self.client.table("leads")
            .select("id", count=CountMethod.exact)
            .execute()
        )
        return result.count or 0

    # =========================================================================
    # Phone Webhook Storage (PHONES ARE GOLD!)
    # =========================================================================

    def store_apollo_phone_webhook(
        self,
        email: str,
        person_id: str | None,
        direct_phone: str | None,
        mobile_phone: str | None,
        work_phone: str | None,
        raw_phones: list[dict[str, Any]],
        lead_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Store phone data from Apollo webhook LOCALLY before HubSpot sync.

        PHONES ARE GOLD! This stores phones locally with synced_to_hubspot=FALSE.
        HubSpot sync requires explicit approval via sync_phone_to_hubspot().

        Args:
            email: Contact email (primary identifier)
            person_id: Apollo person ID
            direct_phone: Direct dial number (BEST)
            mobile_phone: Mobile number (GOOD)
            work_phone: Work line (OK)
            raw_phones: Raw phone array from Apollo for audit
            lead_id: Optional link to leads table

        Returns:
            Inserted record
        """
        import json

        result = (
            self.client.table("apollo_phone_webhooks")
            .insert({
                "email": email,
                "person_id": person_id,
                "direct_phone": direct_phone,
                "mobile_phone": mobile_phone,
                "work_phone": work_phone,
                "raw_phones": json.dumps(raw_phones),
                "lead_id": lead_id,
                "synced_to_hubspot": False,  # NOT synced until approved
            })
            .execute()
        )
        return cast(dict[str, Any], result.data[0]) if result.data else {}

    def get_unsynced_phones(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get phone records pending HubSpot sync approval.

        Returns:
            List of phone records with synced_to_hubspot=FALSE
        """
        result = (
            self.client.table("apollo_phone_webhooks")
            .select("*")
            .eq("synced_to_hubspot", False)
            .order("received_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def mark_phone_synced(self, phone_id: int) -> dict[str, Any]:
        """
        Mark a phone record as synced to HubSpot.

        Called AFTER successful HubSpot API call.

        Args:
            phone_id: ID of apollo_phone_webhooks record

        Returns:
            Updated record
        """
        from datetime import datetime, timezone

        result = (
            self.client.table("apollo_phone_webhooks")
            .update({
                "synced_to_hubspot": True,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", phone_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def get_phones_by_email(self, email: str) -> list[dict[str, Any]]:
        """
        Get all phone records for an email.

        Useful for checking if we already have phones before re-enriching.

        Args:
            email: Contact email

        Returns:
            List of phone records (may have multiple from different webhooks)
        """
        result = (
            self.client.table("apollo_phone_webhooks")
            .select("*")
            .eq("email", email)
            .order("received_at", desc=True)
            .execute()
        )
        return result.data or []

    # =========================================================================
    # Outreach Operations (for Phase 2)
    # =========================================================================

    def create_outreach_event(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Create an outreach event."""
        result = self.client.table("outreach_events").insert(event_data).execute()
        return cast(dict[str, Any], result.data[0]) if result.data else {}

    def get_scheduled_events(
        self, before: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get scheduled outreach events."""
        query = (
            self.client.table("outreach_events")
            .select("*, leads(*)")
            .eq("status", "scheduled")
        )

        if before:
            query = query.lte("scheduled_at", before)

        result = query.order("scheduled_at").limit(limit).execute()
        return result.data or []

    # =========================================================================
    # Call Outcome Operations (BDR call tracking)
    # =========================================================================

    def create_call_outcome(self, outcome_data: dict[str, Any]) -> dict[str, Any]:
        """
        Insert a call outcome record.

        Args:
            outcome_data: Call outcome fields

        Returns:
            Inserted record
        """
        result = self.client.table("call_outcomes").insert(outcome_data).execute()
        return cast(dict[str, Any], result.data[0]) if result.data else {}

    def get_outcomes_by_lead(
        self, lead_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get all call outcomes for a lead, most recent first."""
        result = (
            self.client.table("call_outcomes")
            .select("*")
            .eq("lead_id", lead_id)
            .order("called_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def get_outcomes_by_date(self, date_str: str) -> list[dict[str, Any]]:
        """
        Get all call outcomes for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            List of call outcome records
        """
        start = f"{date_str}T00:00:00+00:00"
        end = f"{date_str}T23:59:59+00:00"
        result = (
            self.client.table("call_outcomes")
            .select("*")
            .gte("called_at", start)
            .lte("called_at", end)
            .order("called_at", desc=True)
            .execute()
        )
        return result.data or []

    def get_outcomes_by_date_range(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """
        Get call outcomes within a date range.

        Args:
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD

        Returns:
            List of call outcome records
        """
        start = f"{start_date}T00:00:00+00:00"
        end = f"{end_date}T23:59:59+00:00"
        result = (
            self.client.table("call_outcomes")
            .select("*")
            .gte("called_at", start)
            .lte("called_at", end)
            .order("called_at", desc=True)
            .execute()
        )
        return result.data or []

    def get_pending_follow_ups(
        self, before_date: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get call outcomes with pending follow-ups on or before a date.

        Args:
            before_date: Include follow-ups up to this date (YYYY-MM-DD)
            limit: Max results

        Returns:
            List of call outcomes with follow_up_date set
        """
        result = (
            self.client.table("call_outcomes")
            .select("*")
            .not_.is_("follow_up_date", "null")
            .lte("follow_up_date", before_date)
            .order("follow_up_date")
            .limit(limit)
            .execute()
        )
        return result.data or []

    def get_unsynced_call_outcomes(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get call outcomes not yet synced to HubSpot."""
        result = (
            self.client.table("call_outcomes")
            .select("*")
            .eq("synced_to_hubspot", False)
            .order("called_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def mark_outcome_synced(
        self, outcome_id: str, hubspot_engagement_id: str
    ) -> dict[str, Any]:
        """
        Mark a call outcome as synced to HubSpot.

        Args:
            outcome_id: UUID of the call outcome
            hubspot_engagement_id: HubSpot engagement ID from API response

        Returns:
            Updated record
        """
        from datetime import datetime, timezone

        result = (
            self.client.table("call_outcomes")
            .update({
                "synced_to_hubspot": True,
                "synced_at": datetime.now(timezone.utc).isoformat(),
                "hubspot_engagement_id": hubspot_engagement_id,
            })
            .eq("id", outcome_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def update_lead(self, lead_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Generic lead field update.

        Used by call outcome service to update last_contacted,
        contact_count, and lead_status after a call.

        Args:
            lead_id: Lead UUID
            data: Fields to update

        Returns:
            Updated lead record
        """
        result = (
            self.client.table("leads")
            .update(data)
            .eq("id", lead_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    # -------------------------------------------------------------------------
    # Call Briefs
    # -------------------------------------------------------------------------

    def save_call_brief(self, brief_data: dict[str, Any]) -> dict[str, Any]:
        """
        Insert a call brief record.

        Args:
            brief_data: Call brief fields (lead_id, brief_json, brief_quality, etc.)

        Returns:
            Inserted record with generated UUID
        """
        result = self.client.table("call_briefs").insert(brief_data).execute()
        return cast(dict[str, Any], result.data[0]) if result.data else {}

    def get_call_brief(self, brief_id: str) -> dict[str, Any] | None:
        """
        Retrieve a call brief by ID.

        Args:
            brief_id: Call brief UUID

        Returns:
            Brief record or None
        """
        result = (
            self.client.table("call_briefs")
            .select("*")
            .eq("id", brief_id)
            .execute()
        )
        return cast(dict[str, Any], result.data[0]) if result.data else None

    def get_briefs_with_outcomes(self) -> list[dict[str, Any]]:
        """
        Get call briefs joined with their outcomes for effectiveness analysis.

        Returns a list of briefs that have linked outcomes, including
        the outcome disposition and result for conversion tracking.

        Returns:
            List of brief records with outcome data
        """
        result = (
            self.client.table("call_briefs")
            .select("*, call_outcomes(id, disposition, result, objections)")
            .execute()
        )
        return cast(list[dict[str, Any]], result.data) if result.data else []


@lru_cache
def get_supabase_client() -> SupabaseClient:
    """Get cached Supabase client instance."""
    return SupabaseClient()


# Singleton instance for convenience
supabase_client = SupabaseClient()
