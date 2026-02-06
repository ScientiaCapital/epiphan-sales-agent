"""Call outcome tracking service.

Closes the feedback loop: log what happened, update the lead,
schedule follow-ups. No AI/LLM calls — pure data tracking.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.data.call_outcome_schemas import (
    BriefEffectivenessResponse,
    CallDisposition,
    CallOutcomeCreate,
    CallOutcomeLogResult,
    CallOutcomeResponse,
    CallResult,
    ConversionFunnel,
    DailyCallStats,
    FollowUpType,
    LeadCallHistory,
    PendingFollowUp,
    PendingFollowUpsResponse,
    PersonaEffectivenessDetail,
    PersonaSummary,
    PhoneTypeBreakdown,
    PhoneTypeImpact,
    QualityConversion,
    ScriptEffectivenessResponse,
    ScriptTemplateRow,
    ScriptTriggerPerformance,
    TierAnalytics,
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
            "call_brief_id": outcome.call_brief_id,
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

    def get_brief_effectiveness(self) -> BriefEffectivenessResponse:
        """
        Analyze call brief effectiveness — enhanced with persona, tier, phone, and funnel data.

        Backward compatible: all 5 original fields preserved.
        """
        briefs_with_outcomes = supabase_client.get_briefs_with_outcomes()

        # Initialize counters
        quality_stats: dict[str, dict[str, int]] = {
            "HIGH": {"total": 0, "meetings": 0},
            "MEDIUM": {"total": 0, "meetings": 0},
            "LOW": {"total": 0, "meetings": 0},
        }
        total_briefs = 0
        total_linked = 0
        objection_matches = 0
        objection_comparisons = 0
        meeting_qualities: list[str] = []
        all_outcomes: list[dict[str, Any]] = []

        # Group by persona and tier
        persona_outcomes: dict[str, list[dict[str, Any]]] = {}
        persona_titles: dict[str, str] = {}
        tier_outcomes: dict[str, list[dict[str, Any]]] = {}
        tier_scores: dict[str, list[float]] = {}

        for brief in briefs_with_outcomes:
            total_briefs += 1
            quality = (brief.get("brief_quality") or "medium").upper()
            if quality not in quality_stats:
                quality = "MEDIUM"

            brief_json = brief.get("brief_json") or {}
            persona_id, persona_title = self._extract_persona_from_brief(brief_json)
            tier = self._extract_tier_from_brief(brief_json)

            outcomes = brief.get("call_outcomes", [])
            if not outcomes:
                continue

            for outcome in outcomes:
                total_linked += 1
                quality_stats[quality]["total"] += 1
                all_outcomes.append(outcome)

                if outcome.get("result") == "meeting_booked":
                    quality_stats[quality]["meetings"] += 1
                    meeting_qualities.append(quality)

                # Group by persona
                if persona_id:
                    persona_outcomes.setdefault(persona_id, []).append(outcome)
                    if persona_title:
                        persona_titles[persona_id] = persona_title

                # Group by tier
                if tier:
                    tier_outcomes.setdefault(tier, []).append(outcome)
                    score = (brief_json.get("qualification") or {}).get("score")
                    if score is not None:
                        tier_scores.setdefault(tier, []).append(float(score))

                # Check objection prediction accuracy
                predicted = (brief_json.get("objection_prep") or {}).get("objections", [])
                actual = outcome.get("objections") or []
                if predicted and actual:
                    objection_comparisons += 1
                    predicted_texts = {
                        o.get("objection", "").lower()
                        for o in predicted
                        if isinstance(o, dict)
                    }
                    actual_lower = {o.lower() for o in actual}
                    if predicted_texts & actual_lower:
                        objection_matches += 1

        # Build quality conversion models
        conversion_by_quality: dict[str, QualityConversion] = {}
        for q, stats in quality_stats.items():
            total = stats["total"]
            meetings = stats["meetings"]
            conversion_by_quality[q] = QualityConversion(
                total=total,
                meetings=meetings,
                rate=round(meetings / total * 100, 1) if total > 0 else 0.0,
            )

        objection_accuracy = (
            round(objection_matches / objection_comparisons, 2)
            if objection_comparisons > 0
            else 0.0
        )

        avg_quality = max(
            set(meeting_qualities), key=meeting_qualities.count
        ) if meeting_qualities else "N/A"

        # Build persona summaries
        persona_summaries = []
        for pid, p_outcomes in persona_outcomes.items():
            persona_summaries.append(PersonaSummary(
                persona_id=pid,
                persona_title=persona_titles.get(pid),
                funnel=self._build_conversion_funnel(p_outcomes, total_briefs=len([
                    b for b in briefs_with_outcomes
                    if self._extract_persona_from_brief(b.get("brief_json") or {})[0] == pid
                ])),
                avg_duration=self._compute_avg_duration(p_outcomes),
                top_objections=self._extract_top_items(p_outcomes, "objections"),
                top_buying_signals=self._extract_top_items(p_outcomes, "buying_signals"),
            ))

        # Build tier analytics
        tier_analytics = []
        for t, t_outcomes in tier_outcomes.items():
            scores = tier_scores.get(t, [])
            tier_analytics.append(TierAnalytics(
                tier=t,
                funnel=self._build_conversion_funnel(t_outcomes),
                avg_duration=self._compute_avg_duration(t_outcomes),
                avg_score=round(sum(scores) / len(scores), 1) if scores else 0.0,
            ))

        return BriefEffectivenessResponse(
            total_briefs_used=total_briefs,
            total_outcomes_linked=total_linked,
            conversion_by_quality=conversion_by_quality,
            objection_prediction_accuracy=objection_accuracy,
            avg_brief_quality_for_meetings=avg_quality,
            persona_effectiveness=persona_summaries,
            tier_analytics=tier_analytics,
            phone_type_impact=self._compute_phone_type_impact(all_outcomes),
            overall_funnel=self._build_conversion_funnel(all_outcomes, total_briefs=total_briefs),
        )

    def get_persona_effectiveness(self, persona_id: str) -> PersonaEffectivenessDetail:
        """
        Deep dive into a specific persona's effectiveness.

        Args:
            persona_id: Persona identifier (e.g., 'av_director')

        Returns:
            Per-trigger breakdown, top objections/signals, phone impact
        """
        briefs = supabase_client.get_briefs_with_outcomes(persona_id=persona_id)

        all_outcomes: list[dict[str, Any]] = []
        trigger_outcomes: dict[str, list[dict[str, Any]]] = {}
        persona_title: str | None = None

        for brief in briefs:
            brief_json = brief.get("brief_json") or {}
            _, title = self._extract_persona_from_brief(brief_json)
            if title:
                persona_title = title

            trigger = (brief_json.get("trigger") or brief.get("trigger") or "unknown")
            outcomes = brief.get("call_outcomes", [])
            for outcome in outcomes:
                all_outcomes.append(outcome)
                trigger_outcomes.setdefault(trigger, []).append(outcome)

        # Build per-trigger breakdown
        by_trigger = []
        for trig, t_outcomes in trigger_outcomes.items():
            by_trigger.append(ScriptTriggerPerformance(
                trigger=trig,
                funnel=self._build_conversion_funnel(t_outcomes),
                avg_duration=self._compute_avg_duration(t_outcomes),
                sample_size_warning=len(t_outcomes) < 5,
            ))

        return PersonaEffectivenessDetail(
            persona_id=persona_id,
            persona_title=persona_title,
            overall_funnel=self._build_conversion_funnel(all_outcomes, total_briefs=len(briefs)),
            by_trigger=by_trigger,
            top_objections=self._extract_top_items(all_outcomes, "objections"),
            top_buying_signals=self._extract_top_items(all_outcomes, "buying_signals"),
            phone_type_impact=self._compute_phone_type_impact(all_outcomes),
            avg_duration=self._compute_avg_duration(all_outcomes),
        )

    def get_script_effectiveness(self) -> ScriptEffectivenessResponse:
        """
        Script matrix — every persona x trigger combination ranked by meeting rate.
        """
        briefs = supabase_client.get_briefs_with_outcomes()

        # Group outcomes by (persona, trigger)
        combo_outcomes: dict[tuple[str | None, str | None], list[dict[str, Any]]] = {}

        for brief in briefs:
            brief_json = brief.get("brief_json") or {}
            persona_id, _ = self._extract_persona_from_brief(brief_json)
            trigger = brief_json.get("trigger") or brief.get("trigger")

            outcomes = brief.get("call_outcomes", [])
            for outcome in outcomes:
                combo_outcomes.setdefault((persona_id, trigger), []).append(outcome)

        rows: list[ScriptTemplateRow] = []
        for (persona, trigger), outcomes in combo_outcomes.items():
            rows.append(ScriptTemplateRow(
                persona=persona,
                trigger=trigger,
                funnel=self._build_conversion_funnel(outcomes),
                avg_duration=self._compute_avg_duration(outcomes),
                sample_size_warning=len(outcomes) < 5,
            ))

        # Sort by meeting rate descending
        rows.sort(key=lambda r: r.funnel.meeting_rate, reverse=True)

        # Best/worst with minimum 5 sample threshold
        eligible = [r for r in rows if not r.sample_size_warning]
        best = eligible[0] if eligible else None
        worst = eligible[-1] if eligible else None

        return ScriptEffectivenessResponse(
            rows=rows,
            best_performing=best,
            worst_performing=worst,
        )

    # =========================================================================
    # Private helpers — effectiveness analytics
    # =========================================================================

    @staticmethod
    def _build_conversion_funnel(
        outcomes: list[dict[str, Any]], total_briefs: int = 0
    ) -> ConversionFunnel:
        """Build a ConversionFunnel from a list of outcome dicts."""
        total_outcomes = len(outcomes)
        connections = sum(
            1 for o in outcomes if o.get("disposition") == "connected"
        )
        meetings = sum(1 for o in outcomes if o.get("result") == "meeting_booked")
        follow_ups = sum(1 for o in outcomes if o.get("result") == "follow_up_needed")
        qualified_out = sum(1 for o in outcomes if o.get("result") == "qualified_out")
        nurture = sum(1 for o in outcomes if o.get("result") == "nurture")
        dead = sum(1 for o in outcomes if o.get("result") == "dead")
        no_contact = sum(1 for o in outcomes if o.get("result") == "no_contact")

        connect_rate = round(connections / total_outcomes * 100, 1) if total_outcomes > 0 else 0.0
        meeting_rate = round(meetings / connections * 100, 1) if connections > 0 else 0.0
        conversion_rate = round(meetings / total_outcomes * 100, 1) if total_outcomes > 0 else 0.0

        return ConversionFunnel(
            total_briefs=total_briefs,
            total_outcomes=total_outcomes,
            connections=connections,
            meetings_booked=meetings,
            follow_ups=follow_ups,
            qualified_out=qualified_out,
            nurture=nurture,
            dead=dead,
            no_contact=no_contact,
            connect_rate=connect_rate,
            meeting_rate=meeting_rate,
            conversion_rate=conversion_rate,
        )

    @staticmethod
    def _compute_phone_type_impact(
        outcomes: list[dict[str, Any]]
    ) -> list[PhoneTypeImpact]:
        """Compute phone type effectiveness from outcomes."""
        phone_data: dict[str, dict[str, int]] = {}
        for o in outcomes:
            pt = (o.get("phone_type") or "unknown").lower()
            stats = phone_data.setdefault(pt, {"dials": 0, "connections": 0, "meetings": 0})
            stats["dials"] += 1
            if o.get("disposition") == "connected":
                stats["connections"] += 1
            if o.get("result") == "meeting_booked":
                stats["meetings"] += 1

        result = []
        for pt, stats in phone_data.items():
            dials = stats["dials"]
            connections = stats["connections"]
            meetings = stats["meetings"]
            result.append(PhoneTypeImpact(
                phone_type=pt,
                dials=dials,
                connections=connections,
                meetings=meetings,
                connect_rate=round(connections / dials * 100, 1) if dials > 0 else 0.0,
                meeting_rate=round(meetings / connections * 100, 1) if connections > 0 else 0.0,
            ))
        return result

    @staticmethod
    def _extract_top_items(
        outcomes: list[dict[str, Any]], field: str, limit: int = 3
    ) -> list[dict[str, int]]:
        """Extract frequency-sorted top items from an outcome field (objections/buying_signals)."""
        counts: dict[str, int] = {}
        for o in outcomes:
            items = o.get(field) or []
            for item in items:
                if isinstance(item, str) and item.strip():
                    counts[item.strip().lower()] = counts.get(item.strip().lower(), 0) + 1

        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [{k: v} for k, v in sorted_items[:limit]]

    @staticmethod
    def _compute_avg_duration(outcomes: list[dict[str, Any]]) -> float:
        """Compute average call duration for connected calls only."""
        durations = [
            o.get("duration_seconds", 0)
            for o in outcomes
            if o.get("disposition") == "connected"
            and o.get("duration_seconds", 0) > 0
        ]
        return round(sum(durations) / len(durations), 1) if durations else 0.0

    @staticmethod
    def _extract_persona_from_brief(
        brief_json: dict[str, Any]
    ) -> tuple[str | None, str | None]:
        """Extract persona_id and persona_title from brief_json."""
        contact = brief_json.get("contact") or {}
        persona_id = contact.get("persona_id")
        persona_title = contact.get("persona_title") or contact.get("title")

        if not persona_id:
            qual = brief_json.get("qualification") or {}
            persona_id = qual.get("persona")

        return persona_id, persona_title

    @staticmethod
    def _extract_tier_from_brief(brief_json: dict[str, Any]) -> str | None:
        """Extract tier from brief_json qualification data."""
        qual = brief_json.get("qualification") or {}
        return qual.get("tier")

    # =========================================================================
    # Private helpers — follow-up & lead management
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
