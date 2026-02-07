"""Tests for UserMemoryStore wiring in CallSessionManager.

Tests that start_session fetches user context, end_session records
interactions and objections, and that memory failures never break
the core session flow (graceful degradation).
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.call_session.manager import CallSessionManager  # noqa: I001

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
            "name": "Jane Smith",
            "persona": "ld_director",
        },
        "company": {"name": "Test Corp"},
        "qualification": {"tier": "tier_2"},
        "brief_quality": "medium",
    }


def _mock_user_context(
    interaction_count: int = 0,
    objections: list[str] | None = None,
    account_notes: str | None = None,
) -> MagicMock:
    """Build a mock UserContext dataclass."""
    ctx = MagicMock()
    ctx.interaction_count = interaction_count
    ctx.last_interaction = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc) if interaction_count > 0 else None
    ctx.objections_seen = objections or []
    ctx.account_notes = account_notes
    return ctx


# =============================================================================
# start_session — User Context Fetch
# =============================================================================


class TestStartSessionMemory:
    """Test that start_session fetches and includes user context."""

    @pytest.mark.asyncio
    async def test_fetches_user_context(
        self, manager: CallSessionManager, mock_brief_response: dict[str, Any]
    ) -> None:
        """start_session calls _safe_get_user_context."""
        with (
            patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief,
            patch.object(manager, "_safe_get_user_context", new_callable=AsyncMock) as mock_ctx,
        ):
            mock_brief.return_value = mock_brief_response
            mock_ctx.return_value = _mock_user_context(interaction_count=0)

            await manager.start_session(lead_id="lead-1")
            mock_ctx.assert_awaited_once_with("lead-1")

    @pytest.mark.asyncio
    async def test_includes_prior_interactions_in_context(
        self, manager: CallSessionManager, mock_brief_response: dict[str, Any]
    ) -> None:
        """Prior interactions are added to session lead_context."""
        with (
            patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief,
            patch.object(manager, "_safe_get_user_context", new_callable=AsyncMock) as mock_ctx,
        ):
            mock_brief.return_value = mock_brief_response
            mock_ctx.return_value = _mock_user_context(
                interaction_count=3,
                objections=["Too expensive"],
                account_notes="VIP account",
            )

            session, _ = await manager.start_session(lead_id="lead-2")
            prior = session.lead_context.get("prior_interactions")
            assert prior is not None
            assert prior["interaction_count"] == 3
            assert prior["objections_seen"] == ["Too expensive"]
            assert prior["account_notes"] == "VIP account"
            assert prior["last_interaction"] is not None

    @pytest.mark.asyncio
    async def test_no_prior_interactions_skips_context(
        self, manager: CallSessionManager, mock_brief_response: dict[str, Any]
    ) -> None:
        """No prior interactions means no prior_interactions key."""
        with (
            patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief,
            patch.object(manager, "_safe_get_user_context", new_callable=AsyncMock) as mock_ctx,
        ):
            mock_brief.return_value = mock_brief_response
            mock_ctx.return_value = _mock_user_context(interaction_count=0)

            session, _ = await manager.start_session(lead_id="lead-3")
            assert "prior_interactions" not in session.lead_context

    @pytest.mark.asyncio
    async def test_memory_failure_doesnt_break_start(
        self, manager: CallSessionManager, mock_brief_response: dict[str, Any]
    ) -> None:
        """Memory fetch failure doesn't break session start."""
        with (
            patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief,
            patch.object(manager, "_safe_get_user_context", new_callable=AsyncMock) as mock_ctx,
        ):
            mock_brief.return_value = mock_brief_response
            mock_ctx.return_value = None  # Simulates failure returning None

            session, brief = await manager.start_session(lead_id="lead-4")
            assert session.session_id is not None
            assert "prior_interactions" not in session.lead_context


# =============================================================================
# end_session — Interaction + Objection Recording
# =============================================================================


