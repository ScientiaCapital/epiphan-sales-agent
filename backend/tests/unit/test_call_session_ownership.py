"""Tests for WebSocket session ownership hardening.

Verifies that:
1. Sessions are bound to the user who created them (via JWT sub claim)
2. Other users cannot access, modify, or end another user's session
3. Ownership checks apply to both REST and manager-level operations
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.routes.call_session import (
    _handle_competitor_query,
    _handle_end_call,
    _handle_objection,
)
from app.data.call_session_schemas import CallSessionState
from app.main import app
from app.services.call_session.manager import CallSessionManager

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client() -> TestClient:
    """Test client with JWT bypass already applied by conftest."""
    return TestClient(app)


@pytest.fixture
def manager() -> CallSessionManager:
    """Fresh CallSessionManager for each test."""
    return CallSessionManager()


@pytest.fixture
def mock_brief() -> dict[str, Any]:
    """Minimal mock brief for start_session."""
    return {
        "contact": {"name": "John Doe", "persona": "av_director"},
        "company": {"name": "Test University"},
        "qualification": {"tier": "tier_1"},
        "script": {},
        "brief_quality": "high",
        "intelligence_gaps": [],
        "processing_time_ms": 2500.0,
    }


# =============================================================================
# Manager-Level Ownership Tests
# =============================================================================


class TestManagerOwnership:
    """Test ownership enforcement at the CallSessionManager level."""

    @pytest.mark.asyncio
    async def test_session_stores_user_id(self, manager: CallSessionManager) -> None:
        """Starting a session stores the user_id on the session state."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}

            session, _ = await manager.start_session(
                lead_id="lead-123",
                user_id="tim",
            )

            assert session.user_id == "tim"

    @pytest.mark.asyncio
    async def test_get_session_owner_allowed(self, manager: CallSessionManager) -> None:
        """Session owner can retrieve their own session."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}

            session, _ = await manager.start_session(
                lead_id="lead-123",
                user_id="tim",
            )

            result = manager.get_session(session.session_id, user_id="tim")
            assert result is not None
            assert result.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_get_session_wrong_user_denied(self, manager: CallSessionManager) -> None:
        """Non-owner cannot retrieve another user's session."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}

            session, _ = await manager.start_session(
                lead_id="lead-123",
                user_id="tim",
            )

            result = manager.get_session(session.session_id, user_id="attacker")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_session_no_user_id_skips_check(self, manager: CallSessionManager) -> None:
        """When user_id is None, ownership check is skipped (backward compat)."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}

            session, _ = await manager.start_session(
                lead_id="lead-123",
                user_id="tim",
            )

            result = manager.get_session(session.session_id, user_id=None)
            assert result is not None

    @pytest.mark.asyncio
    async def test_default_user_id_is_anonymous(self, manager: CallSessionManager) -> None:
        """Without explicit user_id, session defaults to 'anonymous'."""
        with patch.object(manager, "_generate_brief", new_callable=AsyncMock) as mock_brief:
            mock_brief.return_value = {"contact": {}, "company": {}, "qualification": {}}

            session, _ = await manager.start_session(lead_id="lead-123")
            assert session.user_id == "anonymous"


# =============================================================================
# REST Endpoint Ownership Tests
# =============================================================================


class TestRestOwnership:
    """Test that REST endpoints enforce session ownership."""

    def test_get_session_wrong_user_returns_404(self, client: TestClient) -> None:
        """GET /api/call-session/{id} returns 404 for wrong user."""
        with patch("app.api.routes.call_session.call_session_manager") as mock_mgr:
            # Ownership check fails → returns None → 404
            mock_mgr.get_session.return_value = None

            response = client.get("/api/call-session/sess-123")
            assert response.status_code == 404

            # Verify the manager was called with user_id from JWT override
            mock_mgr.get_session.assert_called_once_with("sess-123", user_id="test-user")

    def test_competitor_query_wrong_user_returns_404(self, client: TestClient) -> None:
        """POST /api/call-session/{id}/competitor returns 404 for wrong user."""
        with patch("app.api.routes.call_session.call_session_manager") as mock_mgr:
            mock_mgr.get_session.return_value = None

            response = client.post("/api/call-session/sess-123/competitor", json={
                "competitor_name": "Zoom",
                "context": "test",
            })
            assert response.status_code == 404
            mock_mgr.get_session.assert_called_once_with("sess-123", user_id="test-user")

    def test_objection_query_wrong_user_returns_404(self, client: TestClient) -> None:
        """POST /api/call-session/{id}/objection returns 404 for wrong user."""
        with patch("app.api.routes.call_session.call_session_manager") as mock_mgr:
            mock_mgr.get_session.return_value = None

            response = client.post("/api/call-session/sess-123/objection", json={
                "objection_text": "Not interested",
            })
            assert response.status_code == 404
            mock_mgr.get_session.assert_called_once_with("sess-123", user_id="test-user")

    def test_end_session_wrong_user_returns_404(self, client: TestClient) -> None:
        """POST /api/call-session/{id}/end returns 404 for wrong user."""
        with patch("app.api.routes.call_session.call_session_manager") as mock_mgr:
            mock_mgr.get_session.return_value = None

            response = client.post("/api/call-session/sess-123/end", json={
                "disposition": "connected",
                "result": "meeting_booked",
            })
            assert response.status_code == 404
            mock_mgr.get_session.assert_called_once_with("sess-123", user_id="test-user")

    def test_start_session_passes_user_id(self, client: TestClient, mock_brief: dict[str, Any]) -> None:
        """POST /api/call-session/start passes JWT sub claim to manager."""
        session = CallSessionState(
            session_id="sess-new",
            user_id="test-user",
            lead_id="lead-123",
        )

        with patch("app.api.routes.call_session.call_session_manager") as mock_mgr:
            mock_mgr.start_session = AsyncMock(return_value=(session, mock_brief))

            response = client.post("/api/call-session/start", json={
                "lead_id": "lead-123",
            })

            assert response.status_code == 200
            # Verify user_id was passed from the JWT override fixture
            mock_mgr.start_session.assert_called_once_with(
                lead_id="lead-123",
                lead_email=None,
                user_id="test-user",
            )


# =============================================================================
# WebSocket Handler Ownership Tests
# =============================================================================


class TestWsHandlerOwnership:
    """Test that internal WS handler functions enforce session ownership."""

    @pytest.mark.asyncio
    async def test_competitor_query_wrong_user_returns_error(self) -> None:
        """_handle_competitor_query returns error if user doesn't own session."""
        with patch("app.api.routes.call_session.call_session_manager") as mock_mgr:
            mock_mgr.get_session.return_value = None  # ownership check fails

            result = await _handle_competitor_query(
                "sess-123",
                {"competitor_name": "Zoom", "context": "test"},
                user_id="attacker",
            )

            assert result["data"]["message"] == "Session not found"
            mock_mgr.get_session.assert_called_once_with("sess-123", user_id="attacker")

    @pytest.mark.asyncio
    async def test_objection_wrong_user_returns_error(self) -> None:
        """_handle_objection returns error if user doesn't own session."""
        with patch("app.api.routes.call_session.call_session_manager") as mock_mgr:
            mock_mgr.get_session.return_value = None

            result = await _handle_objection(
                "sess-123",
                {"objection_text": "Not interested"},
                user_id="attacker",
            )

            assert result["data"]["message"] == "Session not found"
            mock_mgr.get_session.assert_called_once_with("sess-123", user_id="attacker")

    @pytest.mark.asyncio
    async def test_end_call_wrong_user_returns_error(self) -> None:
        """_handle_end_call returns error if user doesn't own session."""
        with patch("app.api.routes.call_session.call_session_manager") as mock_mgr:
            mock_mgr.get_session.return_value = None

            result = await _handle_end_call(
                "sess-123",
                {"disposition": "connected", "result": "meeting_booked"},
                user_id="attacker",
            )

            assert result["data"]["message"] == "Session not found"
            mock_mgr.get_session.assert_called_once_with("sess-123", user_id="attacker")
