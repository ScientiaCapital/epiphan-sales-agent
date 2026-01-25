"""Epiphan ICP and Persona models based on BDR Playbook."""

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
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Vertical(str, Enum):
    """
    Epiphan target verticals from BDR Playbook.

    Primary (First 90 Days):
    - Higher Education: 1,600+ universities, LMS integration
    - Corporate: $352B training market, L&D/Comms/IT buying centers
    - Live Events: $87B → $345B market, production companies

    Secondary (Growth):
    - Government: 89,000+ entities, Open Meeting Law
    - House of Worship: 91% streaming post-COVID
    - Healthcare: $546M medical video, 78% teaching hospital adoption
    - Industrial: Manufacturing training, OSHA compliance
    - Legal: Courts, depositions, law enforcement
    - UX Research: Confidential research, local recording
    """

    HIGHER_ED = "higher_ed"
    CORPORATE = "corporate"
    LIVE_EVENTS = "live_events"
    GOVERNMENT = "government"
    HOUSE_OF_WORSHIP = "house_of_worship"
    HEALTHCARE = "healthcare"
    INDUSTRIAL = "industrial"
    LEGAL = "legal"
    UX_RESEARCH = "ux_research"


class PersonaType(str, Enum):
    """Key buyer personas from Epiphan BDR Playbook."""

    AV_DIRECTOR = "av_director"
    LD_DIRECTOR = "ld_director"  # Learning & Development
    TECHNICAL_DIRECTOR = "technical_director"
    SIMULATION_DIRECTOR = "simulation_director"
    COURT_ADMINISTRATOR = "court_administrator"
    CORP_COMMS_DIRECTOR = "corp_comms_director"
    EHS_MANAGER = "ehs_manager"  # Environment, Health & Safety
    LAW_FIRM_IT = "law_firm_it"
    CIO = "cio"
    PROVOST = "provost"


class ProductFit(str, Enum):
    """Epiphan product lineup for lead matching."""

    PEARL_NANO = "pearl_nano"  # $1,999 - SRT, mobile, PoE
    PEARL_NEXUS = "pearl_nexus"  # $3,299 - Fixed install, 1RU, 1TB SSD
    PEARL_MINI = "pearl_mini"  # $3,999 - Volunteer-friendly, touchscreen
    PEARL_2 = "pearl_2"  # $7,999 - Complex production, 6+ inputs
    EC20_PTZ = "ec20_ptz"  # $1,899 - AI auto-tracking


class ICPScore(Base, TimestampMixin):
    """
    ICP scoring for Epiphan leads.

    Based on playbook criteria:
    - Higher Ed: 10,000+ students, 50+ classrooms, existing LMS
    - Corporate: Fortune 1000, 1,000+ employees, hybrid workforce
    - Healthcare: Academic medical centers, simulation centers
    """

    __tablename__ = "icp_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Lead Reference
    lead_id: Mapped[int] = mapped_column(Integer, index=True)
    hubspot_id: Mapped[str | None] = mapped_column(String(50), index=True)

    # Vertical Classification
    primary_vertical: Mapped[Vertical | None] = mapped_column(String(30), index=True)
    secondary_verticals: Mapped[list | None] = mapped_column(ARRAY(String))
    vertical_confidence: Mapped[float | None] = mapped_column(Float)

    # Persona Match
    primary_persona: Mapped[PersonaType | None] = mapped_column(String(30))
    persona_confidence: Mapped[float | None] = mapped_column(Float)

    # Product Fit
    recommended_product: Mapped[ProductFit | None] = mapped_column(String(30))
    product_fit_reasoning: Mapped[str | None] = mapped_column(Text)

    # ICP Attribute Scores (0-100)
    company_size_score: Mapped[float | None] = mapped_column(Float)
    budget_authority_score: Mapped[float | None] = mapped_column(Float)
    tech_maturity_score: Mapped[float | None] = mapped_column(Float)
    buying_intent_score: Mapped[float | None] = mapped_column(Float)

    # Higher Ed Specific
    student_count: Mapped[int | None] = mapped_column(Integer)
    classroom_count: Mapped[int | None] = mapped_column(Integer)
    has_lms: Mapped[bool] = mapped_column(Boolean, default=False)
    lms_platform: Mapped[str | None] = mapped_column(
        String(50)
    )  # Panopto, Kaltura, YuJa

    # Corporate Specific
    employee_count: Mapped[int | None] = mapped_column(Integer)
    is_fortune_1000: Mapped[bool] = mapped_column(Boolean, default=False)
    has_hybrid_workforce: Mapped[bool] = mapped_column(Boolean, default=False)
    uses_zoom_teams: Mapped[bool] = mapped_column(Boolean, default=False)

    # Healthcare Specific
    is_academic_medical_center: Mapped[bool] = mapped_column(Boolean, default=False)
    has_simulation_center: Mapped[bool] = mapped_column(Boolean, default=False)
    ssh_accredited: Mapped[bool] = mapped_column(Boolean, default=False)

    # Government Specific
    is_government: Mapped[bool] = mapped_column(Boolean, default=False)
    population_served: Mapped[int | None] = mapped_column(Integer)

    # Overall Fit
    overall_icp_score: Mapped[float | None] = mapped_column(Float, index=True)
    icp_reasoning: Mapped[str | None] = mapped_column(Text)

    # Buying Signals Detected
    buying_signals: Mapped[list | None] = mapped_column(ARRAY(String))
    # Examples: "new_construction", "ada_compliance", "panopto_expansion", etc.

    __table_args__ = (
        Index("ix_icp_vertical_score", "primary_vertical", "overall_icp_score"),
    )


