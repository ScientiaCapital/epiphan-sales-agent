"""Tests for REST call session fallback endpoints.

Tests the REST equivalents of the WebSocket endpoints:
POST /api/call-session/start, /{id}/competitor, /{id}/objection, /{id}/end, GET /{id}
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
    """Mock brief response."""
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
# Start Session
# =============================================================================


class TestStartSession:
    """Test POST /api/call-session/start."""

    def test_start_session_success(self, client: TestClient, mock_brief: dict) -> None:
        """Starting a session returns session_id and brief."""
        from app.data.call_session_schemas import CallSessionState

        mock_session = CallSessionState(
            session_id="sess-rest-123",
            lead_id="lead-123",
            brief_id="brief-uuid",
        )

        with patch("app.api.routes.call_session.call_session_manager") as mock_manager:
            mock_manager.start_session = AsyncMock(return_value=(mock_session, mock_brief))

            response = client.post("/api/call-session/start", json={
                "lead_id": "lead-123",
                "lead_email": "john@test.com",
            })

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "sess-rest-123"
            assert data["brief"]["brief_quality"] == "high"
            assert data["brief_id"] == "brief-uuid"

    def test_start_session_without_email(self, client: TestClient, mock_brief: dict) -> None:
        """Starting a session without email still works."""
        from app.data.call_session_schemas import CallSessionState

        mock_session = CallSessionState(session_id="sess-456", lead_id="lead-456")

        with patch("app.api.routes.call_session.call_session_manager") as mock_manager:
            mock_manager.start_session = AsyncMock(return_value=(mock_session, mock_brief))

            response = client.post("/api/call-session/start", json={"lead_id": "lead-456"})

            assert response.status_code == 200

    def test_start_session_missing_lead_id(self, client: TestClient) -> None:
        """Missing lead_id returns 422."""
        response = client.post("/api/call-session/start", json={})
        assert response.status_code == 422


# =============================================================================
# Competitor Query
# =============================================================================


class TestCompetitorQuery:
    """Test POST /api/call-session/{id}/competitor."""

    def test_competitor_query_success(self, client: TestClient) -> None:
        """Competitor query returns response."""
        from app.data.call_session_schemas import CallSessionState

        mock_session = CallSessionState(session_id="sess-123", lead_id="lead-123")

        with patch("app.api.routes.call_session.call_session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session
            mock_manager.get_competitor_response = AsyncMock(return_value={
                "response": "Zoom lacks enterprise reliability...",
                "proof_points": ["99.9% uptime SLA"],
                "follow_up": "What's your uptime requirement?",
            })

            response = client.post("/api/call-session/sess-123/competitor", json={
                "competitor_name": "Zoom",
                "context": "They said Zoom works fine",
            })

            assert response.status_code == 200
            data = response.json()
            assert "Zoom" in data["response"]

    def test_competitor_query_session_not_found(self, client: TestClient) -> None:
        """Competitor query on missing session returns 404."""
        with patch("app.api.routes.call_session.call_session_manager") as mock_manager:
            mock_manager.get_session.return_value = None

            response = client.post("/api/call-session/bad-id/competitor", json={
                "competitor_name": "Zoom",
                "context": "test",
            })

            assert response.status_code == 404


# =============================================================================
# Objection Query
# =============================================================================


class TestObjectionQuery:
    """Test POST /api/call-session/{id}/objection."""

    def test_objection_query_success(self, client: TestClient) -> None:
        """Objection query returns response."""
        from app.data.call_session_schemas import CallSessionState

        mock_session = CallSessionState(session_id="sess-123", lead_id="lead-123")

        with patch("app.api.routes.call_session.call_session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session
            mock_manager.get_objection_response = AsyncMock(return_value={
                "response": "I hear you. Many AV Directors felt the same...",
                "discovery_question": "What solution are you currently using?",
                "persona_context": "AV Director",
            })

            response = client.post("/api/call-session/sess-123/objection", json={
                "objection_text": "We already have a solution",
            })

            assert response.status_code == 200
            data = response.json()
            assert "response" in data

    def test_objection_query_session_not_found(self, client: TestClient) -> None:
        """Objection query on missing session returns 404."""
        with patch("app.api.routes.call_session.call_session_manager") as mock_manager:
            mock_manager.get_session.return_value = None

            response = client.post("/api/call-session/bad-id/objection", json={
                "objection_text": "Not interested",
            })

            assert response.status_code == 404


# =============================================================================
# End Session
# =============================================================================


class TestEndSession:
    """Test POST /api/call-session/{id}/end."""

    def test_end_session_success(self, client: TestClient) -> None:
        """Ending a session logs outcome and returns confirmation."""
        from app.data.call_session_schemas import CallSessionState

        mock_session = CallSessionState(session_id="sess-123", lead_id="lead-123")

        with patch("app.api.routes.call_session.call_session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session
            mock_manager.end_session = AsyncMock(return_value={
                "outcome_id": "outcome-789",
                "follow_up_date": "2026-02-08",
                "follow_up_type": "callback",
            })

            response = client.post("/api/call-session/sess-123/end", json={
                "disposition": "connected",
                "result": "meeting_booked",
                "notes": "Booked demo",
                "duration_seconds": 180,
            })

            assert response.status_code == 200
            data = response.json()
            assert data["outcome_id"] == "outcome-789"

    def test_end_session_not_found(self, client: TestClient) -> None:
        """Ending a missing session returns 404."""
        with patch("app.api.routes.call_session.call_session_manager") as mock_manager:
            mock_manager.get_session.return_value = None

            response = client.post("/api/call-session/bad-id/end", json={
                "disposition": "connected",
                "result": "meeting_booked",
            })

            assert response.status_code == 404


# =============================================================================
# Get Session State
# =============================================================================


class TestGetSession:
    """Test GET /api/call-session/{id}."""

    def test_get_session_success(self, client: TestClient) -> None:
        """Getting a session returns its current state."""
        from app.data.call_session_schemas import CallSessionState

        mock_session = CallSessionState(
            session_id="sess-123",
            lead_id="lead-123",
            lead_email="john@test.com",
            brief_id="brief-uuid",
            persona_id="av_director",
            objections_raised=["Too expensive"],
            competitors_mentioned=["Zoom"],
        )

        with patch("app.api.routes.call_session.call_session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session

            response = client.get("/api/call-session/sess-123")

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "sess-123"
            assert data["lead_id"] == "lead-123"
            assert data["persona_id"] == "av_director"
            assert "Zoom" in data["competitors_mentioned"]

    def test_get_session_not_found(self, client: TestClient) -> None:
        """Getting a missing session returns 404."""
        with patch("app.api.routes.call_session.call_session_manager") as mock_manager:
            mock_manager.get_session.return_value = None

            response = client.get("/api/call-session/bad-id")

            assert response.status_code == 404
