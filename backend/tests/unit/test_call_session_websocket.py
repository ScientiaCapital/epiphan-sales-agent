"""Tests for WebSocket call session endpoint.

Tests WebSocket connect/disconnect, message routing, auth via query token,
invalid message handling, and error responses.
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client() -> TestClient:
    """Test client with JWT bypass already applied by conftest."""
    return TestClient(app)


@pytest.fixture
def mock_brief() -> dict[str, Any]:
    """Mock brief response from CallSessionManager."""
    return {
        "contact": {"name": "John Doe", "persona": "av_director"},
        "company": {"name": "Test University"},
        "qualification": {"tier": "tier_1", "score": 85.0},
        "script": {"personalized_script": "Hi John..."},
        "brief_quality": "high",
        "intelligence_gaps": [],
        "processing_time_ms": 2500.0,
    }


# =============================================================================
# Connection & Auth
# =============================================================================


class TestWebSocketConnection:
    """Test WebSocket connection and authentication."""

    def test_connect_with_valid_token(self, client: TestClient) -> None:
        """Valid JWT token allows WebSocket connection."""
        with patch("app.api.routes.call_session.get_current_user", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = {"sub": "tim", "role": "bdr"}

            with client.websocket_connect("/ws/call-session?token=valid-jwt") as _ws:
                pass  # Connection accepted — just verifying we connected

    def test_connect_without_token_rejected(self, client: TestClient) -> None:
        """Missing token rejects the WebSocket connection."""
        with (
            patch("app.api.routes.call_session.get_current_user", new_callable=AsyncMock) as mock_auth,
            pytest.raises(Exception, match=""),
        ):
            mock_auth.side_effect = Exception("Invalid token")
            with client.websocket_connect("/ws/call-session?token=") as _ws:
                pass

    def test_connect_with_invalid_token_rejected(self, client: TestClient) -> None:
        """Invalid token rejects the WebSocket connection."""
        with (
            patch("app.api.routes.call_session.get_current_user", new_callable=AsyncMock) as mock_auth,
            pytest.raises(Exception, match=""),
        ):
            mock_auth.side_effect = Exception("Token expired")
            with client.websocket_connect("/ws/call-session?token=expired-jwt") as _ws:
                pass


# =============================================================================
# Message Routing
# =============================================================================


class TestMessageRouting:
    """Test WebSocket message type routing."""

    def test_start_call_returns_brief(self, client: TestClient, mock_brief: dict) -> None:
        """start_call message triggers brief generation and returns it."""
        from app.data.call_session_schemas import CallSessionState

        mock_session = CallSessionState(
            session_id="sess-123",
            lead_id="lead-123",
        )

        with (
            patch("app.api.routes.call_session.get_current_user", new_callable=AsyncMock) as mock_auth,
            patch("app.api.routes.call_session.call_session_manager") as mock_manager,
        ):
            mock_auth.return_value = {"sub": "tim", "role": "bdr"}
            mock_manager.start_session = AsyncMock(return_value=(mock_session, mock_brief))

            with client.websocket_connect("/ws/call-session?token=valid") as ws:
                ws.send_json({
                    "type": "start_call",
                    "data": {"lead_id": "lead-123", "lead_email": "john@test.com"},
                })

                response = ws.receive_json()
                assert response["type"] == "call_brief"
                assert response["data"]["session_id"] == "sess-123"
                assert response["data"]["brief_quality"] == "high"

    def test_competitor_query_returns_response(self, client: TestClient, mock_brief: dict) -> None:
        """competitor_query message returns battlecard data."""
        from app.data.call_session_schemas import CallSessionState

        mock_session = CallSessionState(session_id="sess-123", lead_id="lead-123")

        with (
            patch("app.api.routes.call_session.get_current_user", new_callable=AsyncMock) as mock_auth,
            patch("app.api.routes.call_session.call_session_manager") as mock_manager,
        ):
            mock_auth.return_value = {"sub": "tim", "role": "bdr"}
            mock_manager.start_session = AsyncMock(return_value=(mock_session, mock_brief))
            mock_manager.get_competitor_response = AsyncMock(return_value={
                "response": "Zoom lacks 4K support...",
                "proof_points": ["Pearl supports 4K"],
                "follow_up": "What resolution do you need?",
            })

            with client.websocket_connect("/ws/call-session?token=valid") as ws:
                # Start session first
                ws.send_json({"type": "start_call", "data": {"lead_id": "lead-123"}})
                ws.receive_json()  # Consume brief response

                # Query competitor
                ws.send_json({
                    "type": "competitor_query",
                    "data": {"competitor_name": "Zoom", "context": "They said Zoom is cheaper"},
                })

                response = ws.receive_json()
                assert response["type"] == "competitor_response"
                assert "Zoom" in response["data"]["response"]

    def test_objection_returns_response(self, client: TestClient, mock_brief: dict) -> None:
        """objection message returns persona-matched response."""
        from app.data.call_session_schemas import CallSessionState

        mock_session = CallSessionState(session_id="sess-123", lead_id="lead-123")

        with (
            patch("app.api.routes.call_session.get_current_user", new_callable=AsyncMock) as mock_auth,
            patch("app.api.routes.call_session.call_session_manager") as mock_manager,
        ):
            mock_auth.return_value = {"sub": "tim", "role": "bdr"}
            mock_manager.start_session = AsyncMock(return_value=(mock_session, mock_brief))
            mock_manager.get_objection_response = AsyncMock(return_value={
                "response": "I understand, many felt the same...",
                "discovery_question": "What drove that concern?",
                "persona_context": "Common for AV Directors",
            })

            with client.websocket_connect("/ws/call-session?token=valid") as ws:
                ws.send_json({"type": "start_call", "data": {"lead_id": "lead-123"}})
                ws.receive_json()

                ws.send_json({
                    "type": "objection",
                    "data": {"objection_text": "We already have a solution"},
                })

                response = ws.receive_json()
                assert response["type"] == "objection_response"
                assert "understand" in response["data"]["response"].lower()

    def test_end_call_returns_confirmation(self, client: TestClient, mock_brief: dict) -> None:
        """end_call message logs outcome and returns confirmation."""
        from app.data.call_session_schemas import CallSessionState

        mock_session = CallSessionState(session_id="sess-123", lead_id="lead-123")

        with (
            patch("app.api.routes.call_session.get_current_user", new_callable=AsyncMock) as mock_auth,
            patch("app.api.routes.call_session.call_session_manager") as mock_manager,
        ):
            mock_auth.return_value = {"sub": "tim", "role": "bdr"}
            mock_manager.start_session = AsyncMock(return_value=(mock_session, mock_brief))
            mock_manager.end_session = AsyncMock(return_value={
                "outcome_id": "outcome-456",
                "follow_up_date": "2026-02-08",
                "follow_up_type": "callback",
            })

            with client.websocket_connect("/ws/call-session?token=valid") as ws:
                ws.send_json({"type": "start_call", "data": {"lead_id": "lead-123"}})
                ws.receive_json()

                ws.send_json({
                    "type": "end_call",
                    "data": {
                        "disposition": "connected",
                        "result": "meeting_booked",
                        "notes": "Booked demo for next week",
                    },
                })

                response = ws.receive_json()
                assert response["type"] == "call_logged"
                assert response["data"]["outcome_id"] == "outcome-456"


# =============================================================================
# Error Handling
# =============================================================================


class TestErrorHandling:
    """Test error responses for invalid messages."""

    def test_invalid_message_format(self, client: TestClient) -> None:
        """Invalid JSON message returns error."""
        with patch("app.api.routes.call_session.get_current_user", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = {"sub": "tim", "role": "bdr"}

            with client.websocket_connect("/ws/call-session?token=valid") as ws:
                ws.send_json({"invalid": "format"})

                response = ws.receive_json()
                assert response["type"] == "error"

    def test_competitor_query_before_start(self, client: TestClient) -> None:
        """Competitor query before start_call returns error."""
        with patch("app.api.routes.call_session.get_current_user", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = {"sub": "tim", "role": "bdr"}

            with client.websocket_connect("/ws/call-session?token=valid") as ws:
                ws.send_json({
                    "type": "competitor_query",
                    "data": {"competitor_name": "Zoom", "context": "test"},
                })

                response = ws.receive_json()
                assert response["type"] == "error"
                assert "No active session" in response["data"]["message"]

    def test_end_call_before_start(self, client: TestClient) -> None:
        """end_call before start_call returns error."""
        with patch("app.api.routes.call_session.get_current_user", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = {"sub": "tim", "role": "bdr"}

            with client.websocket_connect("/ws/call-session?token=valid") as ws:
                ws.send_json({
                    "type": "end_call",
                    "data": {"disposition": "connected", "result": "meeting_booked"},
                })

                response = ws.receive_json()
                assert response["type"] == "error"

    def test_start_call_missing_lead_id(self, client: TestClient) -> None:
        """start_call without lead_id returns error."""
        with patch("app.api.routes.call_session.get_current_user", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = {"sub": "tim", "role": "bdr"}

            with client.websocket_connect("/ws/call-session?token=valid") as ws:
                ws.send_json({
                    "type": "start_call",
                    "data": {},
                })

                response = ws.receive_json()
                assert response["type"] == "error"
                assert "lead_id" in response["data"]["message"].lower()

    def test_objection_before_start(self, client: TestClient) -> None:
        """Objection query before start_call returns error."""
        with patch("app.api.routes.call_session.get_current_user", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = {"sub": "tim", "role": "bdr"}

            with client.websocket_connect("/ws/call-session?token=valid") as ws:
                ws.send_json({
                    "type": "objection",
                    "data": {"objection_text": "Not interested"},
                })

                response = ws.receive_json()
                assert response["type"] == "error"
                assert "No active session" in response["data"]["message"]
