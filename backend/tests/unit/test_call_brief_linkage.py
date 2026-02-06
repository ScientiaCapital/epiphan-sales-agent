"""Tests for call brief ↔ call outcome linkage.

Tests the feedback loop: persisted call briefs linked to outcomes
so agents can learn which scripts/briefs lead to meetings.

TDD RED: These tests will fail until the implementation is complete.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.data.call_outcome_schemas import (
    CallDisposition,
    CallOutcomeCreate,
    CallOutcomeResponse,
    CallResult,
)
from app.data.lead_schemas import Lead
from app.main import app
from app.services.langgraph.agents.call_brief import (
    BriefQuality,
    CallBriefResponse,
    CallScript,
    CompanySnapshot,
    CompetitorPrep,
    ContactInfo,
    DiscoveryPrep,
    ObjectionPrep,
    PhoneInfo,
    QualificationSummary,
    ReferenceStoryBrief,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_lead() -> Lead:
    """Create a sample lead for testing."""
    return Lead(
        hubspot_id="test_123",
        email="john.doe@university.edu",
        first_name="John",
        last_name="Doe",
        company="State University",
        title="AV Director",
        phone="555-0100",
        industry="higher_ed",
        persona_match="av_director",
    )


@pytest.fixture
def sample_request_body() -> dict[str, Any]:
    """Sample API request body for call brief."""
    return {
        "lead": {
            "hubspot_id": "test_123",
            "email": "john@university.edu",
            "first_name": "John",
            "last_name": "Doe",
            "company": "State University",
            "title": "AV Director",
            "phone": "555-0100",
            "industry": "higher_ed",
            "persona_match": "av_director",
        },
        "trigger": "content_download",
        "call_type": "warm",
        "research_depth": "quick",
    }


@pytest.fixture
def mock_brief() -> CallBriefResponse:
    """Create a mock brief response with brief_id."""
    return CallBriefResponse(
        brief_id="brief-uuid-001",
        contact=ContactInfo(
            name="John Doe",
            title="AV Director",
            phones=PhoneInfo(mobile_phone="555-0100"),
        ),
        company=CompanySnapshot(
            name="State University",
            industry="Higher Education",
        ),
        qualification=QualificationSummary(
            tier="Tier 1",
            score=82,
            confidence=0.9,
        ),
        script=CallScript(
            personalized_script="Hi John, I noticed your team...",
        ),
        objection_prep=ObjectionPrep(),
        discovery_prep=DiscoveryPrep(),
        competitor_prep=CompetitorPrep(),
        reference_story=ReferenceStoryBrief(),
        brief_quality=BriefQuality.HIGH,
        intelligence_gaps=[],
        processing_time_ms=1500.0,
    )


# =============================================================================
# 1. CallBriefResponse includes brief_id
# =============================================================================


class TestCallBriefResponseHasBriefId:
    """Verify CallBriefResponse schema includes a brief_id field."""

    def test_brief_response_has_brief_id_field(self, mock_brief: CallBriefResponse) -> None:
        """CallBriefResponse should have a brief_id string field."""
        assert hasattr(mock_brief, "brief_id")
        assert mock_brief.brief_id == "brief-uuid-001"

    def test_brief_response_brief_id_in_serialization(self, mock_brief: CallBriefResponse) -> None:
        """brief_id should appear in JSON serialization."""
        data = mock_brief.model_dump()
        assert "brief_id" in data
        assert data["brief_id"] == "brief-uuid-001"

    def test_brief_response_brief_id_is_string(self, mock_brief: CallBriefResponse) -> None:
        """brief_id must be a string (UUID)."""
        assert isinstance(mock_brief.brief_id, str)
        assert len(mock_brief.brief_id) > 0


# =============================================================================
# 2. Call Brief API endpoint persists brief and returns brief_id
# =============================================================================


class TestCallBriefEndpointPersistence:
    """Verify POST /api/agents/call-brief persists the brief and returns brief_id."""

    def test_call_brief_endpoint_returns_brief_id(
        self,
        client: TestClient,
        sample_request_body: dict[str, Any],
        mock_brief: CallBriefResponse,
    ) -> None:
        """API response should include brief_id in the brief object."""
        with patch(
            "app.api.routes.call_brief._assembler.assemble",
            new_callable=AsyncMock,
            return_value=mock_brief,
        ):
            response = client.post("/api/agents/call-brief", json=sample_request_body)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "brief_id" in data["brief"]
        assert data["brief"]["brief_id"] == "brief-uuid-001"

    def test_call_brief_endpoint_calls_save(
        self,
        client: TestClient,
        sample_request_body: dict[str, Any],
        mock_brief: CallBriefResponse,
    ) -> None:
        """Endpoint should call save_brief on the supabase client."""
        with (
            patch(
                "app.api.routes.call_brief._assembler.assemble",
                new_callable=AsyncMock,
                return_value=mock_brief,
            ),
            patch(
                "app.api.routes.call_brief.save_call_brief",
                return_value={"id": "brief-uuid-001"},
            ) as mock_save,
        ):
            response = client.post("/api/agents/call-brief", json=sample_request_body)
        assert response.status_code == 200
        mock_save.assert_called_once()


# =============================================================================
# 3. CallOutcomeCreate accepts optional call_brief_id
# =============================================================================


class TestCallOutcomeCreateWithBriefId:
    """Verify CallOutcomeCreate schema accepts an optional call_brief_id."""

    def test_outcome_create_accepts_call_brief_id(self) -> None:
        """CallOutcomeCreate should accept an optional call_brief_id."""
        outcome = CallOutcomeCreate(
            lead_id="lead-001",
            phone_number_dialed="555-0100",
            disposition=CallDisposition.CONNECTED,
            result=CallResult.MEETING_BOOKED,
            call_brief_id="brief-uuid-001",
        )
        assert outcome.call_brief_id == "brief-uuid-001"

    def test_outcome_create_brief_id_defaults_to_none(self) -> None:
        """call_brief_id should default to None when not provided."""
        outcome = CallOutcomeCreate(
            lead_id="lead-001",
            phone_number_dialed="555-0100",
            disposition=CallDisposition.CONNECTED,
            result=CallResult.MEETING_BOOKED,
        )
        assert outcome.call_brief_id is None

    def test_outcome_create_serializes_brief_id(self) -> None:
        """call_brief_id should appear in serialized output."""
        outcome = CallOutcomeCreate(
            lead_id="lead-001",
            phone_number_dialed="555-0100",
            disposition=CallDisposition.CONNECTED,
            result=CallResult.MEETING_BOOKED,
            call_brief_id="brief-uuid-001",
        )
        data = outcome.model_dump()
        assert "call_brief_id" in data
        assert data["call_brief_id"] == "brief-uuid-001"


# =============================================================================
# 4. CallOutcomeResponse includes call_brief_id
# =============================================================================


class TestCallOutcomeResponseWithBriefId:
    """Verify CallOutcomeResponse includes call_brief_id."""

    def test_outcome_response_has_call_brief_id(self) -> None:
        """CallOutcomeResponse should have call_brief_id field."""
        response = CallOutcomeResponse(
            id="outcome-001",
            lead_id="lead-001",
            called_at="2026-02-06T10:00:00Z",
            duration_seconds=120,
            phone_number_dialed="555-0100",
            disposition="connected",
            result="meeting_booked",
            call_brief_id="brief-uuid-001",
        )
        assert response.call_brief_id == "brief-uuid-001"

    def test_outcome_response_brief_id_defaults_to_none(self) -> None:
        """call_brief_id should default to None in response."""
        response = CallOutcomeResponse(
            id="outcome-001",
            lead_id="lead-001",
            called_at="2026-02-06T10:00:00Z",
            duration_seconds=120,
            phone_number_dialed="555-0100",
            disposition="connected",
            result="meeting_booked",
        )
        assert response.call_brief_id is None


# =============================================================================
# 5. CallOutcomeService passes call_brief_id to database
# =============================================================================


class TestCallOutcomeServiceBriefId:
    """Verify service layer includes call_brief_id in database insert."""

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_log_outcome_includes_brief_id_in_record(
        self, mock_db: MagicMock
    ) -> None:
        """log_outcome should include call_brief_id in the record data."""
        from app.services.call_outcomes.service import CallOutcomeService

        mock_db.create_call_outcome.return_value = {
            "id": "outcome-001",
            "lead_id": "lead-001",
            "called_at": "2026-02-06T10:00:00Z",
            "duration_seconds": 120,
            "phone_number_dialed": "555-0100",
            "disposition": "connected",
            "result": "meeting_booked",
            "call_brief_id": "brief-uuid-001",
            "follow_up_date": None,
            "follow_up_type": None,
            "notes": None,
            "objections": None,
            "buying_signals": None,
            "competitor_mentioned": None,
            "follow_up_notes": None,
            "hubspot_engagement_id": None,
            "synced_to_hubspot": False,
            "synced_at": None,
            "created_at": "2026-02-06T10:00:00Z",
            "updated_at": "2026-02-06T10:00:00Z",
            "phone_type": None,
        }
        mock_db.update_lead.return_value = {"id": "lead-001"}

        service = CallOutcomeService()
        outcome = CallOutcomeCreate(
            lead_id="lead-001",
            phone_number_dialed="555-0100",
            disposition=CallDisposition.CONNECTED,
            result=CallResult.MEETING_BOOKED,
            call_brief_id="brief-uuid-001",
        )

        service.log_outcome(outcome)

        # Verify call_brief_id was in the insert data
        call_args = mock_db.create_call_outcome.call_args[0][0]
        assert call_args["call_brief_id"] == "brief-uuid-001"

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_log_outcome_omits_brief_id_when_none(
        self, mock_db: MagicMock
    ) -> None:
        """When call_brief_id is None, it should still be included as None."""
        from app.services.call_outcomes.service import CallOutcomeService

        mock_db.create_call_outcome.return_value = {
            "id": "outcome-002",
            "lead_id": "lead-001",
            "called_at": "2026-02-06T10:00:00Z",
            "duration_seconds": 60,
            "phone_number_dialed": "555-0100",
            "disposition": "voicemail",
            "result": "follow_up_needed",
            "call_brief_id": None,
            "follow_up_date": "2026-02-08",
            "follow_up_type": "callback",
            "notes": None,
            "objections": None,
            "buying_signals": None,
            "competitor_mentioned": None,
            "follow_up_notes": None,
            "hubspot_engagement_id": None,
            "synced_to_hubspot": False,
            "synced_at": None,
            "created_at": "2026-02-06T10:00:00Z",
            "updated_at": "2026-02-06T10:00:00Z",
            "phone_type": None,
        }
        mock_db.update_lead.return_value = {"id": "lead-001"}

        service = CallOutcomeService()
        outcome = CallOutcomeCreate(
            lead_id="lead-001",
            phone_number_dialed="555-0100",
            disposition=CallDisposition.VOICEMAIL,
            result=CallResult.FOLLOW_UP_NEEDED,
        )

        service.log_outcome(outcome)
        call_args = mock_db.create_call_outcome.call_args[0][0]
        assert "call_brief_id" in call_args
        assert call_args["call_brief_id"] is None


# =============================================================================
# 6. Call Outcome API accepts call_brief_id
# =============================================================================


class TestCallOutcomeAPIWithBriefId:
    """Verify POST /api/call-outcomes accepts call_brief_id."""

    @patch("app.api.routes.call_outcomes.supabase_client")
    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_log_outcome_api_accepts_brief_id(
        self, mock_service: MagicMock, mock_db: MagicMock, client: TestClient
    ) -> None:
        """POST /api/call-outcomes should accept call_brief_id in request."""
        from app.data.call_outcome_schemas import CallOutcomeLogResult

        mock_db.get_lead_by_id.return_value = {"id": "lead-001"}

        mock_service.log_outcome.return_value = CallOutcomeLogResult(
            success=True,
            outcome=CallOutcomeResponse(
                id="outcome-001",
                lead_id="lead-001",
                called_at="2026-02-06T10:00:00Z",
                duration_seconds=120,
                phone_number_dialed="555-0100",
                disposition="connected",
                result="meeting_booked",
                call_brief_id="brief-uuid-001",
            ),
            lead_updated=True,
            follow_up_scheduled=False,
        )

        response = client.post(
            "/api/call-outcomes",
            json={
                "lead_id": "lead-001",
                "phone_number_dialed": "555-0100",
                "disposition": "connected",
                "result": "meeting_booked",
                "call_brief_id": "brief-uuid-001",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["outcome"]["call_brief_id"] == "brief-uuid-001"


# =============================================================================
# 7. Brief effectiveness analytics
# =============================================================================


class TestBriefEffectivenessAnalytics:
    """Verify GET /api/call-outcomes/brief-effectiveness endpoint."""

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_brief_effectiveness_endpoint_exists(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """GET /api/call-outcomes/brief-effectiveness should return 200."""
        mock_service.get_brief_effectiveness.return_value = {
            "total_briefs_used": 10,
            "total_outcomes_linked": 8,
            "conversion_by_quality": {
                "HIGH": {"total": 5, "meetings": 3, "rate": 0.6},
                "MEDIUM": {"total": 3, "meetings": 1, "rate": 0.33},
                "LOW": {"total": 0, "meetings": 0, "rate": 0.0},
            },
            "objection_prediction_accuracy": 0.65,
            "avg_brief_quality_for_meetings": "HIGH",
        }

        response = client.get("/api/call-outcomes/brief-effectiveness")
        assert response.status_code == 200
        data = response.json()
        assert "total_briefs_used" in data
        assert "conversion_by_quality" in data

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_brief_effectiveness_conversion_by_quality(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Conversion rates should be broken down by brief quality level."""
        mock_service.get_brief_effectiveness.return_value = {
            "total_briefs_used": 20,
            "total_outcomes_linked": 15,
            "conversion_by_quality": {
                "HIGH": {"total": 10, "meetings": 5, "rate": 0.5},
                "MEDIUM": {"total": 5, "meetings": 1, "rate": 0.2},
                "LOW": {"total": 0, "meetings": 0, "rate": 0.0},
            },
            "objection_prediction_accuracy": 0.7,
            "avg_brief_quality_for_meetings": "HIGH",
        }

        response = client.get("/api/call-outcomes/brief-effectiveness")
        data = response.json()
        high = data["conversion_by_quality"]["HIGH"]
        assert high["total"] == 10
        assert high["meetings"] == 5
        assert high["rate"] == 0.5

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_brief_effectiveness_objection_accuracy(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Should include objection prediction accuracy."""
        mock_service.get_brief_effectiveness.return_value = {
            "total_briefs_used": 5,
            "total_outcomes_linked": 5,
            "conversion_by_quality": {
                "HIGH": {"total": 3, "meetings": 2, "rate": 0.67},
                "MEDIUM": {"total": 2, "meetings": 0, "rate": 0.0},
                "LOW": {"total": 0, "meetings": 0, "rate": 0.0},
            },
            "objection_prediction_accuracy": 0.65,
            "avg_brief_quality_for_meetings": "HIGH",
        }

        response = client.get("/api/call-outcomes/brief-effectiveness")
        data = response.json()
        assert "objection_prediction_accuracy" in data
        assert data["objection_prediction_accuracy"] == 0.65


# =============================================================================
# 8. Supabase client has call_briefs methods
# =============================================================================


class TestSupabaseCallBriefMethods:
    """Verify SupabaseClient has methods for call_briefs table."""

    def test_supabase_client_has_save_call_brief(self) -> None:
        """SupabaseClient should have a save_call_brief method."""
        from app.services.database.supabase_client import SupabaseClient

        assert hasattr(SupabaseClient, "save_call_brief")

    def test_supabase_client_has_get_call_brief(self) -> None:
        """SupabaseClient should have a get_call_brief method."""
        from app.services.database.supabase_client import SupabaseClient

        assert hasattr(SupabaseClient, "get_call_brief")

    def test_supabase_client_has_get_briefs_with_outcomes(self) -> None:
        """SupabaseClient should have a method to get briefs joined with outcomes."""
        from app.services.database.supabase_client import SupabaseClient

        assert hasattr(SupabaseClient, "get_briefs_with_outcomes")
