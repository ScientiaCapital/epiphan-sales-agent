"""Tests for CallOutcomeService business logic.

Tests follow-up rules, lead status updates, stats computation,
and business day calculation.
"""

from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.data.call_outcome_schemas import (
    CallDisposition,
    CallOutcomeCreate,
    CallResult,
    FollowUpType,
)
from app.services.call_outcomes.service import CallOutcomeService


@pytest.fixture
def service() -> CallOutcomeService:
    """Create a fresh service instance."""
    return CallOutcomeService()


SAMPLE_INSERTED_RECORD: dict[str, Any] = {
    "id": "outcome-uuid-001",
    "lead_id": "lead-uuid-001",
    "called_at": "2026-02-05T14:30:00+00:00",
    "duration_seconds": 180,
    "phone_number_dialed": "555-0100",
    "phone_type": "direct",
    "disposition": "connected",
    "result": "meeting_booked",
    "notes": None,
    "objections": None,
    "buying_signals": None,
    "competitor_mentioned": None,
    "follow_up_date": None,
    "follow_up_type": None,
    "follow_up_notes": None,
    "hubspot_engagement_id": None,
    "synced_to_hubspot": False,
    "synced_at": None,
    "created_at": "2026-02-05T14:30:00+00:00",
    "updated_at": "2026-02-05T14:30:00+00:00",
}

SAMPLE_LEAD: dict[str, Any] = {
    "id": "lead-uuid-001",
    "hubspot_id": "hs_123",
    "first_name": "John",
    "last_name": "Doe",
    "company": "Acme Corp",
    "contact_count": 0,
    "lead_status": "open",
}


def _make_outcome(
    disposition: CallDisposition = CallDisposition.CONNECTED,
    result: CallResult = CallResult.MEETING_BOOKED,
    **overrides: Any,
) -> CallOutcomeCreate:
    """Build a CallOutcomeCreate for testing."""
    return CallOutcomeCreate(
        lead_id="lead-uuid-001",
        phone_number_dialed="555-0100",
        phone_type="direct",
        disposition=disposition,
        result=result,
        **overrides,
    )


# =============================================================================
# Lead Status Updates
# =============================================================================


