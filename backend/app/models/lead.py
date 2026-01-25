"""Lead models for tracking BDR leads and audit trail."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LeadTier(str, Enum):
    """Lead qualification tiers."""

    PLATINUM = "platinum"  # 85-100 score
    GOLD = "gold"  # 70-84 score
    SILVER = "silver"  # 50-69 score
    BRONZE = "bronze"  # 0-49 score


class LeadStatus(str, Enum):
    """Lead pipeline status."""

    NEW = "new"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    ENGAGED = "engaged"
    OPPORTUNITY = "opportunity"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    NURTURE = "nurture"


class LeadAuditEvent(str, Enum):
    """Types of audit events in lead lifecycle."""

    # Import Stage
    LEAD_IMPORTED = "lead_imported"
    LEAD_FILTERED = "lead_filtered"

    # Qualification Stage
    LEAD_QUALIFIED = "lead_qualified"
    LEAD_SCORED = "lead_scored"
    TIER_ASSIGNED = "tier_assigned"

    # Enrichment Stage
    ENRICHMENT_STARTED = "enrichment_started"
    ENRICHMENT_COMPLETED = "enrichment_completed"
    EMAIL_EXTRACTED = "email_extracted"

    # HubSpot Sync
    HUBSPOT_SYNCED = "hubspot_synced"
    HUBSPOT_UPDATED = "hubspot_updated"

    # Pattern Detection
    PATTERN_MATCHED = "pattern_matched"
    CONVERSION_PREDICTED = "conversion_predicted"

    # Outreach
    OUTREACH_RECOMMENDED = "outreach_recommended"
    FIRST_CONTACT = "first_contact"

    # Lifecycle
    STATUS_CHANGED = "status_changed"
    TIER_CHANGED = "tier_changed"


class LeadAuditStage(str, Enum):
    """Pipeline stages for categorizing audit events."""

    IMPORT = "import"
    QUALIFICATION = "qualification"
    ENRICHMENT = "enrichment"
    SYNC = "sync"
    PATTERN = "pattern"
    OUTREACH = "outreach"
    LIFECYCLE = "lifecycle"


class Lead(Base, TimestampMixin):
    """
    Primary lead model for BDR prospects.

    Synced from HubSpot with enrichment data and AI scoring.
    """

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # HubSpot Reference
    hubspot_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, index=True
    )
    hubspot_owner_id: Mapped[str | None] = mapped_column(String(50))

    # Company Info
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    company_website: Mapped[str | None] = mapped_column(String(500))
    company_domain: Mapped[str | None] = mapped_column(String(255), index=True)
    industry: Mapped[str | None] = mapped_column(String(100))
    company_size: Mapped[str | None] = mapped_column(String(50))
    employee_count: Mapped[int | None] = mapped_column(Integer)
    annual_revenue: Mapped[float | None] = mapped_column(Numeric(15, 2))

    # Contact Info
    contact_name: Mapped[str | None] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(255), index=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    contact_title: Mapped[str | None] = mapped_column(String(255))
    contact_linkedin: Mapped[str | None] = mapped_column(String(500))

    # Location
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))

    # Lead Status
    status: Mapped[LeadStatus] = mapped_column(
        String(50), default=LeadStatus.NEW, index=True
    )
    tier: Mapped[LeadTier | None] = mapped_column(String(20), index=True)

    # AI Qualification Scores
    qualification_score: Mapped[float | None] = mapped_column(Float, index=True)
    qualification_reasoning: Mapped[str | None] = mapped_column(Text)
    qualified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Epiphan-Specific Scoring (customize for your ICP)
    video_production_score: Mapped[float | None] = mapped_column(Float)
    broadcast_score: Mapped[float | None] = mapped_column(Float)
    education_score: Mapped[float | None] = mapped_column(Float)
    enterprise_score: Mapped[float | None] = mapped_column(Float)

    # Outreach Tracking
    has_been_contacted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    first_contact_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_contact_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    contact_count: Mapped[int] = mapped_column(Integer, default=0)

    # Email Analysis
    email_domain_quality: Mapped[str | None] = mapped_column(
        String(20)
    )  # corporate, personal, invalid
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Pattern Matching
    matched_pattern_id: Mapped[int | None] = mapped_column(Integer)
    conversion_probability: Mapped[float | None] = mapped_column(Float)

    # Source Tracking
    lead_source: Mapped[str | None] = mapped_column(String(100))
    utm_source: Mapped[str | None] = mapped_column(String(100))
    utm_campaign: Mapped[str | None] = mapped_column(String(100))

    # Enrichment Data (JSON blob from Apollo/Clearbit)
    enrichment_data: Mapped[dict | None] = mapped_column(JSONB)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Sync Metadata
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_status: Mapped[str] = mapped_column(String(20), default="pending")

    __table_args__ = (
        Index("ix_leads_untouched", "has_been_contacted", "qualification_score"),
        Index("ix_leads_company_domain", "company_domain"),
        Index("ix_leads_status_tier", "status", "tier"),
    )


class LeadAuditLog(Base):
    """
    Audit trail for lead lifecycle - tracks every decision.

    Used by agents to understand lead history and for compliance.
    """

    __tablename__ = "lead_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Lead Reference
    lead_id: Mapped[int | None] = mapped_column(Integer, index=True)
    company_name: Mapped[str | None] = mapped_column(String(255), index=True)
    hubspot_id: Mapped[str | None] = mapped_column(String(50), index=True)

    # Event Details
    event_type: Mapped[LeadAuditEvent] = mapped_column(String(50), index=True)
    stage: Mapped[LeadAuditStage] = mapped_column(String(30), index=True)

    # Decision Data (what the agent decided and why)
    decision_data: Mapped[dict | None] = mapped_column(JSONB)

    # Performance Metrics
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6))

    # Agent Attribution
    agent_type: Mapped[str | None] = mapped_column(String(50))
    llm_provider: Mapped[str | None] = mapped_column(String(30))

    # Session Tracking (groups related events)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_audit_lead_event", "lead_id", "event_type"),
        Index("ix_audit_session", "session_id"),
        Index("ix_audit_created", "created_at"),
    )
