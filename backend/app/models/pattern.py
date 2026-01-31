"""Pattern models for ML-based lead analysis."""

from datetime import datetime
from typing import Any

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


class LeadPattern(Base, TimestampMixin):
    """
    Discovered patterns in successful lead conversions.

    Used to identify similar leads in the database and prioritize outreach.
    """

    __tablename__ = "lead_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Pattern Identity
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)

    # Pattern Criteria (what defines this pattern)
    criteria: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Example criteria:
    # {
    #     "industry": ["education", "media"],
    #     "employee_count_min": 50,
    #     "employee_count_max": 500,
    #     "titles": ["VP", "Director", "Head of"],
    #     "email_domain_type": "corporate",
    #     "has_video_production": true
    # }

    # Pattern Stats
    total_matches: Mapped[int] = mapped_column(Integer, default=0)
    conversion_rate: Mapped[float | None] = mapped_column(Float)  # Historical rate
    avg_deal_size: Mapped[float | None] = mapped_column(Float)
    avg_sales_cycle_days: Mapped[int | None] = mapped_column(Integer)

    # Sample Leads (IDs of leads that match this pattern)
    sample_lead_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))

    # Best Practices
    recommended_approach: Mapped[str | None] = mapped_column(Text)
    best_first_touch: Mapped[str | None] = mapped_column(String(50))  # email, call, linkedin
    optimal_cadence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Effectiveness Tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence_score: Mapped[float | None] = mapped_column(Float)  # Model confidence
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Source Attribution
    discovered_by: Mapped[str] = mapped_column(
        String(50), default="pattern_agent"
    )  # agent or manual

    __table_args__ = (
        Index("ix_pattern_active_conversion", "is_active", "conversion_rate"),
    )


class WinLossPattern(Base, TimestampMixin):
    """
    Patterns extracted from won and lost deals.

    Learned from Clari Copilot conversations and HubSpot deal data.
    """

    __tablename__ = "win_loss_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Pattern Type
    is_win_pattern: Mapped[bool] = mapped_column(Boolean, index=True)  # True = win, False = loss

    # Pattern Name & Description
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)

    # Associated Factors
    factors: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Win factors example:
    # {
    #     "had_champion": true,
    #     "multi_threaded": true,
    #     "demo_within_7_days": true,
    #     "competitor_displacement": false
    # }
    # Loss factors example:
    # {
    #     "single_threaded": true,
    #     "price_objection": true,
    #     "lost_to_competitor": "Competitor X",
    #     "no_budget": true
    # }

    # Statistics
    occurrences: Mapped[int] = mapped_column(Integer, default=0)
    avg_deal_size: Mapped[float | None] = mapped_column(Float)
    industries: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    company_sizes: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # Associated Conversations (Clari IDs that informed this pattern)
    source_conversation_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))

    # AE Attribution (which AEs exhibited this pattern)
    ae_names: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # Coaching Recommendations
    coaching_notes: Mapped[str | None] = mapped_column(Text)
    prevention_strategy: Mapped[str | None] = mapped_column(Text)  # For loss patterns
    replication_strategy: Mapped[str | None] = mapped_column(Text)  # For win patterns

    # Validation
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    validated_by: Mapped[str | None] = mapped_column(String(100))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_winloss_type_occurrences", "is_win_pattern", "occurrences"),
    )