class TestLeadStatusUpdates:
    """Test that log_outcome updates lead status correctly."""

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_meeting_booked_sets_meeting_scheduled(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """meeting_booked → lead_status = 'meeting_scheduled'."""
        mock_db.create_call_outcome.return_value = SAMPLE_INSERTED_RECORD
        mock_db.get_lead_by_id.return_value = {**SAMPLE_LEAD, "contact_count": 0}
        mock_db.update_lead.return_value = {}

        result = service.log_outcome(_make_outcome())

        assert result.success is True
        assert result.lead_updated is True
        # Verify update_lead was called with meeting_scheduled
        update_call = mock_db.update_lead.call_args
        assert update_call[0][1]["lead_status"] == "meeting_scheduled"

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_qualified_out_sets_disqualified(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """qualified_out → lead_status = 'disqualified'."""
        mock_db.create_call_outcome.return_value = {
            **SAMPLE_INSERTED_RECORD, "result": "qualified_out",
        }
        mock_db.get_lead_by_id.return_value = {**SAMPLE_LEAD}
        mock_db.update_lead.return_value = {}

        service.log_outcome(
            _make_outcome(result=CallResult.QUALIFIED_OUT)
        )

        update_data = mock_db.update_lead.call_args[0][1]
        assert update_data["lead_status"] == "disqualified"

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_dead_sets_dead(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """dead → lead_status = 'dead'."""
        mock_db.create_call_outcome.return_value = {
            **SAMPLE_INSERTED_RECORD, "result": "dead",
        }
        mock_db.get_lead_by_id.return_value = {**SAMPLE_LEAD}
        mock_db.update_lead.return_value = {}

        service.log_outcome(
            _make_outcome(
                disposition=CallDisposition.WRONG_NUMBER,
                result=CallResult.DEAD,
            )
        )

        update_data = mock_db.update_lead.call_args[0][1]
        assert update_data["lead_status"] == "dead"

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_voicemail_no_status_change(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """voicemail/no_contact → lead_status unchanged."""
        mock_db.create_call_outcome.return_value = {
            **SAMPLE_INSERTED_RECORD,
            "disposition": "voicemail",
            "result": "no_contact",
            "follow_up_date": "2026-02-07",
            "follow_up_type": "callback",
        }
        mock_db.get_lead_by_id.return_value = {**SAMPLE_LEAD}
        mock_db.update_lead.return_value = {}

        service.log_outcome(
            _make_outcome(
                disposition=CallDisposition.VOICEMAIL,
                result=CallResult.NO_CONTACT,
            )
        )

        update_data = mock_db.update_lead.call_args[0][1]
        assert "lead_status" not in update_data

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_follow_up_no_status_change(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """connected/follow_up_needed → lead_status unchanged."""
        mock_db.create_call_outcome.return_value = {
            **SAMPLE_INSERTED_RECORD,
            "result": "follow_up_needed",
            "follow_up_date": "2026-02-10",
            "follow_up_type": "send_email",
        }
        mock_db.get_lead_by_id.return_value = {**SAMPLE_LEAD}
        mock_db.update_lead.return_value = {}

        service.log_outcome(
            _make_outcome(result=CallResult.FOLLOW_UP_NEEDED)
        )

        update_data = mock_db.update_lead.call_args[0][1]
        assert "lead_status" not in update_data

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_contact_count_increments(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """contact_count increments from 0 to 1."""
        mock_db.create_call_outcome.return_value = SAMPLE_INSERTED_RECORD
        mock_db.get_lead_by_id.return_value = {**SAMPLE_LEAD, "contact_count": 0}
        mock_db.update_lead.return_value = {}

        service.log_outcome(_make_outcome())

        update_data = mock_db.update_lead.call_args[0][1]
        assert update_data["contact_count"] == 1


# =============================================================================
# Default Follow-Up Rules
# =============================================================================


class TestFollowUpRules:
    """Test automatic follow-up scheduling."""

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_voicemail_2_business_days(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """Voicemail → callback in 2 business days."""
        mock_db.create_call_outcome.return_value = {
            **SAMPLE_INSERTED_RECORD,
            "disposition": "voicemail",
            "result": "no_contact",
        }
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_db.update_lead.return_value = {}

        result = service.log_outcome(
            _make_outcome(
                disposition=CallDisposition.VOICEMAIL,
                result=CallResult.NO_CONTACT,
            )
        )

        assert result.follow_up_scheduled is True
        # Verify callback type was passed to DB
        create_call = mock_db.create_call_outcome.call_args[0][0]
        assert create_call["follow_up_type"] == "callback"

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_no_answer_1_business_day(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """No answer → callback in 1 business day."""
        mock_db.create_call_outcome.return_value = {
            **SAMPLE_INSERTED_RECORD,
            "disposition": "no_answer",
            "result": "no_contact",
        }
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_db.update_lead.return_value = {}

        result = service.log_outcome(
            _make_outcome(
                disposition=CallDisposition.NO_ANSWER,
                result=CallResult.NO_CONTACT,
            )
        )

        assert result.follow_up_scheduled is True
        create_call = mock_db.create_call_outcome.call_args[0][0]
        assert create_call["follow_up_type"] == "callback"

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_gatekeeper_1_business_day(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """Gatekeeper → callback in 1 business day."""
        mock_db.create_call_outcome.return_value = {
            **SAMPLE_INSERTED_RECORD,
            "disposition": "gatekeeper",
            "result": "no_contact",
        }
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_db.update_lead.return_value = {}

        result = service.log_outcome(
            _make_outcome(
                disposition=CallDisposition.GATEKEEPER,
                result=CallResult.NO_CONTACT,
            )
        )

        assert result.follow_up_scheduled is True

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_connected_follow_up_3_days_email(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """Connected + follow_up_needed → send_email in 3 business days."""
        mock_db.create_call_outcome.return_value = {
            **SAMPLE_INSERTED_RECORD,
            "result": "follow_up_needed",
        }
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_db.update_lead.return_value = {}

        result = service.log_outcome(
            _make_outcome(result=CallResult.FOLLOW_UP_NEEDED)
        )

        assert result.follow_up_scheduled is True
        create_call = mock_db.create_call_outcome.call_args[0][0]
        assert create_call["follow_up_type"] == "send_email"

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_meeting_no_follow_up(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """Meeting booked → no automatic follow-up."""
        mock_db.create_call_outcome.return_value = SAMPLE_INSERTED_RECORD
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_db.update_lead.return_value = {}

        result = service.log_outcome(_make_outcome())

        assert result.follow_up_scheduled is False

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_not_interested_no_follow_up(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """Not interested → no automatic follow-up."""
        mock_db.create_call_outcome.return_value = {
            **SAMPLE_INSERTED_RECORD,
            "disposition": "not_interested",
            "result": "dead",
        }
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_db.update_lead.return_value = {}

        result = service.log_outcome(
            _make_outcome(
                disposition=CallDisposition.NOT_INTERESTED,
                result=CallResult.DEAD,
            )
        )

        assert result.follow_up_scheduled is False

    @patch("app.services.call_outcomes.service.supabase_client")
    def test_explicit_overrides_default(
        self, mock_db: MagicMock, service: CallOutcomeService
    ) -> None:
        """Tim's explicit follow-up overrides default rules."""
        mock_db.create_call_outcome.return_value = {
            **SAMPLE_INSERTED_RECORD,
            "disposition": "voicemail",
            "result": "no_contact",
            "follow_up_date": "2026-02-20",
            "follow_up_type": "schedule_demo",
        }
        mock_db.get_lead_by_id.return_value = SAMPLE_LEAD
        mock_db.update_lead.return_value = {}

        result = service.log_outcome(
            _make_outcome(
                disposition=CallDisposition.VOICEMAIL,
                result=CallResult.NO_CONTACT,
                follow_up_date=date(2026, 2, 20),
                follow_up_type=FollowUpType.SCHEDULE_DEMO,
            )
        )

        assert result.follow_up_scheduled is True
        # Verify Tim's date was used, not default
        create_call = mock_db.create_call_outcome.call_args[0][0]
        assert create_call["follow_up_date"] == "2026-02-20"
        assert create_call["follow_up_type"] == "schedule_demo"

    def test_business_days_skip_weekends(
        self, service: CallOutcomeService
    ) -> None:
        """_add_business_days skips Saturday and Sunday."""
        # Wednesday 2026-02-04 + 2 business days = Friday 2026-02-06
        result = service._add_business_days(date(2026, 2, 4), 2)
        assert result == date(2026, 2, 6)

        # Friday 2026-02-06 + 1 business day = Monday 2026-02-09
        result = service._add_business_days(date(2026, 2, 6), 1)
        assert result == date(2026, 2, 9)

        # Friday 2026-02-06 + 3 business days = Wednesday 2026-02-11
        result = service._add_business_days(date(2026, 2, 6), 3)
        assert result == date(2026, 2, 11)


# =============================================================================
# Stats Computation
# =============================================================================


class TestStatsComputation:
    """Test _compute_stats aggregation logic."""

    def test_all_fields_computed(self, service: CallOutcomeService) -> None:
        """Verify all stats fields are computed from raw outcomes."""
        outcomes: list[dict[str, Any]] = [
            {"disposition": "connected", "result": "meeting_booked",
             "duration_seconds": 300, "phone_type": "direct"},
            {"disposition": "connected", "result": "follow_up_needed",
             "duration_seconds": 180, "phone_type": "mobile"},
            {"disposition": "voicemail", "result": "no_contact",
             "duration_seconds": 30, "phone_type": "work"},
            {"disposition": "no_answer", "result": "no_contact",
             "duration_seconds": 0, "phone_type": "direct"},
        ]

        stats = service._compute_stats("2026-02-05", outcomes)
        assert stats.total_dials == 4
        assert stats.connections == 2
        assert stats.voicemails == 1
        assert stats.no_answers == 1
        assert stats.meetings_booked == 1
        assert stats.connect_rate == 50.0  # 2/4 * 100
        assert stats.meeting_rate == 50.0  # 1/2 * 100
        assert stats.avg_call_duration == 240.0  # (300+180)/2

    def test_division_by_zero(self, service: CallOutcomeService) -> None:
        """Zero dials → zero rates, no division error."""
        stats = service._compute_stats("2026-02-05", [])
        assert stats.total_dials == 0
        assert stats.connect_rate == 0.0
        assert stats.meeting_rate == 0.0
        assert stats.avg_call_duration == 0.0

    def test_phone_type_breakdown(self, service: CallOutcomeService) -> None:
        """Phone types are counted correctly."""
        outcomes: list[dict[str, Any]] = [
            {"disposition": "connected", "result": "meeting_booked",
             "duration_seconds": 120, "phone_type": "direct"},
            {"disposition": "voicemail", "result": "no_contact",
             "duration_seconds": 0, "phone_type": "direct"},
            {"disposition": "connected", "result": "follow_up_needed",
             "duration_seconds": 60, "phone_type": "mobile"},
            {"disposition": "no_answer", "result": "no_contact",
             "duration_seconds": 0, "phone_type": None},
        ]

        stats = service._compute_stats("2026-02-05", outcomes)
        assert stats.phone_type_breakdown.direct == 2
        assert stats.phone_type_breakdown.mobile == 1
        assert stats.phone_type_breakdown.unknown == 1

    def test_avg_duration_excludes_non_connected(
        self, service: CallOutcomeService
    ) -> None:
        """Average duration only counts connected calls with duration > 0."""
        outcomes: list[dict[str, Any]] = [
            {"disposition": "connected", "result": "meeting_booked",
             "duration_seconds": 600, "phone_type": "direct"},
            {"disposition": "voicemail", "result": "no_contact",
             "duration_seconds": 30, "phone_type": "work"},
            {"disposition": "no_answer", "result": "no_contact",
             "duration_seconds": 0, "phone_type": "mobile"},
        ]

        stats = service._compute_stats("2026-02-05", outcomes)
        # Only the connected call (600s) counts
        assert stats.avg_call_duration == 600.0
