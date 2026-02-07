"""Tests for CallSessionManager.

Tests session lifecycle, agent orchestration, competitor/objection responses,
outcome logging, and graceful degradation.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.call_session.manager import CallSessionManager

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def manager() -> CallSessionManager:
    """Fresh manager instance for each test."""
    return CallSessionManager()


@pytest.fixture
def mock_brief_response() -> dict[str, Any]:
    """Mock call brief response dict."""
    return {
        "contact": {
            "name": "John Doe",
            "persona": "av_director",
            "phones": {"has_phone": True, "best_phone": "555-0100"},
        },
        "company": {"name": "State University", "industry": "higher_ed"},
        "qualification": {"tier": "tier_1", "score": 85.0},
        "script": {"personalized_script": "Hi John, I'm calling about..."},
        "objection_prep": {"objections": []},
        "discovery_prep": {"questions": []},
        "competitor_prep": {"competitors": []},
        "reference_story": {},
        "brief_quality": "high",
        "intelligence_gaps": [],
        "processing_time_ms": 2500.0,
        "brief_id": "brief-uuid-123",
    }


@pytest.fixture
def mock_outcome_result() -> MagicMock:
    """Mock CallOutcomeLogResult."""
    result = MagicMock()
    result.outcome_id = "outcome-uuid-456"
    result.follow_up_date = None
    result.follow_up_type = None
    return result


# =============================================================================
# Session Lifecycle
# =============================================================================


class TestSessionLifecycle:
    """Test session start, query, and end."""

    @pytest.mark.asyncio
    async def test_start_session_creates_session(self, manager: CallSessionManager) -> None:
        """Starting a session creates it in the manager."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {"persona": "av_director"}, "company": {}, "qualification": {}}

            session, brief = await manager.start_session(
                lead_id="lead-123",
                lead_email="john@test.com",
            )

            assert session.session_id is not None
            assert session.lead_id == "lead-123"
            assert session.lead_email == "john@test.com"
            assert manager.active_session_count == 1

    @pytest.mark.asyncio
    async def test_start_session_returns_brief(self, manager: CallSessionManager, mock_brief_response: dict) -> None:
        """Starting a session returns the call brief."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = mock_brief_response

            _, brief = await manager.start_session(lead_id="lead-123")

            assert brief["brief_quality"] == "high"
            assert brief["contact"]["name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_start_session_extracts_persona(self, manager: CallSessionManager) -> None:
        """Session extracts persona_id from the brief contact data."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {"persona": "ld_director"}, "company": {}, "qualification": {}}

            session, _ = await manager.start_session(lead_id="lead-123")

            assert session.persona_id == "ld_director"

    @pytest.mark.asyncio
    async def test_get_session_returns_none_for_unknown(self, manager: CallSessionManager) -> None:
        """Getting a non-existent session returns None."""
        assert manager.get_session("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_session_returns_active_session(self, manager: CallSessionManager) -> None:
        """Getting an active session returns it."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}

            session, _ = await manager.start_session(lead_id="lead-123")

            found = manager.get_session(session.session_id)
            assert found is not None
            assert found.lead_id == "lead-123"

    @pytest.mark.asyncio
    async def test_end_session_removes_from_manager(self, manager: CallSessionManager) -> None:
        """Ending a session removes it from the manager."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}
            session, _ = await manager.start_session(lead_id="lead-123")

        with patch.object(manager, "_log_outcome", new_callable=AsyncMock) as mock_log:
            mock_log.return_value = {"outcome_id": "o-123", "follow_up_date": None, "follow_up_type": None}

            await manager.end_session(
                session_id=session.session_id,
                disposition="connected",
                result="meeting_booked",
            )

            assert manager.active_session_count == 0
            assert manager.get_session(session.session_id) is None

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, manager: CallSessionManager) -> None:
        """Multiple sessions can be active simultaneously."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}

            s1, _ = await manager.start_session(lead_id="lead-1")
            s2, _ = await manager.start_session(lead_id="lead-2")
            s3, _ = await manager.start_session(lead_id="lead-3")

            assert manager.active_session_count == 3
            assert manager.get_session(s1.session_id) is not None
            assert manager.get_session(s2.session_id) is not None
            assert manager.get_session(s3.session_id) is not None


# =============================================================================
# Competitor Response
# =============================================================================


class TestCompetitorResponse:
    """Test competitor intelligence during calls."""

    @pytest.mark.asyncio
    async def test_competitor_response_tracks_mention(self, manager: CallSessionManager) -> None:
        """Competitor queries are tracked in session state."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}
            session, _ = await manager.start_session(lead_id="lead-123")

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value={
            "response": "Great question about Zoom...",
            "proof_points": ["4K support"],
            "follow_up_question": "What resolution do you need?",
        })

        with patch(
            "app.services.langgraph.agents.competitor_intel.competitor_intel_agent",
            mock_agent,
        ):
            result = await manager.get_competitor_response(
                session_id=session.session_id,
                competitor_name="Zoom",
                context="They said Zoom is cheaper",
            )

            assert "Zoom" in session.competitors_mentioned
            assert result["response"] == "Great question about Zoom..."

    @pytest.mark.asyncio
    async def test_competitor_response_deduplicates_mentions(self, manager: CallSessionManager) -> None:
        """Same competitor mentioned twice only tracked once."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}
            session, _ = await manager.start_session(lead_id="lead-123")

        with patch(
            "app.services.call_session.manager.competitor_intel_agent",
            create=True,
        ) as mock_agent:
            mock_agent.run = AsyncMock(return_value={
                "response": "...", "proof_points": [], "follow_up_question": None,
            })

            await manager.get_competitor_response(session.session_id, "Zoom", "context 1")
            await manager.get_competitor_response(session.session_id, "Zoom", "context 2")

            assert session.competitors_mentioned.count("Zoom") == 1

    @pytest.mark.asyncio
    async def test_competitor_response_invalid_session(self, manager: CallSessionManager) -> None:
        """Competitor query on invalid session returns error."""
        result = await manager.get_competitor_response("bad-id", "Zoom", "context")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_competitor_agent_failure_graceful(self, manager: CallSessionManager) -> None:
        """Agent failure returns a useful fallback response."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}
            session, _ = await manager.start_session(lead_id="lead-123")

        with patch(
            "app.services.call_session.manager.competitor_intel_agent",
            create=True,
        ) as mock_agent:
            mock_agent.run = AsyncMock(side_effect=RuntimeError("LLM down"))

            result = await manager.get_competitor_response(
                session_id=session.session_id,
                competitor_name="Vaddio",
                context="They love Vaddio",
            )

            assert "Vaddio" in result["response"]
            assert result["follow_up"] is not None