class BuyingTrigger(Base, TimestampMixin):
    """
    Detected buying triggers from playbook.

    High Intent:
    - New building construction/renovation
    - RFP for classroom technology
    - Hybrid workforce investment
    - Executive comms quality complaints

    Medium Intent:
    - ADA compliance pressure
    - Faculty/staff complaints
    - Job postings (AV Director, Technical Director)
    """

    __tablename__ = "buying_triggers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Lead Reference
    lead_id: Mapped[int] = mapped_column(Integer, index=True)

    # Trigger Details
    trigger_type: Mapped[str] = mapped_column(String(50), index=True)
    # Types: construction, rfp, hybrid_investment, ada_compliance, job_posting,
    #        executive_complaint, panopto_expansion, equipment_failure

    trigger_source: Mapped[str] = mapped_column(String(50))
    # Sources: hubspot, linkedin, news, job_board, website, clari_conversation

    # Intent Level
    intent_level: Mapped[str] = mapped_column(String(20))  # high, medium, low
    confidence: Mapped[float | None] = mapped_column(Float)

    # Details
    description: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(500))
    detected_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )

    # Follow-up
    requires_action: Mapped[bool] = mapped_column(Boolean, default=True)
    action_taken: Mapped[bool] = mapped_column(Boolean, default=False)
    action_notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_trigger_lead_type", "lead_id", "trigger_type"),
        Index("ix_trigger_intent", "intent_level", "detected_date"),
    )


class CompetitorIntel(Base, TimestampMixin):
    """
    Competitive intelligence from Clari conversations and research.

    Key competitors from playbook:
    - Panopto/Kaltura (video platforms - complementary)
    - Extron SMP (similar, but outdated fleet management)
    - Blackmagic ATEM (cheaper, needs PC)
    - vMix (software, Windows crashes)
    - TriCaster ($10K-$35K, overkill)
    - Haivision ($10K+, broadcast tier)
    """

    __tablename__ = "competitor_intel"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Lead/Conversation Reference
    lead_id: Mapped[int | None] = mapped_column(Integer, index=True)
    conversation_id: Mapped[int | None] = mapped_column(Integer)

    # Competitor
    competitor_name: Mapped[str] = mapped_column(String(100), index=True)
    # panopto, kaltura, extron, blackmagic, vmix, tricaster, haivision, magewell, etc.

    # Context
    context_type: Mapped[str] = mapped_column(String(30))
    # Types: incumbent, evaluating, mentioned, replaced

    # Details
    notes: Mapped[str | None] = mapped_column(Text)
    win_message: Mapped[str | None] = mapped_column(Text)  # From battlecard

    # Outcome (if known)
    displaced_competitor: Mapped[bool] = mapped_column(Boolean, default=False)
    lost_to_competitor: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_competitor_name", "competitor_name"),
    )
