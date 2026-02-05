"""Call outcome tracking service.

Closes the feedback loop: log what happened, update the lead,
schedule follow-ups. No AI/LLM calls — pure data tracking.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.data.call_outcome_schemas import (
    CallDisposition,
    CallOutcomeCreate,
    CallOutcomeLogResult,
    CallOutcomeResponse,
    CallResult,
    DailyCallStats,
    FollowUpType,
    LeadCallHistory,
    PendingFollowUp,
    PendingFollowUpsResponse,
    PhoneTypeBreakdown,
)
from app.services.database.supabase_client import supabase_client
from app.services.integrations.hubspot.client import hubspot_client

logger = logging.getLogger(__name__)


# =============================================================================
# Default follow-up rules
# =============================================================================

# Maps disposition → (business_days_offset, follow_up_type)
# None means no automatic follow-up
DEFAULT_FOLLOW_UP_RULES: dict[str, tuple[int, FollowUpType] | None] = {
    CallDisposition.VOICEMAIL.value: (2, FollowUpType.CALLBACK),
    CallDisposition.NO_ANSWER.value: (1, FollowUpType.CALLBACK),
    CallDisposition.BUSY.value: (1, FollowUpType.CALLBACK),
    CallDisposition.GATEKEEPER.value: (1, FollowUpType.CALLBACK),
    CallDisposition.CALLBACK_REQUESTED.value: None,  # Tim specifies the date
    CallDisposition.CONNECTED.value: None,  # Handled by result-based rules below
    CallDisposition.NOT_INTERESTED.value: None,
    CallDisposition.WRONG_NUMBER.value: None,
    CallDisposition.NO_LONGER_THERE.value: None,
}

# Result-based follow-up for connected calls
CONNECTED_FOLLOW_UP_RULES: dict[str, tuple[int, FollowUpType] | None] = {
    CallResult.FOLLOW_UP_NEEDED.value: (3, FollowUpType.SEND_EMAIL),
    CallResult.NURTURE.value: (7, FollowUpType.SEND_EMAIL),
    CallResult.MEETING_BOOKED.value: None,
    CallResult.QUALIFIED_OUT.value: None,
    CallResult.DEAD.value: None,
    CallResult.NO_CONTACT.value: None,
}

# Lead status updates based on result
LEAD_STATUS_MAP: dict[str, str] = {
    CallResult.MEETING_BOOKED.value: "meeting_scheduled",
    CallResult.QUALIFIED_OUT.value: "disqualified",
    CallResult.DEAD.value: "dead",
}


class CallOutcomeService:
    """Service for logging and querying call outcomes."""

    def log_outcome(self, outcome: CallOutcomeCreate) -> CallOutcomeLogResult:
        """
        Log a call outcome: insert record, update lead, schedule follow-up.

        Args:
            outcome: Call outcome data from BDR

        Returns:
            Result with outcome record and what was updated
        """
        # 1. Apply default follow-up rules if Tim didn't specify one
        follow_up_date = outcome.follow_up_date
        follow_up_type = outcome.follow_up_type
        follow_up_scheduled = False

        if follow_up_date is None and follow_up_type is None:
            rule = self._get_follow_up_rule(
                outcome.disposition.value, outcome.result.value
            )
            if rule is not None:
                days, fu_type = rule
                follow_up_date = self._add_business_days(
                    date.today(), days
                )
                follow_up_type = fu_type

        if follow_up_date is not None:
            follow_up_scheduled = True

        # 2. Build record for insertion
        now = datetime.now(timezone.utc)
        record_data: dict[str, Any] = {
            "lead_id": outcome.lead_id,
            "called_at": now.isoformat(),
            "duration_seconds": outcome.duration_seconds,
            "phone_number_dialed": outcome.phone_number_dialed,
            "phone_type": outcome.phone_type,
            "disposition": outcome.disposition.value,
            "result": outcome.result.value,
            "notes": outcome.notes,
            "objections": outcome.objections,
            "buying_signals": outcome.buying_signals,
            "competitor_mentioned": outcome.competitor_mentioned,
        }

        if follow_up_date is not None:
            record_data["follow_up_date"] = follow_up_date.isoformat()
        if follow_up_type is not None:
            record_data["follow_up_type"] = follow_up_type.value if isinstance(
                follow_up_type, FollowUpType
            ) else follow_up_type

        if outcome.follow_up_notes:
            record_data["follow_up_notes"] = outcome.follow_up_notes

        # 3. Insert call outcome
        inserted = supabase_client.create_call_outcome(record_data)

        # 4. Update lead record
        lead_updated = self._update_lead_after_call(
            outcome.lead_id, outcome.result.value
        )

        # 5. Build response
        outcome_response = self._record_to_response(inserted)
        return CallOutcomeLogResult(
            success=True,
            outcome=outcome_response,
            lead_updated=lead_updated,
            follow_up_scheduled=follow_up_scheduled,
        )

    def get_daily_stats(self, date_str: str) -> DailyCallStats:
        """
        Compute daily call stats for the performance dashboard.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Aggregated stats for the day
        """
        outcomes = supabase_client.get_outcomes_by_date(date_str)
        return self._compute_stats(date_str, outcomes)

    def get_stats_for_range(
        self, start_date: str, end_date: str
    ) -> list[DailyCallStats]:
        """
        Compute stats for each day in a date range.

        Args:
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD

        Returns:
            List of daily stats, one per day with calls
        """
        outcomes = supabase_client.get_outcomes_by_date_range(start_date, end_date)

        # Group by date
        by_date: dict[str, list[dict[str, Any]]] = {}
        for o in outcomes:
            called_at = o.get("called_at", "")
            day = called_at[:10] if called_at else "unknown"
            by_date.setdefault(day, []).append(o)

        return [
            self._compute_stats(day, day_outcomes)
            for day, day_outcomes in sorted(by_date.items())
        ]

    def get_lead_history(self, lead_id: str) -> LeadCallHistory:
        """
        Get full call history for a lead.

        Args:
            lead_id: Lead UUID

        Returns:
            Call history with summary stats
        """
        records = supabase_client.get_outcomes_by_lead(lead_id)
        outcomes = [self._record_to_response(r) for r in records]

        # Look up lead name/company
        lead = supabase_client.get_lead_by_id(lead_id)
        lead_name = None
        company = None
        if lead:
            first = lead.get("first_name", "") or ""
            last = lead.get("last_name", "") or ""
            lead_name = f"{first} {last}".strip() or None
            company = lead.get("company")

        total_connections = sum(
            1 for o in outcomes if o.disposition == CallDisposition.CONNECTED.value
        )
        last_called = outcomes[0].called_at if outcomes else None

        return LeadCallHistory(
            lead_id=lead_id,
            lead_name=lead_name,
            company=company,
            total_calls=len(outcomes),
            total_connections=total_connections,
            last_called=last_called,
            outcomes=outcomes,
        )

    def get_pending_follow_ups(
        self,
        target_date: date | None = None,
        include_overdue: bool = True,
    ) -> PendingFollowUpsResponse:
        """
        Get follow-ups that need doing.

        Args:
            target_date: Date to check (default: today)
            include_overdue: Include past-due follow-ups

        Returns:
            List of pending follow-ups with counts
        """
        check_date = target_date or date.today()
        before_date = check_date.isoformat()

        records = supabase_client.get_pending_follow_ups(before_date)

        follow_ups: list[PendingFollowUp] = []
        overdue_count = 0

        for r in records:
            fu_date_str = r.get("follow_up_date", "")
            fu_date = date.fromisoformat(fu_date_str) if fu_date_str else check_date
            is_overdue = fu_date < check_date

            if is_overdue:
                overdue_count += 1

            if not include_overdue and is_overdue:
                continue

            # Look up lead info
            lead = supabase_client.get_lead_by_id(r.get("lead_id", ""))
            lead_name = None
            company = None
            if lead:
                first = lead.get("first_name", "") or ""
                last = lead.get("last_name", "") or ""
                lead_name = f"{first} {last}".strip() or None
                company = lead.get("company")

            follow_ups.append(
                PendingFollowUp(
                    outcome_id=r["id"],
                    lead_id=r["lead_id"],
                    lead_name=lead_name,
                    company=company,
                    phone_number=r.get("phone_number_dialed", ""),
                    follow_up_date=fu_date,
                    follow_up_type=r.get("follow_up_type", "callback"),
                    follow_up_notes=r.get("follow_up_notes"),
                    disposition=r.get("disposition", ""),
                    is_overdue=is_overdue,
                )
            )

        # Sort: overdue first, then by date
        follow_ups.sort(key=lambda f: (not f.is_overdue, f.follow_up_date))

        return PendingFollowUpsResponse(
            follow_ups=follow_ups,
            total_count=len(follow_ups),
            overdue_count=overdue_count,
        )

    async def sync_to_hubspot(self, outcome_id: str) -> dict[str, Any]:
        """
        Sync a call outcome to HubSpot as a CALL engagement.

        Args:
            outcome_id: UUID of the call outcome to sync

        Returns:
            HubSpot engagement result
        """
        # Get the outcome record
        result = (
            supabase_client.client.table("call_outcomes")
            .select("*")
            .eq("id", outcome_id)
            .single()
            .execute()
        )
        record = result.data
        if not record:
            raise ValueError(f"Call outcome {outcome_id} not found")

        # Get lead's HubSpot ID
        lead = supabase_client.get_lead_by_id(record["lead_id"])
        if not lead or not lead.get("hubspot_id"):
            raise ValueError(
                f"Lead {record['lead_id']} not found or missing HubSpot ID"
            )

        # Build call body
        body = self._build_hubspot_call_body(record)

        # Log to HubSpot
        hs_result = await hubspot_client.log_activity(
            contact_id=lead["hubspot_id"],
            activity_type="CALL",
            body=body,
        )

        # Mark as synced
        engagement_id = str(
            hs_result.get("engagement", {}).get("id", "")
        )
        supabase_client.mark_outcome_synced(outcome_id, engagement_id)

        return {"synced": True, "hubspot_engagement_id": engagement_id}

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _get_follow_up_rule(
        self, disposition: str, result: str
    ) -> tuple[int, FollowUpType] | None:
        """Get the default follow-up rule for a disposition/result combo."""
        # For connected calls, use result-based rules
        if disposition == CallDisposition.CONNECTED.value:
            return CONNECTED_FOLLOW_UP_RULES.get(result)
        # For non-connected, use disposition-based rules
        return DEFAULT_FOLLOW_UP_RULES.get(disposition)

    def _update_lead_after_call(self, lead_id: str, result: str) -> bool:
        """
        Update lead record after a call.

        - Increments contact_count
        - Sets last_contacted to now
        - Updates lead_status if result warrants it
        """
        lead = supabase_client.get_lead_by_id(lead_id)
        if not lead:
            logger.warning("Lead %s not found for post-call update", lead_id)
            return False

        update_data: dict[str, Any] = {
            "last_contacted": datetime.now(timezone.utc).isoformat(),
            "contact_count": (lead.get("contact_count") or 0) + 1,
        }

        # Conditional status update
        new_status = LEAD_STATUS_MAP.get(result)
        if new_status:
            update_data["lead_status"] = new_status

        supabase_client.update_lead(lead_id, update_data)
        return True

    @staticmethod
    def _add_business_days(start_date: date, days: int) -> date:
        """Add business days (skipping weekends) to a date."""
        current = start_date
        added = 0
        while added < days:
            current += timedelta(days=1)
            # Skip weekends (5=Sat, 6=Sun)
            if current.weekday() < 5:
                added += 1
        return current

    def _compute_stats(
        self, date_str: str, outcomes: list[dict[str, Any]]
    ) -> DailyCallStats:
        """Aggregate raw outcome records into daily stats."""
        total_dials = len(outcomes)
        connections = sum(
            1 for o in outcomes if o.get("disposition") == CallDisposition.CONNECTED.value
        )
        voicemails = sum(
            1 for o in outcomes if o.get("disposition") == CallDisposition.VOICEMAIL.value
        )
        no_answers = sum(
            1 for o in outcomes if o.get("disposition") == CallDisposition.NO_ANSWER.value
        )
        meetings_booked = sum(
            1 for o in outcomes if o.get("result") == CallResult.MEETING_BOOKED.value
        )

        # Connect rate: connections / total dials
        connect_rate = (connections / total_dials * 100) if total_dials > 0 else 0.0

        # Meeting rate: meetings / connections (not dials)
        meeting_rate = (
            (meetings_booked / connections * 100) if connections > 0 else 0.0
        )

        # Average duration for connected calls only
        connected_durations = [
            o.get("duration_seconds", 0)
            for o in outcomes
            if o.get("disposition") == CallDisposition.CONNECTED.value
            and o.get("duration_seconds", 0) > 0
        ]
        avg_duration = (
            sum(connected_durations) / len(connected_durations)
            if connected_durations
            else 0.0
        )

        # Phone type breakdown
        breakdown = PhoneTypeBreakdown()
        for o in outcomes:
            pt = (o.get("phone_type") or "unknown").lower()
            if pt == "direct":
                breakdown.direct += 1
            elif pt == "mobile":
                breakdown.mobile += 1
            elif pt == "work":
                breakdown.work += 1
            elif pt == "company":
                breakdown.company += 1
            else:
                breakdown.unknown += 1

        return DailyCallStats(
            date=date_str,
            total_dials=total_dials,
            connections=connections,
            voicemails=voicemails,
            no_answers=no_answers,
            meetings_booked=meetings_booked,
            connect_rate=round(connect_rate, 1),
            meeting_rate=round(meeting_rate, 1),
            avg_call_duration=round(avg_duration, 1),
            phone_type_breakdown=breakdown,
        )

    @staticmethod
    def _record_to_response(record: dict[str, Any]) -> CallOutcomeResponse:
        """Convert a Supabase record dict to a CallOutcomeResponse."""
        return CallOutcomeResponse(
            id=record.get("id", ""),
            lead_id=record.get("lead_id", ""),
            called_at=record.get("called_at", datetime.now(timezone.utc).isoformat()),
            duration_seconds=record.get("duration_seconds", 0),
            phone_number_dialed=record.get("phone_number_dialed", ""),
            phone_type=record.get("phone_type"),
            disposition=record.get("disposition", ""),
            result=record.get("result", ""),
            notes=record.get("notes"),
            objections=record.get("objections"),
            buying_signals=record.get("buying_signals"),
            competitor_mentioned=record.get("competitor_mentioned"),
            follow_up_date=record.get("follow_up_date"),
            follow_up_type=record.get("follow_up_type"),
            follow_up_notes=record.get("follow_up_notes"),
            hubspot_engagement_id=record.get("hubspot_engagement_id"),
            synced_to_hubspot=record.get("synced_to_hubspot", False),
            synced_at=record.get("synced_at"),
            created_at=record.get("created_at"),
            updated_at=record.get("updated_at"),
        )

    @staticmethod
    def _build_hubspot_call_body(record: dict[str, Any]) -> str:
        """Build a human-readable call body for HubSpot engagement."""
        lines = [
            f"Call Disposition: {record.get('disposition', 'unknown')}",
            f"Result: {record.get('result', 'unknown')}",
            f"Phone: {record.get('phone_number_dialed', 'N/A')} ({record.get('phone_type', 'unknown')})",
            f"Duration: {record.get('duration_seconds', 0)}s",
        ]
        if record.get("notes"):
            lines.append(f"\nNotes: {record['notes']}")
        if record.get("objections"):
            lines.append(f"Objections: {', '.join(record['objections'])}")
        if record.get("buying_signals"):
            lines.append(f"Buying Signals: {', '.join(record['buying_signals'])}")
        if record.get("competitor_mentioned"):
            lines.append(f"Competitor: {record['competitor_mentioned']}")
        return "\n".join(lines)


# Module-level singleton
call_outcome_service = CallOutcomeService()
