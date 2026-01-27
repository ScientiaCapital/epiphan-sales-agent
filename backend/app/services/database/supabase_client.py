"""Supabase client for local lead storage and scoring."""

from functools import lru_cache
from typing import Any

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

    def __init__(self):
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
        return result.data[0] if result.data else {}

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
        return result.data

    def get_lead_by_hubspot_id(self, hubspot_id: str) -> dict[str, Any] | None:
        """Get a lead by HubSpot ID."""
        result = (
            self.client.table("leads")
            .select("*")
            .eq("hubspot_id", hubspot_id)
            .single()
            .execute()
        )
        return result.data

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
                .select("id", count="exact")
                .eq("tier", tier)
                .execute()
            )
            counts[tier] = result.count or 0

        return counts

    def get_total_lead_count(self) -> int:
        """Get total number of leads."""
        result = (
            self.client.table("leads")
            .select("id", count="exact")
            .execute()
        )
        return result.count or 0

    # =========================================================================
    # Outreach Operations (for Phase 2)
    # =========================================================================

    def create_outreach_event(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Create an outreach event."""
        result = self.client.table("outreach_events").insert(event_data).execute()
        return result.data[0] if result.data else {}

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


@lru_cache
def get_supabase_client() -> SupabaseClient:
    """Get cached Supabase client instance."""
    return SupabaseClient()


# Singleton instance for convenience
supabase_client = SupabaseClient()
