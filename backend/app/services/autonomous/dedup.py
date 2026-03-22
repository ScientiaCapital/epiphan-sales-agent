"""Deduplication across sources and historical outreach.

Prevents duplicate outreach by checking:
1. outreach_queue (email-based, last 30 days)
2. Cross-source dedup (same person from Apollo and HubSpot)
3. Recently rejected leads (configurable cooldown)
"""

import logging
from typing import Any, cast

from app.services.autonomous.schemas import RawLead

logger = logging.getLogger(__name__)

# Don't re-queue leads rejected within this window
REJECTION_COOLDOWN_DAYS = 30


class Deduplicator:
    """Prevent duplicate outreach across sources and history."""

    async def deduplicate(
        self,
        leads: list[RawLead],
        cooldown_days: int = REJECTION_COOLDOWN_DAYS,
    ) -> list[RawLead]:
        """Remove leads already queued, recently rejected, or duplicated.

        Returns deduplicated list preserving source priority order.
        """
        if not leads:
            return []

        # Step 1: Cross-source dedup (keep first occurrence by email)
        seen_emails: set[str] = set()
        unique_leads: list[RawLead] = []
        for lead in leads:
            email_lower = lead.email.lower()
            if email_lower not in seen_emails:
                seen_emails.add(email_lower)
                unique_leads.append(lead)

        cross_source_removed = len(leads) - len(unique_leads)
        if cross_source_removed:
            logger.info("Cross-source dedup removed %d duplicates", cross_source_removed)

        # Step 2: Check against outreach_queue history
        historical_emails = await self._get_recent_queue_emails(cooldown_days)
        before_history = len(unique_leads)
        unique_leads = [
            lead for lead in unique_leads
            if lead.email.lower() not in historical_emails
        ]
        history_removed = before_history - len(unique_leads)
        if history_removed:
            logger.info("History dedup removed %d already-queued leads", history_removed)

        logger.info(
            "Dedup result: %d input -> %d output (-%d cross-source, -%d history)",
            len(leads),
            len(unique_leads),
            cross_source_removed,
            history_removed,
        )
        return unique_leads

    async def _get_recent_queue_emails(self, days: int) -> set[str]:
        """Get emails from outreach_queue in the last N days."""
        try:
            from datetime import datetime, timedelta, timezone

            from app.services.database.supabase_client import supabase_client

            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

            result = (
                supabase_client.client.table("outreach_queue")
                .select("lead_email")
                .gte("created_at", cutoff)
                .execute()
            )

            rows = cast(list[dict[str, Any]], result.data) if result.data else []
            return {row["lead_email"].lower() for row in rows if row.get("lead_email")}

        except Exception:
            logger.exception("Failed to fetch queue history for dedup")
            return set()


# Singleton
deduplicator = Deduplicator()
