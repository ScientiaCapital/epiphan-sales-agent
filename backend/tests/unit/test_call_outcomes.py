"""Tests for call outcomes API endpoints.

Tests POST /api/call-outcomes, GET /api/call-outcomes/stats,
GET /api/call-outcomes/follow-ups, GET /api/call-outcomes/lead/{id},
POST /api/call-outcomes/batch.
"""

from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.data.call_outcome_schemas import (
    CallOutcomeLogResult,
    CallOutcomeResponse,
    DailyCallStats,
    LeadCallHistory,
    PendingFollowUp,
    PendingFollowUpsResponse,
    PhoneTypeBreakdown,
)
from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


# =============================================================================
# Sample data fixtures
# =============================================================================

SAMPLE_LEAD = {
    "id": "lead-uuid-001",
    "hubspot_id": "hs_123",
    "email": "john@company.com",
    "first_name": "John",
    "last_name": "Doe",
    "company": "Acme Corp",
    "title": "AV Director",
    "contact_count": 2,
    "lead_status": "open",
}

SAMPLE_OUTCOME_RECORD: dict[str, Any] = {
    "id": "outcome-uuid-001",
    "lead_id": "lead-uuid-001",
    "called_at": "2026-02-05T14:30:00+00:00",
    "duration_seconds": 180,
    "phone_number_dialed": "555-0100",
    "phone_type": "direct",
    "disposition": "connected",
    "result": "meeting_booked",
    "notes": "Great conversation, booked demo for Thursday.",
    "objections": ["budget"],
    "buying_signals": ["asked_about_pricing"],
    "competitor_mentioned": "Zoom",
    "follow_up_date": None,
    "follow_up_type": None,
    "follow_up_notes": None,
    "hubspot_engagement_id": None,
    "synced_to_hubspot": False,
    "synced_at": None,
    "created_at": "2026-02-05T14:30:00+00:00",
    "updated_at": "2026-02-05T14:30:00+00:00",
}


def _make_outcome_request(
    disposition: str = "connected",
    result: str = "meeting_booked",
    **overrides: Any,
) -> dict[str, Any]:
    """Helper to build a call outcome request body."""
    body: dict[str, Any] = {
        "lead_id": "lead-uuid-001",
        "phone_number_dialed": "555-0100",
        "phone_type": "direct",
        "disposition": disposition,
        "result": result,
        "duration_seconds": 180,
    }
    body.update(overrides)
    return body


def _mock_log_result(
    follow_up_scheduled: bool = False,
    **overrides: Any,
) -> CallOutcomeLogResult:
    """Helper to build a mock log result."""
    record = {**SAMPLE_OUTCOME_RECORD, **overrides}
    return CallOutcomeLogResult(
        success=True,
        outcome=CallOutcomeResponse(**record),
        lead_updated=True,
        follow_up_scheduled=follow_up_scheduled,
    )


# =============================================================================
# POST /api/call-outcomes
# =============================================================================


