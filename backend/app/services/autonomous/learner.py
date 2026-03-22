"""Approval pattern learning from Tim's decisions.

Records every approve/reject decision and aggregates patterns
by industry, title, company size, persona, and vertical.
The system gets smarter as Tim reviews more prospects.

Inspired by autoresearch: the agent's "val_bpb" is Tim's approval rate.
"""

import logging
from datetime import datetime, timezone
from typing import Any, cast

from app.services.autonomous.schemas import ApprovalPattern

logger = logging.getLogger(__name__)


class ApprovalLearner:
    """Learn from Tim's approval patterns to improve future scoring."""

    async def record_decision(
        self,
        queue_item_id: str,
        approved: bool,
        rejection_reason: str | None = None,
        reviewer_notes: str | None = None,
    ) -> None:
        """Record an approval/rejection and update pattern aggregates.

        Updates the outreach_queue item status and incrementally
        updates approval_patterns for learning.
        """
        try:
            from app.services.database.supabase_client import supabase_client

            now = datetime.now(timezone.utc).isoformat()

            # Update queue item status
            update_data: dict[str, Any] = {
                "status": "approved" if approved else "rejected",
                "updated_at": now,
            }
            if approved:
                update_data["approved_at"] = now
                if reviewer_notes:
                    update_data["reviewer_notes"] = reviewer_notes
            else:
                update_data["rejected_at"] = now
                if rejection_reason:
                    update_data["rejection_reason"] = rejection_reason

            supabase_client.client.table("outreach_queue").update(
                update_data
            ).eq("id", queue_item_id).execute()

            # Fetch the item to extract pattern dimensions
            result = (
                supabase_client.client.table("outreach_queue")
                .select("lead_industry, lead_title, persona_match, qualification_tier, lead_company")
                .eq("id", queue_item_id)
                .execute()
            )

            if not result.data:
                return

            item = cast(dict[str, Any], result.data[0])

            # Update patterns for each dimension
            dimensions: list[tuple[str, str | None]] = [
                ("industry", item.get("lead_industry")),
                ("title", self._normalize_title(item.get("lead_title"))),
                ("persona", item.get("persona_match")),
                ("vertical", item.get("qualification_tier")),
            ]

            for pattern_type, pattern_key in dimensions:
                if pattern_key:
                    await self._upsert_pattern(pattern_type, pattern_key, approved)

        except Exception:
            logger.exception("Failed to record decision for %s", queue_item_id)

    async def get_patterns(
        self,
        pattern_type: str | None = None,
        min_decisions: int = 5,
    ) -> list[ApprovalPattern]:
        """Get learned approval patterns, optionally filtered by type.

        Only returns patterns with enough data points (min_decisions)
        to be statistically meaningful.
        """
        try:
            from app.services.database.supabase_client import supabase_client

            query = supabase_client.client.table("approval_patterns").select("*")

            if pattern_type:
                query = query.eq("pattern_type", pattern_type)

            result = query.order("approval_rate", desc=True).execute()
            rows = cast(list[dict[str, Any]], result.data) if result.data else []

            patterns = []
            for row in rows:
                total = (row.get("approved_count", 0) or 0) + (row.get("rejected_count", 0) or 0)
                if total >= min_decisions:
                    patterns.append(
                        ApprovalPattern(
                            pattern_type=row["pattern_type"],
                            pattern_key=row["pattern_key"],
                            approved_count=row.get("approved_count", 0),
                            rejected_count=row.get("rejected_count", 0),
                            approval_rate=row.get("approval_rate", 0.0),
                            last_updated=row.get("last_updated"),
                        )
                    )

            return patterns

        except Exception:
            logger.exception("Failed to fetch approval patterns")
            return []

    async def get_scoring_adjustments(self) -> dict[str, float]:
        """Analyze patterns to suggest scoring weight adjustments.

        Returns a dict of dimension:adjustment pairs.
        Positive = Tim approves these more, boost score.
        Negative = Tim rejects these more, lower score.

        Only activates after 50+ total decisions for statistical relevance.
        """
        try:
            from app.services.database.supabase_client import supabase_client

            result = (
                supabase_client.client.table("approval_patterns")
                .select("*")
                .execute()
            )
            rows = cast(list[dict[str, Any]], result.data) if result.data else []

            total_decisions = sum(
                (r.get("approved_count", 0) or 0) + (r.get("rejected_count", 0) or 0)
                for r in rows
            )

            if total_decisions < 50:
                logger.info(
                    "Only %d decisions recorded, need 50+ for learning. Skipping adjustments.",
                    total_decisions,
                )
                return {}

            adjustments: dict[str, float] = {}
            for row in rows:
                total = (row.get("approved_count", 0) or 0) + (row.get("rejected_count", 0) or 0)
                if total < 5:
                    continue

                rate = row.get("approval_rate", 0.5) or 0.5
                key = f"{row['pattern_type']}:{row['pattern_key']}"

                # Scale: 0.0 rate = -0.5 adjustment, 1.0 rate = +0.5 adjustment
                adjustments[key] = round((rate - 0.5), 2)

            return adjustments

        except Exception:
            logger.exception("Failed to compute scoring adjustments")
            return {}

    async def _upsert_pattern(
        self,
        pattern_type: str,
        pattern_key: str,
        approved: bool,
    ) -> None:
        """Upsert a single approval pattern record."""
        try:
            from app.services.database.supabase_client import supabase_client

            now = datetime.now(timezone.utc).isoformat()

            # Fetch existing
            result = (
                supabase_client.client.table("approval_patterns")
                .select("*")
                .eq("pattern_type", pattern_type)
                .eq("pattern_key", pattern_key)
                .execute()
            )

            if result.data:
                row = cast(dict[str, Any], result.data[0])
                approved_count = (row.get("approved_count", 0) or 0) + (1 if approved else 0)
                rejected_count = (row.get("rejected_count", 0) or 0) + (0 if approved else 1)
                total = approved_count + rejected_count
                approval_rate = approved_count / total if total > 0 else 0.0

                supabase_client.client.table("approval_patterns").update({
                    "approved_count": approved_count,
                    "rejected_count": rejected_count,
                    "approval_rate": round(approval_rate, 4),
                    "last_updated": now,
                }).eq("id", row["id"]).execute()
            else:
                approval_rate = 1.0 if approved else 0.0
                supabase_client.client.table("approval_patterns").insert({
                    "pattern_type": pattern_type,
                    "pattern_key": pattern_key,
                    "approved_count": 1 if approved else 0,
                    "rejected_count": 0 if approved else 1,
                    "approval_rate": approval_rate,
                    "last_updated": now,
                }).execute()

        except Exception:
            logger.exception(
                "Failed to upsert pattern %s:%s", pattern_type, pattern_key
            )

    def _normalize_title(self, title: str | None) -> str | None:
        """Normalize job title for pattern matching.

        Groups similar titles: 'VP of IT' and 'Vice President IT' -> 'vp_it'
        """
        if not title:
            return None

        title_lower = title.lower().strip()

        # Common prefix normalization
        replacements = {
            "vice president": "vp",
            "senior vice president": "svp",
            "chief": "c",
            "director of": "director",
            "head of": "head",
        }

        for long, short in replacements.items():
            if title_lower.startswith(long):
                title_lower = title_lower.replace(long, short, 1)

        # Remove noise words
        for word in ["of", "the", "&", "and", "-", ","]:
            title_lower = title_lower.replace(word, " ")

        # Collapse whitespace and truncate
        return "_".join(title_lower.split())[:50]


# Singleton
approval_learner = ApprovalLearner()
