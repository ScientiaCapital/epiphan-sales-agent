"""Conversation models for Clari Copilot integration."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ConversationOutcome(str, Enum):
    """Call/meeting outcome."""

    WON = "won"
    LOST = "lost"
    NEXT_STEP = "next_step"
    NO_DECISION = "no_decision"
    DISQUALIFIED = "disqualified"


class ConversationType(str, Enum):
    """Type of conversation."""

    DISCOVERY = "discovery"
    DEMO = "demo"
    NEGOTIATION = "negotiation"
    FOLLOW_UP = "follow_up"
    CLOSING = "closing"
    CHECK_IN = "check_in"


class Conversation(Base, TimestampMixin):
    """
    Conversation records from Clari Copilot.

    Stores call recordings, transcripts, and AI-extracted insights
    from AE conversations (Lex, Phil, etc.) for pattern learning.
    """

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Clari Reference
    clari_id: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)

    # Lead/Deal Reference
    lead_id: Mapped[int | None] = mapped_column(Integer, index=True)
    hubspot_deal_id: Mapped[str | None] = mapped_column(String(50), index=True)
    company_name: Mapped[str | None] = mapped_column(String(255), index=True)

    # Participants
    ae_name: Mapped[str | None] = mapped_column(String(100), index=True)
    ae_email: Mapped[str | None] = mapped_column(String(255))
    prospect_name: Mapped[str | None] = mapped_column(String(255))
    prospect_title: Mapped[str | None] = mapped_column(String(255))
    prospect_email: Mapped[str | None] = mapped_column(String(255))
    participant_count: Mapped[int] = mapped_column(Integer, default=2)

    # Call Details
    conversation_type: Mapped[ConversationType | None] = mapped_column(String(30))
    call_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    recording_url: Mapped[str | None] = mapped_column(Text)

    # Transcript
    transcript: Mapped[str | None] = mapped_column(Text)
    transcript_summary: Mapped[str | None] = mapped_column(Text)

    # AI Analysis
    sentiment_score: Mapped[float | None] = mapped_column(Float)  # -1 to 1
    engagement_score: Mapped[float | None] = mapped_column(Float)  # 0 to 100
    talk_ratio: Mapped[float | None] = mapped_column(Float)  # AE talk time %

    # Extracted Signals
    buying_signals: Mapped[list | None] = mapped_column(ARRAY(String))
    objections: Mapped[list | None] = mapped_column(ARRAY(String))
    competitors_mentioned: Mapped[list | None] = mapped_column(ARRAY(String))
    next_steps: Mapped[list | None] = mapped_column(ARRAY(String))
    pain_points: Mapped[list | None] = mapped_column(ARRAY(String))
    decision_makers: Mapped[list | None] = mapped_column(ARRAY(String))

    # Topics & Keywords
    topics: Mapped[list | None] = mapped_column(ARRAY(String))
    key_phrases: Mapped[list | None] = mapped_column(ARRAY(String))

    # Outcome
    outcome: Mapped[ConversationOutcome | None] = mapped_column(
        String(30), index=True
    )
    outcome_reason: Mapped[str | None] = mapped_column(Text)

    # Deal Impact
    deal_stage_before: Mapped[str | None] = mapped_column(String(50))
    deal_stage_after: Mapped[str | None] = mapped_column(String(50))
    deal_amount: Mapped[float | None] = mapped_column(Float)

    # Full Analysis (JSON blob with detailed AI analysis)
    full_analysis: Mapped[dict | None] = mapped_column(JSONB)

    # Sync Metadata
    synced_from_clari_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_conv_ae_date", "ae_name", "call_date"),
        Index("ix_conv_outcome", "outcome", "call_date"),
    )


class ConversationInsight(Base, TimestampMixin):
    """
    Extracted insights from conversations for pattern learning.

    These are reusable insights that can inform BDR outreach.
    """

    __tablename__ = "conversation_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Source Conversation
    conversation_id: Mapped[int] = mapped_column(Integer, index=True)

    # Insight Type
    insight_type: Mapped[str] = mapped_column(
        String(50), index=True
    )  # objection_handling, buying_signal, pain_point, etc.

    # Content
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    context: Mapped[str | None] = mapped_column(Text)  # Surrounding conversation
    response: Mapped[str | None] = mapped_column(Text)  # How AE handled it

    # Effectiveness
    effectiveness_score: Mapped[float | None] = mapped_column(Float)  # 0-100
    led_to_positive_outcome: Mapped[bool] = mapped_column(Boolean, default=False)

    # Usage Stats
    times_used_in_coaching: Mapped[int] = mapped_column(Integer, default=0)

    # Categorization
    industry: Mapped[str | None] = mapped_column(String(100))
    deal_size_range: Mapped[str | None] = mapped_column(String(50))
    persona: Mapped[str | None] = mapped_column(String(100))  # Decision maker type

    # Source Attribution
    ae_name: Mapped[str | None] = mapped_column(String(100), index=True)

    __table_args__ = (
        Index("ix_insight_type_effectiveness", "insight_type", "effectiveness_score"),
    )