class TestLogCallOutcome:
    """Tests for POST /api/call-outcomes."""

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_connected_meeting_booked(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Log a connected call that results in a meeting."""
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_service.log_outcome.return_value = _mock_log_result()

        response = client.post(
            "/api/call-outcomes",
            json=_make_outcome_request(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["outcome"]["disposition"] == "connected"
        assert data["outcome"]["result"] == "meeting_booked"

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_voicemail(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Log a voicemail — should auto-schedule follow-up."""
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_service.log_outcome.return_value = _mock_log_result(
            disposition="voicemail",
            result="no_contact",
            follow_up_scheduled=True,
            follow_up_date="2026-02-07",
            follow_up_type="callback",
        )

        response = client.post(
            "/api/call-outcomes",
            json=_make_outcome_request("voicemail", "no_contact"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["follow_up_scheduled"] is True

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_no_answer(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Log a no-answer call."""
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_service.log_outcome.return_value = _mock_log_result(
            disposition="no_answer", result="no_contact",
        )

        response = client.post(
            "/api/call-outcomes",
            json=_make_outcome_request("no_answer", "no_contact"),
        )
        assert response.status_code == 200

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_wrong_number(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Log wrong number — no follow-up."""
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_service.log_outcome.return_value = _mock_log_result(
            disposition="wrong_number", result="dead",
        )

        response = client.post(
            "/api/call-outcomes",
            json=_make_outcome_request("wrong_number", "dead"),
        )
        assert response.status_code == 200
        assert response.json()["follow_up_scheduled"] is False

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_gatekeeper(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Log gatekeeper encounter."""
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_service.log_outcome.return_value = _mock_log_result(
            disposition="gatekeeper", result="no_contact",
            follow_up_scheduled=True,
        )

        response = client.post(
            "/api/call-outcomes",
            json=_make_outcome_request("gatekeeper", "no_contact"),
        )
        assert response.status_code == 200

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_not_interested(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Log not interested — no follow-up."""
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_service.log_outcome.return_value = _mock_log_result(
            disposition="not_interested", result="dead",
        )

        response = client.post(
            "/api/call-outcomes",
            json=_make_outcome_request("not_interested", "dead"),
        )
        assert response.status_code == 200

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_callback_requested(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Log callback requested with Tim's specified date."""
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_service.log_outcome.return_value = _mock_log_result(
            disposition="callback_requested", result="follow_up_needed",
            follow_up_scheduled=True,
            follow_up_date="2026-02-10",
            follow_up_type="callback",
        )

        response = client.post(
            "/api/call-outcomes",
            json=_make_outcome_request(
                "callback_requested", "follow_up_needed",
                follow_up_date="2026-02-10",
                follow_up_type="callback",
                follow_up_notes="Call back Monday afternoon",
            ),
        )
        assert response.status_code == 200

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_with_objections_and_signals(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Log outcome with objections and buying signals."""
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_service.log_outcome.return_value = _mock_log_result(
            objections=["budget", "timing"],
            buying_signals=["asked_about_pricing", "mentioned_deadline"],
        )

        response = client.post(
            "/api/call-outcomes",
            json=_make_outcome_request(
                objections=["budget", "timing"],
                buying_signals=["asked_about_pricing", "mentioned_deadline"],
            ),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["outcome"]["objections"] == ["budget", "timing"]
        assert data["outcome"]["buying_signals"] == [
            "asked_about_pricing", "mentioned_deadline"
        ]

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_with_competitor_mentioned(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Log outcome with competitor mentioned."""
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_service.log_outcome.return_value = _mock_log_result(
            competitor_mentioned="Zoom",
        )

        response = client.post(
            "/api/call-outcomes",
            json=_make_outcome_request(competitor_mentioned="Zoom"),
        )
        assert response.status_code == 200
        assert response.json()["outcome"]["competitor_mentioned"] == "Zoom"

    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_invalid_lead_404(
        self, mock_db: MagicMock, client: TestClient
    ) -> None:
        """Return 404 when lead doesn't exist."""
        mock_db.get_lead_by_id.return_value = None

        response = client.post(
            "/api/call-outcomes",
            json=_make_outcome_request(lead_id="nonexistent-uuid"),
        )
        assert response.status_code == 404

    def test_invalid_disposition_422(self, client: TestClient) -> None:
        """Return 422 for invalid disposition value."""
        response = client.post(
            "/api/call-outcomes",
            json=_make_outcome_request(disposition="hung_up"),
        )
        assert response.status_code == 422

    def test_missing_phone_number_422(self, client: TestClient) -> None:
        """Return 422 when phone_number_dialed is missing."""
        body = _make_outcome_request()
        del body["phone_number_dialed"]
        response = client.post("/api/call-outcomes", json=body)
        assert response.status_code == 422


# =============================================================================
# GET /api/call-outcomes/stats
# =============================================================================


class TestDailyStats:
    """Tests for GET /api/call-outcomes/stats."""

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_empty_day(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Return zero stats for a day with no calls."""
        mock_service.get_daily_stats.return_value = DailyCallStats(
            date="2026-02-05"
        )

        response = client.get("/api/call-outcomes/stats?date=2026-02-05")
        assert response.status_code == 200
        data = response.json()
        assert data["total_dials"] == 0
        assert data["connect_rate"] == 0.0

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_mixed_dispositions(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Return correct counts for mixed dispositions."""
        mock_service.get_daily_stats.return_value = DailyCallStats(
            date="2026-02-05",
            total_dials=20,
            connections=5,
            voicemails=8,
            no_answers=7,
            meetings_booked=2,
            connect_rate=25.0,
            meeting_rate=40.0,
        )

        response = client.get("/api/call-outcomes/stats?date=2026-02-05")
        assert response.status_code == 200
        data = response.json()
        assert data["total_dials"] == 20
        assert data["connections"] == 5
        assert data["voicemails"] == 8

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_connect_rate_calculation(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Verify connect rate is connections/dials * 100."""
        mock_service.get_daily_stats.return_value = DailyCallStats(
            date="2026-02-05",
            total_dials=10,
            connections=3,
            connect_rate=30.0,
        )

        response = client.get("/api/call-outcomes/stats?date=2026-02-05")
        assert response.json()["connect_rate"] == 30.0

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_meeting_rate_calculation(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Verify meeting rate is meetings/connections * 100."""
        mock_service.get_daily_stats.return_value = DailyCallStats(
            date="2026-02-05",
            total_dials=20,
            connections=4,
            meetings_booked=1,
            meeting_rate=25.0,
        )

        response = client.get("/api/call-outcomes/stats?date=2026-02-05")
        assert response.json()["meeting_rate"] == 25.0

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_phone_type_breakdown(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Return phone type breakdown."""
        mock_service.get_daily_stats.return_value = DailyCallStats(
            date="2026-02-05",
            total_dials=10,
            phone_type_breakdown=PhoneTypeBreakdown(
                direct=4, mobile=3, work=2, company=1
            ),
        )

        response = client.get("/api/call-outcomes/stats?date=2026-02-05")
        breakdown = response.json()["phone_type_breakdown"]
        assert breakdown["direct"] == 4
        assert breakdown["mobile"] == 3

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_avg_duration_connected_only(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Average duration only counts connected calls."""
        mock_service.get_daily_stats.return_value = DailyCallStats(
            date="2026-02-05",
            total_dials=10,
            connections=3,
            avg_call_duration=240.5,
        )

        response = client.get("/api/call-outcomes/stats?date=2026-02-05")
        assert response.json()["avg_call_duration"] == 240.5


# =============================================================================
# GET /api/call-outcomes/lead/{lead_id}
# =============================================================================


class TestLeadCallHistory:
    """Tests for GET /api/call-outcomes/lead/{lead_id}."""

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_returns_all_calls(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Return complete call history for a lead."""
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_service.get_lead_history.return_value = LeadCallHistory(
            lead_id="lead-uuid-001",
            lead_name="John Doe",
            company="Acme Corp",
            total_calls=3,
            total_connections=1,
            last_called=datetime(2026, 2, 5, 14, 30, tzinfo=timezone.utc),
            outcomes=[CallOutcomeResponse(**SAMPLE_OUTCOME_RECORD)],
        )

        response = client.get("/api/call-outcomes/lead/lead-uuid-001")
        assert response.status_code == 200
        data = response.json()
        assert data["total_calls"] == 3
        assert data["total_connections"] == 1

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_empty_history(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Return empty history for a lead with no calls."""
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_service.get_lead_history.return_value = LeadCallHistory(
            lead_id="lead-uuid-001",
            lead_name="John Doe",
            company="Acme Corp",
            total_calls=0,
            total_connections=0,
            outcomes=[],
        )

        response = client.get("/api/call-outcomes/lead/lead-uuid-001")
        assert response.status_code == 200
        assert response.json()["total_calls"] == 0

    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_nonexistent_lead_404(
        self, mock_db: MagicMock, client: TestClient
    ) -> None:
        """Return 404 for nonexistent lead."""
        mock_db.get_lead_by_id.return_value = None

        response = client.get("/api/call-outcomes/lead/nonexistent-uuid")
        assert response.status_code == 404

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_total_connections_count(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Verify total connections counts only connected dispositions."""
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_service.get_lead_history.return_value = LeadCallHistory(
            lead_id="lead-uuid-001",
            total_calls=5,
            total_connections=2,
            outcomes=[],
        )

        response = client.get("/api/call-outcomes/lead/lead-uuid-001")
        assert response.json()["total_connections"] == 2


# =============================================================================
# GET /api/call-outcomes/follow-ups
# =============================================================================


class TestFollowUps:
    """Tests for GET /api/call-outcomes/follow-ups."""

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_today_follow_ups(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Return follow-ups due today."""
        mock_service.get_pending_follow_ups.return_value = PendingFollowUpsResponse(
            follow_ups=[
                PendingFollowUp(
                    outcome_id="outcome-1",
                    lead_id="lead-1",
                    lead_name="John Doe",
                    company="Acme",
                    phone_number="555-0100",
                    follow_up_date=date(2026, 2, 5),
                    follow_up_type="callback",
                    disposition="voicemail",
                )
            ],
            total_count=1,
            overdue_count=0,
        )

        response = client.get("/api/call-outcomes/follow-ups?date=2026-02-05")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_include_overdue(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Include overdue follow-ups in results."""
        mock_service.get_pending_follow_ups.return_value = PendingFollowUpsResponse(
            follow_ups=[
                PendingFollowUp(
                    outcome_id="outcome-old",
                    lead_id="lead-1",
                    phone_number="555-0100",
                    follow_up_date=date(2026, 2, 3),
                    follow_up_type="callback",
                    disposition="voicemail",
                    is_overdue=True,
                ),
                PendingFollowUp(
                    outcome_id="outcome-today",
                    lead_id="lead-2",
                    phone_number="555-0200",
                    follow_up_date=date(2026, 2, 5),
                    follow_up_type="send_email",
                    disposition="connected",
                ),
            ],
            total_count=2,
            overdue_count=1,
        )

        response = client.get(
            "/api/call-outcomes/follow-ups?date=2026-02-05&include_overdue=true"
        )
        data = response.json()
        assert data["total_count"] == 2
        assert data["overdue_count"] == 1
        # Overdue should be first
        assert data["follow_ups"][0]["is_overdue"] is True

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_sorted_overdue_first(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Follow-ups sorted with overdue items first."""
        mock_service.get_pending_follow_ups.return_value = PendingFollowUpsResponse(
            follow_ups=[
                PendingFollowUp(
                    outcome_id="overdue-1",
                    lead_id="lead-1",
                    phone_number="555-0100",
                    follow_up_date=date(2026, 2, 1),
                    follow_up_type="callback",
                    disposition="voicemail",
                    is_overdue=True,
                ),
                PendingFollowUp(
                    outcome_id="today-1",
                    lead_id="lead-2",
                    phone_number="555-0200",
                    follow_up_date=date(2026, 2, 5),
                    follow_up_type="callback",
                    disposition="no_answer",
                    is_overdue=False,
                ),
            ],
            total_count=2,
            overdue_count=1,
        )

        response = client.get("/api/call-outcomes/follow-ups?date=2026-02-05")
        data = response.json()
        assert data["follow_ups"][0]["outcome_id"] == "overdue-1"

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    def test_empty_follow_ups(
        self, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Return empty list when no follow-ups pending."""
        mock_service.get_pending_follow_ups.return_value = PendingFollowUpsResponse(
            follow_ups=[],
            total_count=0,
            overdue_count=0,
        )

        response = client.get("/api/call-outcomes/follow-ups")
        data = response.json()
        assert data["total_count"] == 0
        assert data["follow_ups"] == []


# =============================================================================
# POST /api/call-outcomes/batch
# =============================================================================


class TestBatchOutcomes:
    """Tests for POST /api/call-outcomes/batch."""

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_multiple_outcomes(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Log multiple outcomes at once."""
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_service.log_outcome.return_value = _mock_log_result()

        response = client.post(
            "/api/call-outcomes/batch",
            json={
                "outcomes": [
                    _make_outcome_request(),
                    _make_outcome_request("voicemail", "no_contact"),
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["success_count"] == 2
        assert data["failure_count"] == 0

    @patch("app.api.routes.call_outcomes.call_outcome_service")
    @patch("app.api.routes.call_outcomes.supabase_client")
    def test_partial_failure(
        self, mock_db: MagicMock, mock_service: MagicMock, client: TestClient
    ) -> None:
        """Handle partial failure — some leads not found."""
        # First call: lead found; second call: lead not found
        mock_db.get_lead_by_id.side_effect = [SAMPLE_LEAD, None]
        mock_service.log_outcome.return_value = _mock_log_result()

        response = client.post(
            "/api/call-outcomes/batch",
            json={
                "outcomes": [
                    _make_outcome_request(),
                    _make_outcome_request(lead_id="missing-uuid"),
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["failure_count"] == 1

    def test_empty_batch_422(self, client: TestClient) -> None:
        """Return 422 for empty outcomes list."""
        response = client.post(
            "/api/call-outcomes/batch",
            json={"outcomes": []},
        )
        assert response.status_code == 422
