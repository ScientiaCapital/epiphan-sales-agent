"""Call session manager for Voice AI integration.

Manages in-memory session state during live sales calls. Orchestrates
existing agents (call brief, competitor intel, call outcomes) without
duplicating any logic.

Tim makes ~20 calls/day with 1 active at a time, so in-memory state is fine.
Briefs and outcomes are persisted to Supabase via existing code paths.
"""

import logging
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from app.data.call_session_schemas import CallSessionState
from app.data.personas import get_persona_by_id

logger = logging.getLogger(__name__)


class CallSessionManager:
    """Manages active call sessions with agent orchestration.

    Session lifecycle:
    1. start_session() — generates call brief, caches lead context
    2. get_competitor_response() — real-time battlecard lookup
    3. get_objection_response() — persona-matched objection handling
    4. end_session() — logs call outcome linked to brief
    """

    def __init__(self) -> None:
        """Initialize with empty session store."""
        self._sessions: dict[str, CallSessionState] = {}

    @property
    def active_session_count(self) -> int:
        """Number of active sessions."""
        return len(self._sessions)

    def get_session(self, session_id: str) -> CallSessionState | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    async def start_session(
        self,
        lead_id: str,
        lead_email: str | None = None,
    ) -> tuple[CallSessionState, dict[str, Any]]:
        """Start a new call session and generate a call brief.

        Args:
            lead_id: Lead identifier (HubSpot ID or internal).
            lead_email: Optional email for enrichment lookup.

        Returns:
            Tuple of (session_state, brief_dict). Brief dict is the full
            CallBriefResponse serialized, or a minimal fallback on failure.
        """
        session_id = str(uuid.uuid4())
        session = CallSessionState(
            session_id=session_id,
            lead_id=lead_id,
            lead_email=lead_email,
            started_at=datetime.now(timezone.utc),
        )

        # Generate call brief using existing assembler
        brief_dict = await self._generate_brief(session)

        # Extract persona from brief for later objection matching
        contact = brief_dict.get("contact", {})
        if isinstance(contact, dict):
            session.persona_id = contact.get("persona")

        # Cache lead context for session
        session.lead_context = {
            "contact": brief_dict.get("contact", {}),
            "company": brief_dict.get("company", {}),
            "qualification": brief_dict.get("qualification", {}),
        }

        # Fetch prior interaction context (lazy import, graceful degradation)
        user_context = await self._safe_get_user_context(lead_id)
        if user_context and user_context.interaction_count > 0:
            session.lead_context["prior_interactions"] = {
                "interaction_count": user_context.interaction_count,
                "last_interaction": user_context.last_interaction.isoformat() if user_context.last_interaction else None,
                "objections_seen": user_context.objections_seen,
                "account_notes": user_context.account_notes,
            }

        self._sessions[session_id] = session

        logger.info(
            "Call session started",
            extra={
                "session_id": session_id,
                "lead_id": lead_id,
                "persona_id": session.persona_id,
                "brief_quality": brief_dict.get("brief_quality"),
            },
        )

        return session, brief_dict

    async def get_competitor_response(
        self,
        session_id: str,
        competitor_name: str,
        context: str,
    ) -> dict[str, Any]:
        """Get a competitor battlecard response during a live call.

        Args:
            session_id: Active session ID.
            competitor_name: Competitor mentioned by the prospect.
            context: What the prospect said about the competitor.

        Returns:
            Dict with response, proof_points, and follow_up.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        # Track competitor mention in session
        if competitor_name not in session.competitors_mentioned:
            session.competitors_mentioned.append(competitor_name)

        # Run competitor intel agent
        try:
            from app.services.langgraph.agents.competitor_intel import competitor_intel_agent

            result = await competitor_intel_agent.run(
                competitor_name=competitor_name,
                context=context,
                query_type="claim",
            )

            return {
                "response": result.get("response", ""),
                "proof_points": result.get("proof_points", []),
                "follow_up": result.get("follow_up_question"),
            }
        except Exception:
            logger.exception("Competitor agent failed for session %s", session_id)
            return {
                "response": f"I don't have specific data on {competitor_name} right now. Ask about their specific capability and I can help position Epiphan.",
                "proof_points": [],
                "follow_up": "What specific feature of theirs are you comparing?",
            }

    async def get_objection_response(
        self,
        session_id: str,
        objection_text: str,
    ) -> dict[str, Any]:
        """Get a persona-matched objection response during a live call.

        Matches the objection text against known persona objections using
        fuzzy matching. Falls back to generic response if no match found.

        Args:
            session_id: Active session ID.
            objection_text: The objection raised by the prospect.

        Returns:
            Dict with response, discovery_question, and persona_context.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        # Track objection in session
        session.objections_raised.append(objection_text)

        # Try persona-specific objection matching
        if session.persona_id:
            match = self._match_persona_objection(session.persona_id, objection_text)
            if match:
                return match

        # Fallback: generic objection response
        return {
            "response": "I understand your concern. Many of our customers felt the same way before seeing how Epiphan's approach is different.",
            "discovery_question": "Can you help me understand what's driving that concern specifically?",
            "persona_context": None,
        }

    async def end_session(
        self,
        session_id: str,
        disposition: str,
        result: str,
        notes: str | None = None,
        duration_seconds: int = 0,
        objections: list[str] | None = None,
        competitor_mentioned: str | None = None,
    ) -> dict[str, Any]:
        """End a call session and log the outcome.

        Args:
            session_id: Active session ID.
            disposition: Call disposition (connected, voicemail, etc.).
            result: Call result (meeting_booked, follow_up_needed, etc.).
            notes: Optional BDR notes.
            duration_seconds: Call duration.
            objections: Objections raised (defaults to session-tracked ones).
            competitor_mentioned: Competitor mentioned (defaults to first session-tracked one).

        Returns:
            Dict with outcome_id, follow_up_date, and follow_up_type.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        # Use session-tracked data as defaults
        if objections is None and session.objections_raised:
            objections = session.objections_raised
        if competitor_mentioned is None and session.competitors_mentioned:
            competitor_mentioned = session.competitors_mentioned[0]

        # Log outcome using existing service
        outcome_result = await self._log_outcome(
            session=session,
            disposition=disposition,
            result=result,
            notes=notes,
            duration_seconds=duration_seconds,
            objections=objections,
            competitor_mentioned=competitor_mentioned,
        )

        # Record interaction in user memory
        notes_summary = notes or f"{disposition} - {result}"
        await self._safe_record_interaction(session.lead_id, "call", notes_summary, result)

        # Record any objections raised during the call
        if session.objections_raised:
            for objection_text in session.objections_raised:
                await self._safe_add_objection(session.lead_id, objection_text)

        # Clean up session
        del self._sessions[session_id]

        logger.info(
            "Call session ended",
            extra={
                "session_id": session_id,
                "lead_id": session.lead_id,
                "disposition": disposition,
                "result": result,
                "objections_count": len(session.objections_raised),
                "competitors_count": len(session.competitors_mentioned),
            },
        )

        return outcome_result

    async def _safe_get_user_context(self, lead_id: str) -> Any:
        """Fetch user context from memory store. Never fails."""
        try:
            from app.services.langgraph.memory.user_store import user_memory

            return await user_memory.get_user_context(lead_id)
        except Exception:
            logger.debug("User memory context fetch failed for %s", lead_id)
            return None

    async def _safe_record_interaction(
        self, lead_id: str, interaction_type: str, summary: str, outcome: str
    ) -> None:
        """Record interaction in user memory. Never fails."""
        try:
            from app.services.langgraph.memory.user_store import user_memory

            await user_memory.record_interaction(lead_id, interaction_type, summary, outcome)
        except Exception:
            logger.debug("User memory record failed for %s", lead_id)

    async def _safe_add_objection(self, lead_id: str, objection: str) -> None:
        """Record objection in user memory. Never fails."""
        try:
            from app.services.langgraph.memory.user_store import user_memory

            await user_memory.add_objection(lead_id, objection)
        except Exception:
            logger.debug("User memory objection record failed for %s", lead_id)

    def _match_persona_objection(
        self,
        persona_id: str,
        objection_text: str,
    ) -> dict[str, Any] | None:
        """Match objection text against known persona objections.

        Uses fuzzy matching (SequenceMatcher) with 0.4 threshold to find
        the best matching objection from the persona profile.
        """
        profile = get_persona_by_id(persona_id)
        if not profile or not profile.objections:
            return None

        objection_lower = objection_text.lower()
        best_match = None
        best_ratio = 0.0

        for obj in profile.objections:
            ratio = SequenceMatcher(None, objection_lower, obj.objection.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = obj

        if best_match and best_ratio >= 0.4:
            return {
                "response": best_match.response,
                "discovery_question": None,
                "persona_context": f"Common objection for {profile.title}",
            }

        return None

    async def _generate_brief(
        self,
        session: CallSessionState,
    ) -> dict[str, Any]:
        """Generate a call brief using the existing assembler.

        Returns the brief as a dict (serialized CallBriefResponse).
        Falls back to a minimal dict on failure.
        """
        try:
            from app.api.routes.call_brief import save_call_brief
            from app.data.lead_schemas import Lead
            from app.services.langgraph.agents.call_brief import (
                CallBriefAssembler,
                CallBriefRequest,
            )

            # Build a Lead object from the session data
            lead = Lead(
                hubspot_id=session.lead_id,
                email=session.lead_email or f"{session.lead_id}@placeholder.local",
            )

            assembler = CallBriefAssembler()
            request = CallBriefRequest(lead=lead)
            brief = await assembler.assemble(request)

            # Persist brief for feedback loop
            brief_id = save_call_brief(brief, lead_id=session.lead_id)
            if brief_id:
                brief.brief_id = brief_id
                session.brief_id = brief_id

            return brief.model_dump(mode="json")
        except Exception:
            logger.exception("Brief generation failed for session %s", session.session_id)
            return {
                "contact": {},
                "company": {},
                "qualification": {},
                "script": {},
                "objection_prep": {},
                "discovery_prep": {},
                "competitor_prep": {},
                "reference_story": {},
                "brief_quality": "low",
                "intelligence_gaps": ["Brief generation failed — using manual prep"],
                "processing_time_ms": 0.0,
            }

    async def _log_outcome(
        self,
        session: CallSessionState,
        disposition: str,
        result: str,
        notes: str | None,
        duration_seconds: int,
        objections: list[str] | None,
        competitor_mentioned: str | None,
    ) -> dict[str, Any]:
        """Log call outcome using existing CallOutcomeService.

        Returns dict with outcome_id, follow_up_date, and follow_up_type.
        Falls back to a confirmation-only dict on failure.
        """
        try:
            from app.data.call_outcome_schemas import CallDisposition, CallOutcomeCreate, CallResult
            from app.services.call_outcomes.service import CallOutcomeService

            outcome_create = CallOutcomeCreate(
                lead_id=session.lead_id,
                phone_number_dialed="voice_ai_session",
                disposition=CallDisposition(disposition),
                result=CallResult(result),
                duration_seconds=duration_seconds,
                notes=notes,
                objections=objections,
                competitor_mentioned=competitor_mentioned,
                call_brief_id=session.brief_id,
            )

            service = CallOutcomeService()
            log_result = service.log_outcome(outcome_create)

            outcome = log_result.outcome
            return {
                "outcome_id": outcome.id,
                "follow_up_date": outcome.follow_up_date.isoformat() if outcome.follow_up_date else None,
                "follow_up_type": outcome.follow_up_type,
            }
        except Exception:
            logger.exception("Outcome logging failed for session %s", session.session_id)
            return {
                "outcome_id": "failed",
                "follow_up_date": None,
                "follow_up_type": None,
                "error": "Outcome logging failed — log manually in HubSpot",
            }


# Singleton instance
call_session_manager = CallSessionManager()