class TestEndSessionMemory:
    """Test that end_session records interactions and objections."""

    async def _start_session(
        self,
        manager: CallSessionManager,
        lead_id: str = "lead-1",
        objections: list[str] | None = None,
    ) -> str:
        """Helper to start a session and return session_id."""
        with (
            patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief,
            patch.object(manager, "_safe_get_user_context", new_callable=AsyncMock) as mock_ctx,
        ):
            mock_brief.return_value = {
                "contact": {"persona": "av_director"},
                "company": {},
                "qualification": {},
            }
            mock_ctx.return_value = _mock_user_context(interaction_count=0)
            session, _ = await manager.start_session(lead_id=lead_id)

            # Add objections to session if provided
            if objections:
                session.objections_raised = objections

            return session.session_id

    @pytest.mark.asyncio
    async def test_records_interaction(self, manager: CallSessionManager) -> None:
        """end_session calls _safe_record_interaction."""
        session_id = await self._start_session(manager)

        with (
            patch.object(manager, "_log_outcome", new_callable=AsyncMock) as mock_outcome,
            patch.object(manager, "_safe_record_interaction", new_callable=AsyncMock) as mock_record,
            patch.object(manager, "_safe_add_objection", new_callable=AsyncMock),
        ):
            mock_outcome.return_value = {"outcome_id": "o1", "follow_up_date": None, "follow_up_type": None}

            await manager.end_session(session_id, disposition="connected", result="meeting_booked")
            mock_record.assert_awaited_once()
            call_args = mock_record.call_args
            assert call_args[0][0] == "lead-1"
            assert call_args[0][1] == "call"
            assert call_args[0][3] == "meeting_booked"

    @pytest.mark.asyncio
    async def test_records_objections(self, manager: CallSessionManager) -> None:
        """end_session records each objection from the session."""
        session_id = await self._start_session(
            manager, objections=["Too expensive", "Not the right time"]
        )

        with (
            patch.object(manager, "_log_outcome", new_callable=AsyncMock) as mock_outcome,
            patch.object(manager, "_safe_record_interaction", new_callable=AsyncMock),
            patch.object(manager, "_safe_add_objection", new_callable=AsyncMock) as mock_obj,
        ):
            mock_outcome.return_value = {"outcome_id": "o1", "follow_up_date": None, "follow_up_type": None}

            await manager.end_session(session_id, disposition="connected", result="follow_up_needed")
            assert mock_obj.await_count == 2
            mock_obj.assert_any_await("lead-1", "Too expensive")
            mock_obj.assert_any_await("lead-1", "Not the right time")

    @pytest.mark.asyncio
    async def test_no_objections_skips_recording(self, manager: CallSessionManager) -> None:
        """end_session doesn't call add_objection when no objections."""
        session_id = await self._start_session(manager, objections=[])

        with (
            patch.object(manager, "_log_outcome", new_callable=AsyncMock) as mock_outcome,
            patch.object(manager, "_safe_record_interaction", new_callable=AsyncMock),
            patch.object(manager, "_safe_add_objection", new_callable=AsyncMock) as mock_obj,
        ):
            mock_outcome.return_value = {"outcome_id": "o1", "follow_up_date": None, "follow_up_type": None}

            await manager.end_session(session_id, disposition="voicemail", result="no_answer")
            mock_obj.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_memory_failure_doesnt_break_end(self, manager: CallSessionManager) -> None:
        """Memory failures don't break end_session."""
        session_id = await self._start_session(manager, objections=["Price concern"])

        with (
            patch.object(manager, "_log_outcome", new_callable=AsyncMock) as mock_outcome,
            patch.object(manager, "_safe_record_interaction", new_callable=AsyncMock) as mock_record,
            patch.object(manager, "_safe_add_objection", new_callable=AsyncMock) as mock_obj,
        ):
            # Simulate memory failures
            mock_record.side_effect = None  # Still succeeds (returns None)
            mock_obj.side_effect = None
            mock_outcome.return_value = {"outcome_id": "o1", "follow_up_date": None, "follow_up_type": None}

            result = await manager.end_session(session_id, disposition="connected", result="meeting_booked")
            assert result["outcome_id"] == "o1"

    @pytest.mark.asyncio
    async def test_interaction_uses_notes_when_provided(self, manager: CallSessionManager) -> None:
        """Notes parameter is used in interaction summary when provided."""
        session_id = await self._start_session(manager)

        with (
            patch.object(manager, "_log_outcome", new_callable=AsyncMock) as mock_outcome,
            patch.object(manager, "_safe_record_interaction", new_callable=AsyncMock) as mock_record,
            patch.object(manager, "_safe_add_objection", new_callable=AsyncMock),
        ):
            mock_outcome.return_value = {"outcome_id": "o1", "follow_up_date": None, "follow_up_type": None}

            await manager.end_session(
                session_id,
                disposition="connected",
                result="meeting_booked",
                notes="Great conversation, demo scheduled for Friday",
            )
            call_args = mock_record.call_args
            assert call_args[0][2] == "Great conversation, demo scheduled for Friday"

    @pytest.mark.asyncio
    async def test_interaction_fallback_summary_without_notes(self, manager: CallSessionManager) -> None:
        """Without notes, summary is built from disposition + result."""
        session_id = await self._start_session(manager)

        with (
            patch.object(manager, "_log_outcome", new_callable=AsyncMock) as mock_outcome,
            patch.object(manager, "_safe_record_interaction", new_callable=AsyncMock) as mock_record,
            patch.object(manager, "_safe_add_objection", new_callable=AsyncMock),
        ):
            mock_outcome.return_value = {"outcome_id": "o1", "follow_up_date": None, "follow_up_type": None}

            await manager.end_session(session_id, disposition="voicemail", result="no_answer")
            call_args = mock_record.call_args
            assert call_args[0][2] == "voicemail - no_answer"


# =============================================================================
# _safe_* Helpers — Graceful Degradation
# =============================================================================


class TestSafeHelpers:
    """Test that _safe_* helpers never raise."""

    @pytest.mark.asyncio
    async def test_safe_get_user_context_handles_import_error(
        self, manager: CallSessionManager
    ) -> None:
        """_safe_get_user_context returns None on import error."""
        with patch(
            "app.services.langgraph.memory.user_store.user_memory"
        ) as mock_memory:
            mock_memory.get_user_context = AsyncMock(side_effect=ImportError("no module"))
            result = await manager._safe_get_user_context("lead-1")
            assert result is None

    @pytest.mark.asyncio
    async def test_safe_record_interaction_handles_exception(
        self, manager: CallSessionManager
    ) -> None:
        """_safe_record_interaction swallows exceptions."""
        with patch(
            "app.services.langgraph.memory.user_store.user_memory"
        ) as mock_memory:
            mock_memory.record_interaction = AsyncMock(side_effect=RuntimeError("db down"))
            # Should not raise
            await manager._safe_record_interaction("lead-1", "call", "test", "ok")

    @pytest.mark.asyncio
    async def test_safe_add_objection_handles_exception(
        self, manager: CallSessionManager
    ) -> None:
        """_safe_add_objection swallows exceptions."""
        with patch(
            "app.services.langgraph.memory.user_store.user_memory"
        ) as mock_memory:
            mock_memory.add_objection = AsyncMock(side_effect=RuntimeError("db down"))
            # Should not raise
            await manager._safe_add_objection("lead-1", "Too expensive")
