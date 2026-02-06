"""Pydantic schemas for call outcome tracking.

Captures what happens AFTER the call — disposition, result, follow-ups,
and intelligence gathered by the BDR during conversation.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field

# =============================================================================
# Enums
# =============================================================================


class CallDisposition(str, Enum):
    """What happened when Tim dialed the number."""

    CONNECTED = "connected"
    VOICEMAIL = "voicemail"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    WRONG_NUMBER = "wrong_number"
    GATEKEEPER = "gatekeeper"
    CALLBACK_REQUESTED = "callback_requested"
    NOT_INTERESTED = "not_interested"
    NO_LONGER_THERE = "no_longer_there"


class CallResult(str, Enum):
    """Business outcome of the call."""

    MEETING_BOOKED = "meeting_booked"
    FOLLOW_UP_NEEDED = "follow_up_needed"
    QUALIFIED_OUT = "qualified_out"
    NURTURE = "nurture"
    DEAD = "dead"
    NO_CONTACT = "no_contact"


class FollowUpType(str, Enum):
    """Type of follow-up action scheduled."""

    CALLBACK = "callback"
    SEND_EMAIL = "send_email"
    SCHEDULE_DEMO = "schedule_demo"
    SEND_INFO = "send_info"
    LINKEDIN_CONNECT = "linkedin_connect"


# =============================================================================
# Request Models
# =============================================================================


class CallOutcomeCreate(BaseModel):
    """Request body for logging a single call outcome."""

    lead_id: str
    phone_number_dialed: str
    phone_type: str | None = None
    disposition: CallDisposition
    result: CallResult
    duration_seconds: int = Field(default=0, ge=0)
    notes: str | None = None
    objections: list[str] | None = None
    buying_signals: list[str] | None = None
    competitor_mentioned: str | None = None
    follow_up_date: date | None = None
    follow_up_type: FollowUpType | None = None
    follow_up_notes: str | None = None
    call_brief_id: str | None = None


class CallOutcomeBatchCreate(BaseModel):
    """Request body for logging multiple call outcomes (end-of-day catch-up)."""

    outcomes: list[CallOutcomeCreate] = Field(min_length=1)


# =============================================================================
# Response Models
# =============================================================================


class CallOutcomeResponse(BaseModel):
    """Full call outcome record representation."""

    id: str
    lead_id: str
    called_at: datetime
    duration_seconds: int
    phone_number_dialed: str
    phone_type: str | None = None
    disposition: str
    result: str
    notes: str | None = None
    objections: list[str] | None = None
    buying_signals: list[str] | None = None
    competitor_mentioned: str | None = None
    follow_up_date: date | None = None
    follow_up_type: str | None = None
    follow_up_notes: str | None = None
    call_brief_id: str | None = None
    hubspot_engagement_id: str | None = None
    synced_to_hubspot: bool = False
    synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CallOutcomeLogResult(BaseModel):
    """Result of logging a call outcome — tells Tim what happened."""

    success: bool
    outcome: CallOutcomeResponse
    lead_updated: bool
    follow_up_scheduled: bool


class PhoneTypeBreakdown(BaseModel):
    """Dials broken down by phone type."""

    direct: int = 0
    mobile: int = 0
    work: int = 0
    company: int = 0
    unknown: int = 0


class DailyCallStats(BaseModel):
    """Tim's daily performance dashboard."""

    date: str
    total_dials: int = 0
    connections: int = 0
    voicemails: int = 0
    no_answers: int = 0
    meetings_booked: int = 0
    connect_rate: float = 0.0
    meeting_rate: float = 0.0
    avg_call_duration: float = 0.0
    phone_type_breakdown: PhoneTypeBreakdown = Field(
        default_factory=PhoneTypeBreakdown
    )


class PendingFollowUp(BaseModel):
    """A follow-up that needs doing."""

    outcome_id: str
    lead_id: str
    lead_name: str | None = None
    company: str | None = None
    phone_number: str
    follow_up_date: date
    follow_up_type: str
    follow_up_notes: str | None = None
    disposition: str
    is_overdue: bool = False


class PendingFollowUpsResponse(BaseModel):
    """List of pending follow-ups with summary counts."""

    follow_ups: list[PendingFollowUp]
    total_count: int
    overdue_count: int


class LeadCallHistory(BaseModel):
    """Full call history for a single lead."""

    lead_id: str
    lead_name: str | None = None
    company: str | None = None
    total_calls: int
    total_connections: int
    last_called: datetime | None = None
    outcomes: list[CallOutcomeResponse]
