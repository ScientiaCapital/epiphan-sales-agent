"""Pydantic schemas for Voice AI call session integration.

Defines message types for WebSocket communication and REST endpoints.
The Voice AI desktop app connects via WebSocket during live calls to get
lead-specific intelligence: call briefs, competitor battlecards, objection
responses, and call outcome logging.

Protocol: JSON messages structured as {"type": "...", "data": {...}}
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Enums
# =============================================================================


class ClientMessageType(str, Enum):
    """Message types sent by the Voice AI client."""

    START_CALL = "start_call"
    COMPETITOR_QUERY = "competitor_query"
    OBJECTION = "objection"
    END_CALL = "end_call"


class ServerMessageType(str, Enum):
    """Message types sent by the server."""

    CALL_BRIEF = "call_brief"
    COMPETITOR_RESPONSE = "competitor_response"
    OBJECTION_RESPONSE = "objection_response"
    CALL_LOGGED = "call_logged"
    ERROR = "error"


# =============================================================================
# Client → Server Messages
# =============================================================================


class StartCallData(BaseModel):
    """Data for starting a call session."""

    lead_id: str = Field(description="Lead ID (HubSpot ID or internal ID)")
    lead_email: str | None = Field(default=None, description="Lead email for lookup/enrichment")


class CompetitorQueryData(BaseModel):
    """Data for a competitor intelligence query during a call."""

    competitor_name: str = Field(description="Name of competitor mentioned by prospect")
    context: str = Field(description="What the prospect said about the competitor")


class ObjectionData(BaseModel):
    """Data for an objection handling request."""

    objection_text: str = Field(description="The objection raised by the prospect")


class EndCallData(BaseModel):
    """Data for ending a call and logging the outcome."""

    disposition: str = Field(description="Call disposition (connected, voicemail, etc.)")
    result: str = Field(description="Call result (meeting_booked, follow_up_needed, etc.)")
    notes: str | None = Field(default=None, description="BDR notes from the call")
    duration_seconds: int = Field(default=0, ge=0, description="Call duration in seconds")
    objections: list[str] | None = Field(default=None, description="Objections raised during call")
    competitor_mentioned: str | None = Field(default=None, description="Competitor mentioned")


class ClientMessage(BaseModel):
    """Incoming WebSocket message from the Voice AI client."""

    type: ClientMessageType
    data: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Server → Client Messages
# =============================================================================


class CompetitorResponseData(BaseModel):
    """Competitor intelligence response sent back to the client."""

    response: str
    proof_points: list[str] = Field(default_factory=list)
    follow_up: str | None = None


class ObjectionResponseData(BaseModel):
    """Objection handling response sent back to the client."""

    response: str
    discovery_question: str | None = None
    persona_context: str | None = None


class CallLoggedData(BaseModel):
    """Confirmation data after logging a call outcome."""

    outcome_id: str
    follow_up_date: str | None = None
    follow_up_type: str | None = None


class ErrorData(BaseModel):
    """Error response data."""

    message: str
    code: str | None = None


class ServerMessage(BaseModel):
    """Outgoing WebSocket message to the Voice AI client."""

    type: ServerMessageType
    data: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Session State (in-memory, not persisted)
# =============================================================================


class CallSessionState(BaseModel):
    """In-memory state for an active call session.

    Ephemeral — only lives during the call. The call brief and outcome
    are persisted to Supabase via existing code paths.
    """

    session_id: str
    user_id: str = Field(default="anonymous", description="JWT sub claim — session owner")
    lead_id: str
    lead_email: str | None = None
    lead_context: dict[str, Any] = Field(default_factory=dict, description="Cached lead data")
    brief_id: str | None = Field(default=None, description="Persisted brief UUID")
    started_at: datetime = Field(default_factory=lambda: datetime.now())
    objections_raised: list[str] = Field(default_factory=list)
    competitors_mentioned: list[str] = Field(default_factory=list)
    persona_id: str | None = None


# =============================================================================
# REST Request/Response Models
# =============================================================================


class StartSessionRequest(BaseModel):
    """REST request to start a call session."""

    lead_id: str
    lead_email: str | None = None


class StartSessionResponse(BaseModel):
    """REST response after starting a call session."""

    session_id: str
    brief: dict[str, Any] = Field(description="Full CallBriefResponse as dict")
    brief_id: str | None = None


class CompetitorQueryRequest(BaseModel):
    """REST request for a competitor query."""

    competitor_name: str
    context: str


class ObjectionRequest(BaseModel):
    """REST request for objection handling."""

    objection_text: str


class EndSessionRequest(BaseModel):
    """REST request to end a call session."""

    disposition: str
    result: str
    notes: str | None = None
    duration_seconds: int = Field(default=0, ge=0)
    objections: list[str] | None = None
    competitor_mentioned: str | None = None


class SessionStateResponse(BaseModel):
    """REST response for session state query."""

    session_id: str
    lead_id: str
    lead_email: str | None = None
    brief_id: str | None = None
    started_at: str
    objections_raised: list[str]
    competitors_mentioned: list[str]
    persona_id: str | None = None