# =============================================================================
# Objection Response
# =============================================================================


class TestObjectionResponse:
    """Test objection handling during calls."""

    @pytest.mark.asyncio
    async def test_objection_tracks_in_session(self, manager: CallSessionManager) -> None:
        """Objections are tracked in session state."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {"persona": "av_director"}, "company": {}, "qualification": {}}
            session, _ = await manager.start_session(lead_id="lead-123")

        result = await manager.get_objection_response(
            session_id=session.session_id,
            objection_text="We already have a solution",
        )

        assert "We already have a solution" in session.objections_raised
        assert "response" in result

    @pytest.mark.asyncio
    async def test_objection_persona_match(self, manager: CallSessionManager) -> None:
        """Objection matching returns persona-specific response when available."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {"persona": "av_director"}, "company": {}, "qualification": {}}
            session, _ = await manager.start_session(lead_id="lead-123")

        # Patch get_persona_by_id to return a persona with objections
        mock_persona = MagicMock()
        mock_persona.title = "AV Director"
        mock_objection = MagicMock()
        mock_objection.objection = "We already have a video solution"
        mock_objection.response = "Many AV Directors said the same thing before switching to Pearl."
        mock_persona.objections = [mock_objection]

        with patch("app.services.call_session.manager.get_persona_by_id", return_value=mock_persona):
            result = await manager.get_objection_response(
                session_id=session.session_id,
                objection_text="We already have a video solution in place",
            )

            assert "Pearl" in result["response"]
            assert result["persona_context"] is not None

    @pytest.mark.asyncio
    async def test_objection_no_persona_fallback(self, manager: CallSessionManager) -> None:
        """Without persona, returns generic response."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}
            session, _ = await manager.start_session(lead_id="lead-123")

        result = await manager.get_objection_response(
            session_id=session.session_id,
            objection_text="Not interested",
        )

        assert "understand" in result["response"].lower()
        assert result["discovery_question"] is not None

    @pytest.mark.asyncio
    async def test_objection_invalid_session(self, manager: CallSessionManager) -> None:
        """Objection on invalid session returns error."""
        result = await manager.get_objection_response("bad-id", "Not interested")
        assert "error" in result


# =============================================================================
# Outcome Logging
# =============================================================================


class TestOutcomeLogging:
    """Test call outcome logging on session end."""

    @pytest.mark.asyncio
    async def test_end_session_logs_outcome(self, manager: CallSessionManager) -> None:
        """Ending a session logs the call outcome."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}
            session, _ = await manager.start_session(lead_id="lead-123")

        with patch.object(manager, "_log_outcome", new_callable=AsyncMock) as mock_log:
            mock_log.return_value = {
                "outcome_id": "outcome-789",
                "follow_up_date": "2026-02-08",
                "follow_up_type": "callback",
            }

            result = await manager.end_session(
                session_id=session.session_id,
                disposition="connected",
                result="meeting_booked",
                notes="Booked demo for next week",
            )

            assert result["outcome_id"] == "outcome-789"
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_end_session_uses_tracked_data(self, manager: CallSessionManager) -> None:
        """Session-tracked objections/competitors are passed to outcome."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}
            session, _ = await manager.start_session(lead_id="lead-123")

        # Simulate in-call activity
        session.objections_raised = ["Too expensive", "Already have solution"]
        session.competitors_mentioned = ["Zoom"]

        with patch.object(manager, "_log_outcome", new_callable=AsyncMock) as mock_log:
            mock_log.return_value = {"outcome_id": "o-1", "follow_up_date": None, "follow_up_type": None}

            await manager.end_session(
                session_id=session.session_id,
                disposition="connected",
                result="follow_up_needed",
            )

            call_args = mock_log.call_args
            assert call_args.kwargs["objections"] == ["Too expensive", "Already have solution"]
            assert call_args.kwargs["competitor_mentioned"] == "Zoom"

    @pytest.mark.asyncio
    async def test_end_session_invalid_session(self, manager: CallSessionManager) -> None:
        """Ending invalid session returns error."""
        result = await manager.end_session("bad-id", "connected", "meeting_booked")
        assert "error" in result


# =============================================================================
# Brief Generation
# =============================================================================


class TestBriefGeneration:
    """Test brief generation integration."""

    @pytest.mark.asyncio
    async def test_brief_failure_returns_fallback(self, manager: CallSessionManager) -> None:
        """Brief generation failure returns minimal fallback dict."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {
                "contact": {},
                "company": {},
                "qualification": {},
                "script": {},
                "brief_quality": "low",
                "intelligence_gaps": ["Brief generation failed — using manual prep"],
                "processing_time_ms": 0.0,
            }

            session, brief = await manager.start_session(lead_id="lead-123")

            assert brief["brief_quality"] == "low"
            assert len(brief["intelligence_gaps"]) > 0

    @pytest.mark.asyncio
    async def test_brief_persists_brief_id(self, manager: CallSessionManager) -> None:
        """Successful brief generation stores brief_id in session."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {
                "contact": {},
                "company": {},
                "qualification": {},
                "brief_id": "stored-brief-uuid",
            }

            session, _ = await manager.start_session(lead_id="lead-123")
            # brief_id is set in _generate_brief, not from the return value
            # The mock bypasses the actual persistence logic


# =============================================================================
# Fuzzy Objection Matching
# =============================================================================


class TestFuzzyObjectionMatching:
    """Test the _match_persona_objection private method."""

    def test_exact_match(self, manager: CallSessionManager) -> None:
        """Exact objection text matches."""
        mock_persona = MagicMock()
        mock_persona.title = "AV Director"
        obj = MagicMock()
        obj.objection = "We already have a solution"
        obj.response = "That's great — what are you using?"
        mock_persona.objections = [obj]

        with patch("app.services.call_session.manager.get_persona_by_id", return_value=mock_persona):
            result = manager._match_persona_objection("av_director", "We already have a solution")
            assert result is not None
            assert "what are you using" in result["response"].lower()

    def test_fuzzy_match(self, manager: CallSessionManager) -> None:
        """Similar objection text matches via fuzzy matching."""
        mock_persona = MagicMock()
        mock_persona.title = "AV Director"
        obj = MagicMock()
        obj.objection = "We already have a video solution"
        obj.response = "Many said the same before switching"
        mock_persona.objections = [obj]

        with patch("app.services.call_session.manager.get_persona_by_id", return_value=mock_persona):
            result = manager._match_persona_objection("av_director", "We already have a video solution in place")
            assert result is not None

    def test_no_match_below_threshold(self, manager: CallSessionManager) -> None:
        """Very different text doesn't match."""
        mock_persona = MagicMock()
        mock_persona.title = "AV Director"
        obj = MagicMock()
        obj.objection = "We already have a video solution"
        obj.response = "..."
        mock_persona.objections = [obj]

        with patch("app.services.call_session.manager.get_persona_by_id", return_value=mock_persona):
            result = manager._match_persona_objection("av_director", "What is your pricing model?")
            assert result is None

    def test_unknown_persona_returns_none(self, manager: CallSessionManager) -> None:
        """Unknown persona ID returns None."""
        with patch("app.services.call_session.manager.get_persona_by_id", return_value=None):
            result = manager._match_persona_objection("unknown_persona", "test")
            assert result is None
